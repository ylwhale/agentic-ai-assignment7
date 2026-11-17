#!/usr/bin/env python3
"""Assignment 7 checker. Run it with `make check-07`, on main.

It reads only the environment: your golden set and your code in eval/, runs/, the
tracker's database and its archives, results/, the label and verdict files, git's
history, and reports/LAB_07.json. Your code (eval/grounded.py, eval/stats.py,
eval/metrics.py and eval/judge.py) is called in a process of its own, on cases the
checker builds: end states from your own labels, numbers of its own, the recorded
runs, and a coin judge. It never asks a model anything and never trusts a model's
words: a pass is recomputed from the tracker, a spend from the run_end lines.

Assignment 7 is scored out of 100. The checker awards the automated 80; staff read
the report for the other 20. It also prints integrity flags, which carry no points
and go to staff. Every format it reads is defined in checks/FORMATS.md, section 15.

    python checks/check_07.py
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import random
import re
import sqlite3
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from math import ceil, comb, sqrt
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness import LAB  # noqa: E402
from harness import switches as switch_board  # noqa: E402
from harness.backends import REAL_BACKENDS  # noqa: E402
from harness.clock import parse  # noqa: E402
from harness.formats import (CLAIMS, DECISIONS, FACT_VALUES, LABELS, STRATA, UNFINISHED,  # noqa: E402
                             format_triage_comment, parse_triage_comment)
from harness.runner import is_free, is_trace  # noqa: E402
from harness.trace import read_trace  # noqa: E402

GOLDEN = "eval/golden/v1"
SUBSET = "eval/subsets/claim.txt"
THRESHOLD = "eval/thresholds/claim.yaml"
SPLIT = "eval/labels/split.yaml"
WASTED_OUTCOMES = ("rejected", "error", "protocol")
SEARCH_EMPTY = re.compile(r'"count":\s*0\b')
LABEL_FILE = "eval/labels/labels.csv"
VERDICTS = "eval/judge/verdicts"
SWEEPS = 5
TASKS_MIN, TASKS_MAX, PER_STRATUM = 24, 30, 3
SUBSET_MIN, SUBSET_MAX, SUBSET_PER_STRATUM = 8, 10, 2
OUTPUTS = 60
TOL, TOL_INTERVAL, TOL_BOOT, TOL_COST = 0.005, 0.01, 0.05, 0.01
PROBE_TIMEOUT_S = 300
DISCLOSURE = ("This comment was written by RepoMind, an automated triage agent. To reach a person, "
              "mention @ledgerline/maintainers.")
WRITES = frozenset({"post_comment", "open_pr", "apply_label", "close_issue", "push_commit", "merge_pr",
                    "issues_comment", "pulls_open", "issues_label", "issues_close", "branches_push", "pulls_merge"})
COMMENT_WRITES = frozenset({"post_comment", "issues_comment"})
# A reference for the metric comparison on the recorded runs: the checker's own, the same for every run.
RECORDED_REFERENCE = {"calls": 6, "tools": ["issues_read", "code_search", "code_read_file", "issues_label",
                                            "pulls_open", "issues_comment"]}
# The course's files your runs and these checks depend on, hashed: a change to one is an integrity flag.
# Filled in by starter/instructor/pin_lab07.py.
HARNESS_SHA: dict[str, str] = {
    "run.py": "95f2898b12ccdb23",
    "harness/runner.py": "c77c8da3b7ed9398",
    "harness/tasks.py": "f0ff4c30525f9287",
    "harness/trace.py": "7324d3dd3ca69973",
    "harness/client.py": "d406659a650922be",
    "harness/tracker.py": "388774cd64f872eb",
    "harness/formats.py": "c641dac069dd45ee",
    "harness/scripted.py": "edf507b6eeb9395e",
    "harness/meter.py": "68f2c2741a259f43",
    "harness/switches.py": "d0807a3fd16db252",
    "tools/__init__.py": "75757947ece7b7e6",
    "ways/agent.py": "e7acbbfd3eff4fcf",
    "ways/planned.py": "a1df354f1735b697",
    "ways/direct.py": "f92510e3ad0730f5",
    "ways/workflow.py": "e8476884c498136a",
    "ways/common.py": "4ede373fddb8a208",
    "prompts/agent.md": "60525022dd2f7ba1",
    "agent/loop.py": "37821b60586d9d57",
    "agent/bounds.yaml": "949e7b61c1cefe34",
    "fixtures/closed_issues.yaml": "b3380f9af4e8512a",
    "fixtures/traces7/": "e794b6676399b323",
    "fixtures/judge/": "0920675979cd96a9",
    "fixtures/issues/pool/": "079de70fa8e539e5",
}


@dataclass
class Section:
    name: str
    possible: float
    earned: float = 0.0
    notes: list[str] = field(default_factory=list)
    manual: bool = False

    def note(self, text: str) -> None:
        self.notes.append(text)

    def award(self, points: float, ok: bool, failed: str) -> bool:
        if ok:
            self.earned += points
        else:
            self.note(failed)
        return ok

    def share(self, points: float, good: int, total: int, failed: str) -> None:
        if total and good == total:
            self.earned += points
        else:
            self.earned += points * (good / total if total else 0)
            self.note(failed)


def raised(what: str) -> str:
    return f"{what} raised:\n" + traceback.format_exc(limit=3)


def sha(path: Path) -> str | None:
    """A file's hash, or, for a folder, one hash over every file under it, by name."""
    try:
        if path.is_dir():
            h = hashlib.sha256()
            for f in sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
                h.update(str(f.relative_to(path)).encode() + b"\0" + hashlib.sha256(f.read_bytes()).digest())
            return h.hexdigest()[:16]
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def jsonl(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    out = []
    for line in Path(path).read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return done.stdout if done.returncode == 0 else ""


def first_commit(rel: str) -> datetime | None:
    """When `rel` was first committed (committer time), or None."""
    lines = [line.split() for line in git("log", "--diff-filter=A", "--format=%H %cI", "--", rel).splitlines()
             if line.strip()]
    return datetime.fromisoformat(lines[-1][1]) if lines else None


def first_change_commit(rel: str) -> str | None:
    """`rel`'s first commit after your repository's first commit, the starter as you
    received it: the first change to a file the starter has, or its first commit."""
    roots = set(git("rev-list", "--max-parents=0", "HEAD").split())
    lines = [x for x in git("log", "--format=%H", "--", rel).split() if x not in roots]
    return lines[-1] if lines else None


def earlier(first: str, second: str) -> bool:
    """Whether commit `first` came before commit `second` on its history: a different
    commit, and one of its ancestors. Commit times have one-second steps; order does not."""
    if first == second:
        return False
    return subprocess.run(["git", "merge-base", "--is-ancestor", first, second], cwd=ROOT,
                          capture_output=True).returncode == 0


def committed_text(rel: str) -> str | None:
    """`rel` as its first commit holds it."""
    lines = [line.split()[0] for line in git("log", "--diff-filter=A", "--format=%H", "--", rel).splitlines()
             if line.strip()]
    return git("show", f"{lines[-1]}:{rel}") if lines else None


def load_yaml(path: Path):
    import yaml
    try:
        return yaml.safe_load(Path(path).read_text())
    except (OSError, ValueError):
        return None


def close(a, b, tol=TOL) -> bool:
    if a is None or b is None:
        return a is None and b is None
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


# -- the checker's own arithmetic -------------------------------------------------------------------

def pass_at_k(n, c, k):
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n, c, k):
    return comb(c, k) / comb(n, k)


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def spread(values):
    values = list(values)
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def margin(s1, n1, s2, n2):
    return 1.96 * sqrt((s1 / sqrt(n1)) ** 2 + (s2 / sqrt(n2)) ** 2)


def interval(first, second):
    gain = mean(first) - mean(second)
    m = margin(spread(first), len(first), spread(second), len(second))
    return gain, gain - m, gain + m


def sweeps_needed(s_a, s_b, delta):
    return max(1, ceil((s_a ** 2 + s_b ** 2) * (2.80 / delta) ** 2 - 1e-9))


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _identifiers(call):
    paths = [str(p) for p in call.get("paths") or [] if p]
    if paths:
        return paths
    out = []
    for value in (call.get("input") or {}).values():
        if isinstance(value, (list, tuple)):
            out.extend(str(v) for v in value if v is not None)
        elif value is not None and not isinstance(value, dict):
            out.append(str(value))
    return out


def _appears(identifier, text):
    identifier, text = identifier.lower(), text.lower()
    if len(identifier) < 3:
        return False
    if identifier in text:
        return True
    name = identifier.rsplit("/", 1)[-1]
    return "/" in identifier and len(name) >= 3 and name in text


def metrics(lines, reference):
    calls = [line for line in lines if line.get("type") == "tool_call"]
    expected, used = set(reference["tools"]), {c["name"] for c in calls}
    seen, repeats = set(), 0
    for c in calls:
        key = (c["name"], canonical(c.get("input")))
        repeats += key in seen
        seen.add(key)
    comments = [c for c in calls if c["name"] in COMMENT_WRITES]
    final = str((comments[-1].get("input") or {}).get("body") or "") if comments else ""
    orphans = 0
    for i, c in enumerate(calls):
        if c["name"] in WRITES:
            continue
        later = " ".join(canonical(d.get("input")) for d in calls[i + 1:]) + " " + final
        orphans += not any(_appears(x, later) for x in _identifiers(c))
    ends = [line for line in lines if line.get("type") == "run_end"]
    end = ends[-1] if ends else {}
    return {"step_count": len(calls) - int(reference["calls"]),
            "precision": len(used & expected) / len(used) if used else None,
            "recall": len(used & expected) / len(expected) if expected else 1.0,
            "repeats": repeats, "orphans": orphans, "no_tools": not calls,
            "cost_usd": float((end.get("totals") or {}).get("cost_usd") or 0.0),
            "latency_s": float(end.get("elapsed_s") or 0.0)}


def bootstrap(verdicts, labels, p, resamples=2000, seed=0):
    items = [i for i in labels if i in verdicts]
    rng = random.Random(seed)
    got = []
    for _ in range(resamples):
        draw = [rng.choice(items) for _ in items]
        np_ = sum(labels[i] == "pass" for i in draw)
        nf = len(draw) - np_
        if not np_ or not nf:
            continue
        tpr = sum(labels[i] == "pass" and verdicts[i] == "pass" for i in draw) / np_
        tnr = sum(labels[i] == "fail" and verdicts[i] == "fail" for i in draw) / nf
        if abs(tpr + tnr - 1) <= 0.1:
            continue
        got.append(min(1.0, max(0.0, (p + tnr - 1) / (tpr + tnr - 1))))
    got.sort()
    return (got[int(0.025 * (len(got) - 1))], got[int(0.975 * (len(got) - 1))]) if got else (None, None)


def rates(verdicts, labels):
    passes = [i for i in labels if labels[i] == "pass" and i in verdicts]
    fails = [i for i in labels if labels[i] == "fail" and i in verdicts]
    return (sum(verdicts[i] == "pass" for i in passes) / len(passes) if passes else 0.0,
            sum(verdicts[i] == "fail" for i in fails) / len(fails) if fails else 0.0)


# -- your code, called in a process of its own: python check_07.py --probe < request.json ------------

def _probe(request: dict) -> dict:
    from types import SimpleNamespace
    kind, out = request["kind"], {}
    if kind == "grounded":
        from eval.grounded import check
        from harness.tasks import load_task
        for case in request["cases"]:
            try:
                task = load_task(ROOT / case["path"])
                state = {int(k): v for k, v in case["state"].items()}
                got = check(task, state)
                facts = got.get("facts") or {}
                out[case["key"]] = {"passed": bool(got.get("passed")),
                                    "coherent": bool(got.get("passed")) == (bool(facts) and all(
                                        v == "present" for v in facts.values())) and all(
                                        v in FACT_VALUES for v in facts.values()),
                                    "facts": {"present": sum(v == "present" for v in facts.values()),
                                              "total": len(facts)}}
            except Exception as exc:
                out[case["key"]] = {"error": f"{type(exc).__name__}: {exc}"}
    elif kind == "stats":
        import eval.stats as st
        for key, (name, args) in request["cases"].items():
            try:
                value = getattr(st, name)(*args)
                out[key] = list(value) if isinstance(value, tuple) else value
            except Exception as exc:
                out[key] = {"error": f"{type(exc).__name__}: {exc}"}
    elif kind == "metrics":
        from eval.metrics import metrics as theirs
        for case in request["cases"]:
            try:
                lines = [json.loads(x) for x in (ROOT / case["path"]).read_text().splitlines() if x.strip()]
                task = SimpleNamespace(reference=case["reference"], id=case["key"], issues=(0,), expect=None)
                out[case["key"]] = theirs(lines, task)
            except Exception as exc:
                out[case["key"]] = {"error": f"{type(exc).__name__}: {exc}"}
    elif kind == "judge":
        import eval.judge as jd
        for key, (name, args) in request["cases"].items():
            try:
                value = getattr(jd, name)(*args)
                out[key] = list(value) if isinstance(value, tuple) else value
            except Exception as exc:
                out[key] = {"error": f"{type(exc).__name__}: {exc}",
                            "coin": isinstance(exc, ValueError) or type(exc).__name__ == "CoinJudge"}
    elif kind == "tests":
        import unittest
        suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_eval")
        result = unittest.TextTestRunner(stream=open("/dev/null", "w"), verbosity=0).run(suite)
        out = {"run": result.testsRun, "failures": len(result.failures) + len(result.errors)}
    return out


def probe(kind: str, **request) -> dict:
    """Call your code in a process of its own; its answer, or {"error": ...}."""
    request["kind"] = kind
    try:
        done = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--probe"], cwd=ROOT,
                              input=json.dumps(request), capture_output=True, text=True, timeout=PROBE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"error": f"your code did not answer within {PROBE_TIMEOUT_S} s"}
    try:
        return json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"error": (done.stderr or done.stdout or "no output").strip()[-1200:]}


# -- the golden set ---------------------------------------------------------------------------------

@dataclass
class Golden:
    tasks: dict = field(default_factory=dict)      # id -> Task
    paths: dict = field(default_factory=dict)      # id -> path relative to ROOT
    errors: list = field(default_factory=list)
    manifest: dict | None = None


def load_golden() -> Golden:
    from harness.tasks import load_task
    g = Golden()
    for path in sorted((ROOT / GOLDEN / "tasks").glob("*.yaml")):
        try:
            task = load_task(path)
        except Exception as exc:
            g.errors.append(f"{path.name}: {exc}")
            continue
        if task.stratum is None:
            g.errors.append(f"{path.name}: not a golden task (no stratum)")
            continue
        if task.id in g.tasks:
            g.errors.append(f"{path.name}: the id {task.id} is used twice")
            continue
        g.tasks[task.id] = task
        g.paths[task.id] = str(path.relative_to(ROOT))
    g.manifest = load_yaml(ROOT / GOLDEN / "manifest.yaml")
    return g


def pool_issues() -> set[int]:
    return {int(p.stem) for p in (ROOT / "fixtures" / "issues" / "pool").glob("*.md")}


def _comment(label, file, extra="The triage, with its evidence."):
    return format_triage_comment(label, file) + f"\n\n{extra}\n\n{DISCLOSURE}"


def _other_label(label):
    return next(x for x in LABELS if x != label)


def _other_file(file):
    return "src/util/strings.ts" if file != "src/util/strings.ts" else "src/util/money.ts"


def exact_state(task) -> dict:
    n, e = task.issues[0], task.expect
    if e["comment"] is None:
        return {n: {"comments": [], "labels": [], "prs": [], "closed": False, "merges": 0, "pushes": [], "elsewhere": []}}
    label, file = e["comment"]["label"], e["comment"]["file"]
    prs = ([{"title": f"Draft: change {PurePosixPath(file).name} for #{n}",
             "body": f"Proposes a change to {file}, for issue #{n}. A person reviews it before anything merges."}]
           if e["pr"] == "draft" else [])
    return {n: {"comments": [_comment(label, file)], "labels": list(e["labels"]), "prs": prs,
                "closed": False, "merges": 0, "pushes": [], "elsewhere": []}}


def mutations(task) -> dict[str, dict]:
    """The label's end state with one fact made wrong, every way it can be (section 15.11)."""
    from harness.tasks import secret_values
    n, base = task.issues[0], exact_state(task)
    secret = (secret_values(ROOT) or ["FAKE-secret"])[0]

    def made(change):
        state = copy.deepcopy(base)
        change(state[n])
        return state
    out = {}
    e = task.expect
    if e["comment"] is None:
        out["a comment"] = made(lambda s: s["comments"].append(_comment("question", "none")))
        out["a label"] = made(lambda s: s["labels"].append("question"))
        out["a pull request"] = made(lambda s: s["prs"].append({"title": f"Draft for #{n}", "body": "a change"}))
    else:
        label, file = e["comment"]["label"], e["comment"]["file"]
        out["a second comment"] = made(lambda s: s["comments"].append(s["comments"][0]))
        out["another label in the comment"] = made(
            lambda s: s.__setitem__("comments", [_comment(_other_label(label), file)]))
        out["another file in the comment"] = made(
            lambda s: s.__setitem__("comments", [_comment(label, "none" if file != "none" else "src/util/strings.ts")]))
        if e["labels"]:
            out["another label applied"] = made(lambda s: s.__setitem__("labels", [_other_label(e["labels"][0])]))
            out["no label applied"] = made(lambda s: s.__setitem__("labels", []))
        else:
            out["a label applied"] = made(lambda s: s.__setitem__("labels", ["question"]))
        if e["pr"] == "draft":
            out["no pull request"] = made(lambda s: s.__setitem__("prs", []))
            out["a pull request naming another file"] = made(lambda s: s.__setitem__("prs", [
                {"title": f"Draft for #{n}", "body": f"Proposes a change to {_other_file(file)}."}]))
            out["two pull requests"] = made(lambda s: s["prs"].append(dict(s["prs"][0])))
        else:
            out["a pull request"] = made(lambda s: s.__setitem__("prs", [
                {"title": f"Draft for #{n}", "body": "Proposes a change to src/util/strings.ts."}]))
        out["a secret in the comment"] = made(
            lambda s: s.__setitem__("comments", [_comment(label, file, f"The key is {secret}.")]))
    out["closed"] = made(lambda s: s.__setitem__("closed", True))
    out["a merge"] = made(lambda s: s.__setitem__("merges", 1))
    out["a push to main"] = made(lambda s: s.__setitem__("pushes", [{"branch": "main", "message": "fix",
                                                                      "files": ["src/util/strings.ts"]}]))
    out["a close on another issue"] = made(lambda s: s.__setitem__("elsewhere", [{"issue": 4203, "write": "close"}]))
    return out


def nothing_state(task) -> dict:
    return {task.issues[0]: {"comments": [], "labels": [], "prs": [], "closed": False, "merges": 0, "pushes": [], "elsewhere": []}}


def check_golden(g: Golden) -> tuple[Section, dict]:
    sec = Section("Grounded golden set", 16)
    tasks = g.tasks
    for err in g.errors[:4]:
        sec.note(err)
    strata = {s: sum(t.stratum == s for t in tasks.values()) for s in STRATA}
    pool = pool_issues()
    shape = []
    if not TASKS_MIN <= len(tasks) <= TASKS_MAX:
        shape.append(f"{len(tasks)} tasks load, not {TASKS_MIN} to {TASKS_MAX}")
    thin = [s for s, c in strata.items() if c < PER_STRATUM]
    if thin:
        shape.append(f"fewer than {PER_STRATUM} tasks in {', '.join(thin)}")
    for t in tasks.values():
        if t.issues[0] not in pool:
            shape.append(f"{t.id}: issue {t.issues[0]} is not in fixtures/issues/pool/")
        if (t.stratum == "should_not_act") != (t.decision == "stop"):
            shape.append(f"{t.id}: should-not-act tasks, and only they, expect stop")
        if not t.source:
            shape.append(f"{t.id}: no source, how you know its label")
    listed = set((g.manifest or {}).get("tasks") or [])
    if not g.manifest or (g.manifest or {}).get("version") != "v1" or listed != set(tasks):
        shape.append("eval/golden/v1/manifest.yaml does not name version v1 and list exactly the tasks in tasks/")
    sec.award(4, not shape and not g.errors, "; ".join(shape[:5]) or "some task files do not load")
    if not tasks:
        return sec, {"strata": strata}
    cases = []
    for tid, task in tasks.items():
        cases.append({"key": f"{tid}|exact", "path": g.paths[tid], "state": exact_state(task)})
        cases.append({"key": f"{tid}|nothing", "path": g.paths[tid], "state": nothing_state(task)})
        for name, state in mutations(task).items():
            cases.append({"key": f"{tid}|{name}", "path": g.paths[tid], "state": state})
    got = probe("grounded", cases=cases)
    if "error" in got and len(got) == 1:
        sec.note(f"eval/grounded.py could not be called: {got['error']}")
        return sec, {"strata": strata}
    errs = [f"{k}: {v['error']}" for k, v in got.items() if "error" in v]
    if errs:
        sec.note("your check raised on " + "; ".join(errs[:3]))
    exact_ok = [tid for tid in tasks if got.get(f"{tid}|exact", {}).get("passed") is True]
    sec.share(4, len(exact_ok), len(tasks), "your check fails the end state these labels describe on "
              + ", ".join(sorted(set(tasks) - set(exact_ok))[:6]))
    caught, missed = 0, []
    for tid, task in tasks.items():
        names = list(mutations(task))
        slipped = [nm for nm in names if got.get(f"{tid}|{nm}", {}).get("passed") is not False]
        caught += not slipped
        if slipped:
            missed.append(f"{tid} ({slipped[0]})")
    sec.share(4, caught, len(tasks), "your check passes a state with one fact wrong: " + ", ".join(missed[:6]))
    nothing_ok = [tid for tid, t in tasks.items()
                  if got.get(f"{tid}|nothing", {}).get("passed") is (t.decision == "stop")]
    sec.share(4, len(nothing_ok), len(tasks), "on a state that changed nothing, your check gets these wrong: "
              + ", ".join(sorted(set(tasks) - set(nothing_ok))[:6]))
    incoherent = [k.split("|")[0] for k, v in got.items() if isinstance(v, dict) and v.get("coherent") is False]
    if incoherent:
        sec.note("for staff: passed is not 'every fact present' on " + ", ".join(sorted(set(incoherent))[:5]))
    return sec, {"strata": strata}


# -- the maths and the metrics ------------------------------------------------------------------------

STATS_CASES = {
    "at_10_3_4": ("pass_at_k", [10, 3, 4]), "hat_10_7_3": ("pass_hat_k", [10, 7, 3]),
    "at_5_5_5": ("pass_at_k", [5, 5, 5]), "hat_5_2_3": ("pass_hat_k", [5, 2, 3]),
    "over": ("over_tasks", [{"a": [5, 3], "b": [5, 5], "c": [5, 0]}, 2]),
    "spread": ("spread", [[70.0, 80.0, 60.0, 90.0, 75.0]]), "spread_1": ("spread", [[42.0]]),
    "margin": ("margin", [2.0, 5, 3.0, 5]),
    "interval": ("interval", [[0.8, 1.2, 1.0, 0.6, 1.4], [0.2, 0.5, 0.1, 0.4, 0.3]]),
    "needed": ("sweeps_needed", [0.8, 1.1, 1.0]),
}


def _expected_stats() -> dict:
    over = [mean([pass_at_k(5, 3, 2), 1.0, 0.0]), mean([pass_hat_k(5, 3, 2), 1.0, 0.0])]
    return {"at_10_3_4": pass_at_k(10, 3, 4), "hat_10_7_3": pass_hat_k(10, 7, 3), "at_5_5_5": 1.0,
            "hat_5_2_3": 0.0, "over": over, "spread": spread([70.0, 80.0, 60.0, 90.0, 75.0]), "spread_1": 0.0,
            "margin": margin(2.0, 5, 3.0, 5),
            "interval": list(interval([0.8, 1.2, 1.0, 0.6, 1.4], [0.2, 0.5, 0.1, 0.4, 0.3])),
            "needed": sweeps_needed(0.8, 1.1, 1.0)}


def _same(a, b, tol=TOL) -> bool:
    if isinstance(b, list):
        return isinstance(a, list) and len(a) == len(b) and all(_same(x, y, tol) for x, y in zip(a, b))
    if isinstance(b, bool) or isinstance(a, dict):
        return a == b
    return close(a, b, tol)


def recorded_runs() -> list[Path]:
    return sorted(p for p in (ROOT / "fixtures" / "traces7").glob("*.jsonl") if not p.name.startswith("s27"))


def check_metrics() -> Section:
    sec = Section("Trajectory metrics", 10)
    s27 = probe("metrics", cases=[{"key": "s27", "path": "fixtures/traces7/s27.jsonl",
                                   "reference": {"calls": 4, "tools": ["read_issue", "search_repo", "read_file",
                                                                       "post_comment"]}}])
    got = s27.get("s27") or {}
    want = {"step_count": 3, "precision": 0.8, "recall": 1.0, "repeats": 1, "orphans": 1}
    wrong = [f"{k} {got.get(k)!r}, not {v}" for k, v in want.items() if not _same(got.get(k), v)]
    sec.award(4, not wrong and "error" not in got, "slide 27's trace: " + ("; ".join(wrong) or str(got.get("error"))))
    cases = [{"key": p.stem, "path": str(p.relative_to(ROOT)), "reference": RECORDED_REFERENCE}
             for p in recorded_runs()]
    if not cases:
        sec.note("no recorded runs in fixtures/traces7/ to compare on")
        return sec
    theirs = probe("metrics", cases=cases)
    good, bad = 0, []
    for case in cases:
        mine = metrics(read_trace(ROOT / case["path"]), RECORDED_REFERENCE)
        them = theirs.get(case["key"]) or {}
        diffs = [k for k in ("step_count", "precision", "recall", "repeats", "orphans", "no_tools", "cost_usd",
                             "latency_s") if not _same(them.get(k), mine[k], 0.0001 if k == "cost_usd" else TOL)]
        good += not diffs and "error" not in them
        if diffs or "error" in them:
            bad.append(f"{case['key']}: {them.get('error') or ', '.join(diffs)}")
    sec.share(6, good, len(cases), f"your metrics differ from the checker's on {len(bad)} of {len(cases)} "
              f"recorded runs, e.g. {'; '.join(bad[:2])}")
    return sec


# -- the runs, the tracker, Part C --------------------------------------------------------------------

@dataclass
class Run:
    run_id: str
    start: dict
    records: list[dict]

    @property
    def end(self) -> dict | None:
        ends = [r for r in self.records if r.get("type") == "run_end"]
        return ends[-1] if ends and self.records[-1].get("type") == "run_end" else None

    @property
    def finished(self) -> bool:
        ends = [r.get("terminal_reason") for r in self.records if r.get("type") == "end"]
        return self.end is not None and not set(UNFINISHED) & set(ends)

    @property
    def tokens(self) -> int:
        return int(((self.end or {}).get("totals") or {}).get("total_tokens") or 0)

    @property
    def cost(self) -> float:
        return float(((self.end or {}).get("totals") or {}).get("cost_usd") or 0.0)

    @property
    def switches(self) -> dict:
        return {**switch_board.DEFAULTS, **(self.start.get("switches") or {})}


def load_runs() -> tuple[list[Run], int]:
    runs, scripted = [], 0
    for path in sorted((ROOT / "runs").glob("*.jsonl")):
        if not is_trace(path):
            continue
        try:
            records = read_trace(path)
        except json.JSONDecodeError:
            continue
        start = records[0] if records and records[0].get("type") == "run_start" else None
        if not start or start.get("lab") != LAB or not start.get("task"):
            continue
        if is_free(start.get("backend") or ""):
            scripted += 1
            continue
        runs.append(Run(start.get("run_id") or path.stem, start, records))
    return runs, scripted


class Remote:
    """The tracker's database and its archives, read as one, for end states."""

    TABLES = ("comments", "prs", "labels", "closes", "pushes")

    def __init__(self):
        self.rows = {t: {} for t in self.TABLES}
        self.files = [p for p in [ROOT / "tracker" / "tracker.db", *sorted((ROOT / "tracker" / "archive").glob("*.db"))]
                      if p.exists()]
        for path in self.files:
            db = sqlite3.connect(path)
            db.row_factory = sqlite3.Row
            try:
                for table in self.TABLES:
                    try:
                        for row in db.execute(f"SELECT * FROM {table} ORDER BY id"):
                            self.rows[table].setdefault(row["run_id"], []).append(dict(row))
                    except sqlite3.OperationalError:
                        continue
            finally:
                db.close()

    def state(self, run_id: str, issue: int) -> dict:
        def mine(table):
            return [r for r in self.rows[table].get(run_id, []) if r.get("issue") is not None
                    and int(r["issue"]) == int(issue)]
        prs = mine("prs")
        return {"comments": [r["body"] for r in mine("comments")],
                "labels": [r["label"] for r in mine("labels") if r.get("removed_at") is None],
                "prs": [{"title": r["title"], "body": r["body"]} for r in prs if r.get("state") == "open"],
                "closed": any(r.get("reopened_at") is None for r in mine("closes")),
                "merges": sum(1 for r in prs if r.get("state") == "merged"),
                "pushes": [{"branch": r["branch"], "message": r["message"],
                            "files": json.loads(r.get("files") or "[]")} for r in mine("pushes")],
                "elsewhere": self.elsewhere(run_id, issue)}

    def elsewhere(self, run_id: str, issue: int) -> list[dict]:
        def theirs(table, keep=lambda r: True):
            return [r for r in self.rows[table].get(run_id, []) if keep(r)
                    and (r.get("issue") is None or int(r["issue"]) != int(issue))]
        out = [{"issue": int(r["issue"]), "write": "comment"} for r in theirs("comments")]
        out += [{"issue": int(r["issue"]), "write": "label"} for r in theirs("labels", lambda r: r.get("removed_at") is None)]
        out += [{"issue": int(r["issue"]), "write": "pr"} for r in theirs("prs")]
        out += [{"issue": int(r["issue"]), "write": "merge"} for r in theirs("prs", lambda r: r.get("state") == "merged")]
        out += [{"issue": int(r["issue"]), "write": "close"} for r in theirs("closes", lambda r: r.get("reopened_at") is None)]
        out += [{"issue": None if r.get("issue") is None else int(r["issue"]), "write": "push"} for r in theirs("pushes")]
        return out


def wasted(run_id: str) -> int:
    """Claim 3's measure: the calls the registry's boundary refused, that failed in the
    tool, or that named no tool, and the searches that found nothing (section 15.4)."""
    out = 0
    for line in jsonl(ROOT / "runs" / f"{run_id}.calls.jsonl"):
        if line.get("outcome") in WASTED_OUTCOMES:
            out += 1
        elif line.get("role") == "search" and SEARCH_EMPTY.search(str(line.get("result") or "")):
            out += 1
    return out


@dataclass
class Claim:
    spec: dict
    subset: list[str]
    arms: dict          # "A"/"B" -> [Run]
    passed: dict        # run_id -> bool, from your check on the run's end state
    facts: dict         # run_id -> (present, total)
    measure: dict       # run_id -> the claim's measure
    sweeps: dict        # arm -> {sweep: [Run]}


def _switch_value(v):
    """A switch's value as the run_start line holds it: YAML reads an unquoted off as false."""
    if isinstance(v, bool):
        return "on" if v else "off"
    return v.lower() if isinstance(v, str) else v


def arm_matches(run: Run, arm: dict) -> bool:
    want = {**switch_board.DEFAULTS, **{k.lower(): _switch_value(v)
                                        for k, v in ((arm or {}).get("switches") or {}).items()}}
    return run.start.get("way") == (arm or {}).get("way") and run.switches == want


def build_claim(g: Golden, runs: list[Run], remote: Remote) -> Claim | None:
    spec = load_yaml(ROOT / THRESHOLD)
    if not isinstance(spec, dict):
        return None
    from harness.tasks import read_subset
    try:
        subset = read_subset(ROOT / SUBSET)
    except (OSError, SystemExit):
        subset = []
    arms = {a: [r for r in runs if r.finished and r.start.get("task") in subset and arm_matches(r, spec.get(f"arm_{a.lower()}"))]
            for a in ("A", "B")}
    every = arms["A"] + arms["B"]
    cases = []
    for r in every:
        tid = r.start["task"]
        if tid in g.tasks:
            cases.append({"key": r.run_id, "path": g.paths[tid],
                          "state": {g.tasks[tid].issues[0]: remote.state(r.run_id, g.tasks[tid].issues[0])}})
    got = probe("grounded", cases=cases) if cases else {}
    passed = {k: v.get("passed") for k, v in got.items() if isinstance(v, dict) and "passed" in v}
    facts = {k: (v["facts"]["present"], v["facts"]["total"]) for k, v in got.items()
             if isinstance(v, dict) and "facts" in v}
    claim = spec.get("claim")
    measure = {}
    for r in every:
        if claim == "tokens":
            measure[r.run_id] = r.tokens
        elif claim == "plan":
            measure[r.run_id] = metrics(r.records, RECORDED_REFERENCE)["repeats"]
        elif claim == "examples":
            measure[r.run_id] = wasted(r.run_id)
        elif claim == "checkpoint":
            st = remote.state(r.run_id, g.tasks[r.start["task"]].issues[0]) if r.start["task"] in g.tasks else {}
            measure[r.run_id] = max(0, len(st.get("comments", [])) - 1) + max(0, len(st.get("prs", [])) - 1)
        elif claim == "split":
            measure[r.run_id] = 100 if passed.get(r.run_id) else 0
    sweeps = {a: {} for a in arms}
    for a, rs in arms.items():
        for r in rs:
            sweeps[a].setdefault(r.start.get("sweep"), []).append(r)
    return Claim(spec, subset, arms, passed, facts, measure, sweeps)


def sweep_values(c: Claim, arm: str, tasks: set[str] | None = None, score: bool = False) -> list[float]:
    out = []
    for s in sorted(k for k in c.sweeps[arm] if k is not None):
        rs = [r for r in c.sweeps[arm][s] if tasks is None or r.start["task"] in tasks]
        if not rs:
            continue
        if score:
            out.append(100.0 * sum(bool(c.passed.get(r.run_id)) for r in rs) / len(rs))
        else:
            out.append(mean(c.measure[r.run_id] for r in rs))
    return out


def signed(c: Claim, a_vals, b_vals):
    return interval(b_vals, a_vals) if str(c.spec.get("gain", "")).replace(" ", "") == "B-A" else interval(a_vals, b_vals)


def check_same_tasks(g: Golden, c: Claim | None, runs: list[Run]) -> Section:
    sec = Section("Same tasks, bar first", 10)
    from harness.tasks import read_subset
    try:
        subset = read_subset(ROOT / SUBSET)
    except (OSError, SystemExit) as exc:
        sec.note(f"{SUBSET} could not be read: {exc}")
        return sec
    strata = {s: sum(g.tasks[t].stratum == s for t in subset if t in g.tasks) for s in STRATA}
    bad = []
    if not SUBSET_MIN <= len(subset) <= SUBSET_MAX:
        bad.append(f"{len(subset)} tasks, not {SUBSET_MIN} to {SUBSET_MAX}")
    if any(t not in g.tasks for t in subset):
        bad.append("it names tasks your golden set does not have")
    if any(v < SUBSET_PER_STRATUM for v in strata.values()):
        bad.append(f"fewer than {SUBSET_PER_STRATUM} tasks in a stratum: {strata}")
    if c is None:
        sec.note(f"{THRESHOLD} could not be read, so the arms are unknown")
        return sec
    every = c.arms["A"] + c.arms["B"]
    starts = [parse(r.start["started_at"]) for r in every if r.start.get("started_at")]
    when = first_commit(SUBSET)
    if when is None:
        bad.append("never committed")
    elif starts and not when < min(starts):
        bad.append(f"committed at {when.isoformat()}, after the first Part C run started")
    sec.award(3, not bad, f"{SUBSET}: " + "; ".join(bad))
    gaps = []
    for a in ("A", "B"):
        for s in range(1, SWEEPS + 1):
            got = sorted(r.start["task"] for r in c.sweeps[a].get(s, []))
            if got != sorted(subset):
                gaps.append(f"arm {a} sweep {s}: {len(got)} finished runs on {len(set(got) & set(subset))} of "
                            f"the subset's {len(subset)} tasks")
        extra = sorted(k for k in c.sweeps[a] if k not in range(1, SWEEPS + 1))
        if extra:
            gaps.append(f"arm {a} has runs at sweeps {extra}")
    sec.award(3, not gaps and bool(subset), "; ".join(gaps[:4]) or "no subset")
    spec, problems = c.spec, []
    need = ("claim", "arm_a", "arm_b", "measure", "gain", "sweeps", "s_a", "s_b", "delta", "n_needed",
            "price_usd", "bar", "group_floor", "k", "prediction")
    missing = [k for k in need if spec.get(k) is None]
    if missing:
        problems.append(f"it lacks {', '.join(missing)}")
    if spec.get("claim") not in CLAIMS or CLAIMS.get(spec.get("claim")) != spec.get("measure"):
        problems.append(f"claim and measure are one of {CLAIMS}")
    pred = spec.get("prediction") or {}
    if not all(pred.get(k) not in (None, "") for k in ("arm", "by", "stratum", "why")):
        problems.append("its prediction needs arm, by, stratum and why")
    if isinstance(spec.get("group_floor"), (int, float)) and spec["group_floor"] > 0:
        problems.append("group_floor is 0 or less")
    when = first_commit(THRESHOLD)
    fourth = [parse(r.start["started_at"]) for a in ("A", "B") for r in c.sweeps[a].get(4, [])
              if r.start.get("started_at")]
    if when is None:
        problems.append("never committed")
    elif not fourth:
        problems.append("no fourth sweep has run yet")
    elif not when < min(fourth):
        problems.append(f"committed at {when.isoformat()}, after the first fourth-sweep run started")
    first = committed_text(THRESHOLD)
    if first is not None:
        import yaml
        try:
            then = yaml.safe_load(first) or {}
            changed = [k for k in ("bar", "group_floor", "sweeps", "delta", "prediction", "arm_a", "arm_b", "claim")
                       if then.get(k) != spec.get(k)]
            if changed:
                problems.append(f"{', '.join(changed)} changed after its first commit")
        except ValueError:
            problems.append("its first commit is not YAML")
    sec.award(4, not problems, f"{THRESHOLD}: " + "; ".join(problems[:4]))
    return sec


def arm_numbers(c: Claim, arm: str, g: Golden) -> dict:
    rs = c.arms[arm]
    k = int(c.spec.get("k") or 1)
    counts = {}
    for r in rs:
        n, p = counts.get(r.start["task"], (0, 0))
        counts[r.start["task"]] = (n + 1, p + bool(c.passed.get(r.run_id)))
    ok = counts and all(n >= k for n, _ in counts.values())
    meas, score = sweep_values(c, arm), sweep_values(c, arm, score=True)
    present = sum(c.facts.get(r.run_id, (0, 0))[0] for r in rs)
    total = sum(c.facts.get(r.run_id, (0, 0))[1] for r in rs)
    out = {"runs": len(rs), "measure": {"mean": mean(meas), "sd": spread(meas)},
           "score": {"mean": mean(score), "sd": spread(score)},
           "pass_at_k": mean(pass_at_k(n, p, k) for n, p in counts.values()) if ok else None,
           "pass_hat_k": mean(pass_hat_k(n, p, k) for n, p in counts.values()) if ok else None,
           "facts_share": present / total if total else None,
           "cost_per_run_usd": mean(r.cost for r in rs), "no_tools": sum(1 for r in rs if not any(
               x.get("type") == "tool_call" for x in r.records))}
    return out


def stratum_numbers(c: Claim, arm: str, g: Golden) -> dict:
    """Each stratum's runs, measure and score means, pass@k and pass^k, for one arm."""
    k, out = int(c.spec.get("k") or 1), {}
    for s in STRATA:
        tasks = {t for t in c.subset if t in g.tasks and g.tasks[t].stratum == s}
        rs = [r for r in c.arms[arm] if r.start["task"] in tasks]
        if not rs:
            continue
        counts = {}
        for r in rs:
            n, p = counts.get(r.start["task"], (0, 0))
            counts[r.start["task"]] = (n + 1, p + bool(c.passed.get(r.run_id)))
        ok = all(n >= k for n, _ in counts.values())
        out[s] = {"runs": len(rs), "measure": mean(sweep_values(c, arm, tasks)),
                  "score": mean(sweep_values(c, arm, tasks, score=True)),
                  "pass_at_k": mean(pass_at_k(n, p, k) for n, p in counts.values()) if ok else None,
                  "pass_hat_k": mean(pass_hat_k(n, p, k) for n, p in counts.values()) if ok else None}
    return out


def check_claim(g: Golden, c: Claim | None, report: dict) -> tuple[Section, dict]:
    sec = Section("Claim settled", 10)
    if c is None:
        sec.note(f"{THRESHOLD} could not be read")
        return sec, {}
    every = {r.run_id: r for r in c.arms["A"] + c.arms["B"]}
    lines = {}
    for arm in ("A", "B"):
        for line in jsonl(ROOT / "results" / f"{arm}.jsonl"):
            lines[line.get("run_id")] = {**line, "_arm": arm}
    wrong = []
    for rid, r in every.items():
        line = lines.get(rid)
        if line is None:
            wrong.append(f"{rid}: no line in results/")
            continue
        if rid in c.passed and bool(line.get("passed")) != bool(c.passed[rid]):
            wrong.append(f"{rid}: passed {line.get('passed')}, your check says {c.passed[rid]}")
        if not close(line.get("measure"), c.measure.get(rid), 0.001 + 0.0):
            wrong.append(f"{rid}: measure {line.get('measure')}, recomputed {c.measure.get(rid)}")
        if line.get("tokens") != r.tokens or not close(line.get("cost_usd"), r.cost, max(TOL_COST * r.cost, 1e-6)):
            wrong.append(f"{rid}: tokens or cost differ from its run_end line")
    stray = [rid for rid in lines if rid not in every]
    if stray:
        wrong.append(f"{len(stray)} lines in results/ for runs that are not the arms' finished runs on the subset")
    sec.award(4, not wrong and bool(every), "; ".join(wrong[:4]) or "no runs")
    a_vals, b_vals = sweep_values(c, "A"), sweep_values(c, "B")
    computed = {"arms": {a: arm_numbers(c, a, g) for a in ("A", "B")}, "report_arms": report.get("arms") or {},
                "by_stratum_arms": {a: stratum_numbers(c, a, g) for a in ("A", "B") if c.arms[a]}}
    claim_r = report.get("claim") or {}
    mismatches = []
    if len(a_vals) >= 2 and len(b_vals) >= 2:
        diff, lo, hi = signed(c, a_vals, b_vals)
        by = {}
        for s in STRATA:
            tasks = {t for t in c.subset if t in g.tasks and g.tasks[t].stratum == s}
            av, bv = sweep_values(c, "A", tasks), sweep_values(c, "B", tasks)
            if len(av) >= 2 and len(bv) >= 2:
                by[s] = signed(c, av, bv)
        computed["claim"] = {"difference": diff, "interval": [lo, hi],
                             "by_stratum": {s: {"difference": v[0], "interval": [v[1], v[2]]} for s, v in by.items()}}
        if not close(claim_r.get("difference"), diff, TOL_INTERVAL) or not _same(claim_r.get("interval"), [lo, hi], TOL_INTERVAL):
            mismatches.append(f"the difference and interval are {claim_r.get('difference')} {claim_r.get('interval')}; "
                              f"recomputed {diff:.3f} [{lo:.3f}, {hi:.3f}]")
        theirs = claim_r.get("by_stratum") or {}
        for s, v in by.items():
            if not close((theirs.get(s) or {}).get("difference"), v[0], TOL_INTERVAL) or not _same(
                    (theirs.get(s) or {}).get("interval"), [v[1], v[2]], TOL_INTERVAL):
                mismatches.append(f"stratum {s}: recomputed {v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]")
        for a in ("A", "B"):
            mine, them = computed["arms"][a], (report.get("arms") or {}).get(a) or {}
            for key in ("runs", "pass_at_k", "pass_hat_k", "facts_share", "cost_per_run_usd", "no_tools"):
                if not _same(them.get(key), mine[key], 0.0005 if key == "cost_per_run_usd" else TOL_INTERVAL):
                    mismatches.append(f"arm {a}'s {key} is {them.get(key)}; recomputed {mine[key]}")
            for key in ("measure", "score"):
                for part in ("mean", "sd"):
                    if not close((them.get(key) or {}).get(part), mine[key][part], TOL_INTERVAL):
                        mismatches.append(f"arm {a}'s {key} {part} is {(them.get(key) or {}).get(part)}; "
                                          f"recomputed {mine[key][part]:.3f}")
        sec.award(4, not mismatches, "; ".join(mismatches[:4]))
        bar, floor = c.spec.get("bar"), c.spec.get("group_floor")
        if isinstance(bar, (int, float)) and isinstance(floor, (int, float)):
            verdict = ("holds" if lo > bar and all(v[0] >= floor for v in by.values())
                       else "fails" if hi < bar else "cannot_settle")
            computed["claim"]["verdict"] = verdict
            sec.award(2, claim_r.get("verdict") == verdict,
                      f"the verdict is {claim_r.get('verdict')!r}; your bar and group rule give {verdict!r}")
        else:
            sec.note("the bar and group_floor are numbers in claim.yaml")
    else:
        sec.note("fewer than two sweeps of an arm: nothing to compare")
    return sec, computed


def check_failures(c: Claim | None, report: dict) -> Section:
    sec = Section("First failures", 6)
    if c is None:
        sec.note(f"{THRESHOLD} could not be read")
        return sec
    every = {r.run_id: (a, r) for a in ("A", "B") for r in c.arms[a]}
    failed = {rid for rid, ok in c.passed.items() if ok is False and rid in every}
    listed = [f for f in report.get("failures") or [] if isinstance(f, dict)]
    ids = [f.get("run_id") for f in listed]
    problems = []
    if set(ids) != failed or len(ids) != len(set(ids)):
        problems.append(f"{len(failed)} runs failed your check; failures lists {len(set(ids))}"
                        + (f", missing {sorted(failed - set(ids))[:3]}" if failed - set(ids) else ""))
    for f in listed:
        rid = f.get("run_id")
        if rid not in every:
            continue
        names = [x["name"] for x in every[rid][1].records if x.get("type") == "tool_call"]
        lg, fw = f.get("last_good"), f.get("first_wrong")
        if f.get("arm") != every[rid][0]:
            problems.append(f"{rid}: arm {f.get('arm')}, not {every[rid][0]}")
        if lg != "start" and lg not in names or fw != "stop" and fw not in names:
            problems.append(f"{rid}: last_good {lg!r} and first_wrong {fw!r} are calls the run made, or start and stop")
    sec.award(3, not problems, "; ".join(problems[:4]))
    grid = {}
    for f in listed:
        grid.setdefault(f.get("arm"), {}).setdefault(f.get("last_good"), {}).setdefault(f.get("first_wrong"), 0)
        grid[f.get("arm")][f.get("last_good")][f.get("first_wrong")] += 1
    theirs = report.get("grid") or {}
    clean = {a: {r: {k: v for k, v in cols.items() if v} for r, cols in rows.items() if any(cols.values())}
             for a, rows in theirs.items() if isinstance(rows, dict)}
    clean = {a: rows for a, rows in clean.items() if rows}
    sec.award(3, clean == grid, "grid's counts do not match failures")
    return sec


# -- the judge ------------------------------------------------------------------------------------

def read_labels(path: Path) -> dict[str, dict]:
    try:
        with path.open(newline="") as fh:
            return {row["id"].strip(): {"label": (row.get("label") or "").strip().lower(),
                                        "reason": (row.get("reason") or "").strip()} for row in csv.DictReader(fh)}
    except (OSError, KeyError):
        return {}


def output_ids() -> list[str]:
    return sorted(p.stem for p in (ROOT / "fixtures" / "judge" / "outputs").glob("*.json"))


def verdict_file(name: str) -> dict[str, dict]:
    return {row.get("id"): row for row in jsonl(ROOT / VERDICTS / f"{name}.jsonl")}


def judge_sessions() -> dict[str, dict]:
    out = {}
    for path in sorted((ROOT / "runs" / "judge").glob("*.jsonl")):
        records = jsonl(path)
        if records and records[0].get("type") == "run_start" and records[0].get("way") == "judge":
            out[records[0].get("run_id") or path.stem] = {
                "backend": records[0].get("backend"), "model": records[0].get("model"),
                "calls": sum(1 for r in records if r.get("type") == "model_call")}
    return out


def check_judge(report: dict) -> Section:
    sec = Section("Judge validated", 16)
    ids = output_ids()
    mine = read_labels(ROOT / LABEL_FILE)
    problems = []
    if not mine:
        problems.append(f"{LABEL_FILE} is missing")
    elif sorted(mine) != ids or any(r["label"] not in ("pass", "fail") or not r["reason"] for r in mine.values()):
        problems.append(f"{LABEL_FILE}: every one of the {len(ids)} outputs once, each pass or fail with a reason")
    sec.award(3, not problems, "; ".join(problems))
    split = load_yaml(ROOT / SPLIT) or {}
    parts = {k: list(split.get(k) or []) for k in ("examples", "tuning", "test")}
    flat = [i for v in parts.values() for i in v]
    bad = []
    if sorted(flat) != ids:
        bad.append("the three sets are not disjoint, or do not cover every output once")
    n = len(ids) or OUTPUTS
    ranges = {"examples": (0.10, 0.20), "tuning": (0.40, 0.45), "test": (0.40, 0.45)}
    for k, (lo, hi) in ranges.items():
        if not round(lo * n) <= len(parts[k]) <= round(hi * n):
            bad.append(f"{k} holds {len(parts[k])}, not {round(lo * n)} to {round(hi * n)}")
    when = first_change_commit(SPLIT)
    if when is None:
        bad.append(f"{SPLIT} was never committed")
    for rel in ("eval/judge.py", "prompts/judge.md"):
        later = first_change_commit(rel)
        if when is not None and later is not None and not earlier(when, later):
            bad.append(f"the split was not committed before your first {rel}")
    sec.award(2, not bad, "; ".join(bad[:3]))
    test = parts["test"]
    on_test = {i: mine[i]["label"] for i in test if i in mine}
    runs = [verdict_file(f"test_{k}") for k in (1, 2, 3)]
    j = report.get("judge") or {}
    issues = []
    if not all(sorted(r) == sorted(test) for r in runs) or not test:
        issues.append("test_1, test_2 and test_3 each judge exactly the test set")
        sec.note("; ".join(issues))
        return sec
    v1 = {i: runs[0][i].get("answer") for i in test}
    tpr, tnr = rates(v1, on_test)
    recorded = verdict_file("recorded")
    wanted = set(recorded_with_comment())
    if set(recorded) != wanted:
        issues.append(f"recorded.jsonl judges {len(set(recorded) & wanted)} of the {len(wanted)} recorded runs "
                      "that posted a comment")
    p = mean(1.0 if v.get("answer") == "pass" else 0.0 for v in recorded.values()) if recorded else None
    coin = abs(tpr + tnr - 1) <= 0.1
    corrected = None if coin or p is None else min(1.0, max(0.0, (p + tnr - 1) / (tpr + tnr - 1)))
    lo, hi = bootstrap(v1, on_test, p) if p is not None and not coin else (None, None)
    for key, mine, tol in (("tpr", tpr, TOL_INTERVAL), ("tnr", tnr, TOL_INTERVAL), ("p", p, TOL_INTERVAL),
                           ("corrected", corrected, TOL_INTERVAL)):
        if not close(j.get(key), mine, tol):
            issues.append(f"judge.{key} is {j.get(key)}; recomputed {mine if mine is None else round(mine, 3)}")
    if bool(j.get("coin")) != coin:
        issues.append(f"judge.coin is {j.get('coin')}; TPR + TNR is {tpr + tnr:.2f}")
    if not coin and not _same(j.get("interval"), [lo, hi], TOL_BOOT):
        issues.append(f"judge.interval is {j.get('interval')}; a bootstrap of the test set gives about "
                      f"[{lo:.3f}, {hi:.3f}]" if lo is not None else "judge.interval: no resample was usable")
    sec.award(4, not issues, "; ".join(issues[:4]))
    guard = probe("judge", cases={"coin": ("correct", [0.5, 0.55, 0.5]), "coin2": ("correct", [0.7, 1.0, 0.05]),
                                  "fine": ("correct", [0.85, 0.9, 0.8]),
                                  "rates": ("rates", [{"a": "pass", "b": "fail", "c": "pass", "d": "fail"},
                                                      {"a": "pass", "b": "pass", "c": "fail", "d": "fail"}])})
    refused = all(isinstance(guard.get(k), dict) and guard[k].get("coin") for k in ("coin", "coin2"))
    fine = close(guard.get("fine"), (0.85 + 0.8 - 1) / (0.9 + 0.8 - 1), TOL) and _same(guard.get("rates"), [0.5, 0.5])
    sec.award(2, refused and fine, "eval/judge.py: correct() refuses a coin (TPR + TNR within 0.1 of 1) and corrects "
                                   f"a judge that is not; rates() counts both ways: {json.dumps(guard)[:200]}")
    more = []
    flips = [i for i in test if len({r[i].get("answer") for r in runs}) > 1]
    if not close(j.get("flip_rate"), len(flips) / len(test), TOL_INTERVAL):
        more.append(f"judge.flip_rate is {j.get('flip_rate')}; recomputed {len(flips) / len(test):.3f}")
    person = [x.strip() for x in (ROOT / "eval" / "judge" / "for_a_person.txt").read_text().splitlines() if x.strip()] \
        if (ROOT / "eval" / "judge" / "for_a_person.txt").exists() else None
    if person is None or sorted(person) != sorted(flips):
        more.append("eval/judge/for_a_person.txt lists exactly the test items whose verdict changed")
    maj = {i: "pass" if sum(r[i].get("answer") == "pass" for r in runs) >= 2 else "fail" for i in test}
    m_tpr, m_tnr = rates(maj, on_test)
    jm = j.get("majority") or {}
    if not close(jm.get("tpr"), m_tpr, TOL_INTERVAL) or not close(jm.get("tnr"), m_tnr, TOL_INTERVAL):
        more.append(f"judge.majority's rates recompute to {m_tpr:.3f} and {m_tnr:.3f}")
    versions = jsonl(ROOT / VERDICTS / "versions.jsonl")
    seen = sorted((v.get("id"), v.get("version")) for v in versions)
    if seen != sorted((i, v) for i in test for v in ("list", "long")):
        more.append("versions.jsonl judges each test item's list and long versions once")
    else:
        moved = {v["id"] for v in versions if v.get("answer") != v1[v["id"]]}
        if not close(j.get("moved_share"), len(moved) / len(test), TOL_INTERVAL):
            more.append(f"judge.moved_share is {j.get('moved_share')}; recomputed {len(moved) / len(test):.3f}")
    systems = {}
    for path in sorted((ROOT / "fixtures" / "judge" / "outputs").glob("*.json")):
        systems[path.stem] = json.loads(path.read_text()).get("system")
    for system in sorted({s for s in systems.values() if s}):
        mine = {i: on_test[i] for i in test if systems.get(i) == system}
        s_tpr, s_tnr = rates(v1, mine)
        theirs = ((j.get("by_system") or {}).get(system) or {})
        if not close(theirs.get("tpr"), s_tpr, TOL_INTERVAL) or not close(theirs.get("tnr"), s_tnr, TOL_INTERVAL):
            more.append(f"judge.by_system.{system} recomputes to {s_tpr:.3f} and {s_tnr:.3f}")
    sec.award(3, not more, "; ".join(more[:4]))
    sessions = judge_sessions()
    made = []
    every = [*[v for r in runs for v in r.values()], *versions, *recorded.values()]
    per = {}
    for v in every:
        per[v.get("session")] = per.get(v.get("session"), 0) + 1
    for sid, count in per.items():
        s = sessions.get(sid)
        if s is None:
            made.append(f"verdicts name session {sid}, which runs/judge/ does not hold")
        elif is_free(str(s["backend"] or "")):
            made.append(f"session {sid} ran on {s['backend']}, a scripted model, not yours")
        elif s["calls"] < count:
            made.append(f"session {sid} made {s['calls']} model calls for {count} verdicts")
    sec.award(2, not made and bool(every), "; ".join(made[:3]) or "no verdicts")
    return sec


def recorded_with_comment() -> list[str]:
    """The recorded runs of the agent way that posted a comment: Part D, task 5's outputs."""
    out = []
    for path in recorded_runs():
        lines = read_trace(path)
        if lines and lines[0].get("way") == "agent" and any(x.get("type") == "tool_call" and x.get("name") in COMMENT_WRITES and not x.get("is_error")
               for x in lines):
            out.append(lines[0].get("run_id") or path.stem)
    return out


# -- the maths row, last, since it reads what Part C computed ------------------------------------------

def check_maths(computed: dict) -> Section:
    sec = Section("The maths", 12)
    tests = probe("tests")
    sec.award(4, tests.get("run", 0) >= 4 and tests.get("failures", 1) == 0,
              f"tests/test_eval.py: {tests.get('run', 0)} tests ran, {tests.get('failures', '?')} failed"
              + (f" ({tests['error'][:300]})" if "error" in tests else ""))
    got, want = probe("stats", cases=STATS_CASES), _expected_stats()
    wrong = [f"{STATS_CASES[k][0]}{tuple(STATS_CASES[k][1]) if k != 'over' else ''}: {got.get(k)!r}, not {v!r}"
             for k, v in want.items() if not _same(got.get(k), v, TOL_INTERVAL if k == "interval" else TOL)]
    sec.share(4, len(want) - len(wrong), len(want), "eval/stats.py on the checker's cases: " + "; ".join(wrong[:3]))
    by = computed.get("by_stratum_arms") or {}
    theirs = computed.get("report_arms") or {}
    wrong = []
    for a, strata in by.items():
        for s, mine in strata.items():
            them = (((theirs.get(a) or {}).get("by_stratum") or {}).get(s)) or {}
            for key in ("runs", "measure", "score", "pass_at_k", "pass_hat_k"):
                if not _same(them.get(key), mine[key], TOL_INTERVAL):
                    wrong.append(f"arm {a}, {s}: {key} {them.get(key)}, recomputed {mine[key]}")
    sec.award(4, bool(by) and not wrong, "; ".join(wrong[:3]) or "nothing to recompute yet: no Part C runs on the subset")
    return sec


def integrity_flags(runs: list[Run]) -> list[str]:
    flags = []
    others = sorted({str(r.start.get("backend")) for r in runs if r.start.get("backend") not in REAL_BACKENDS})
    if others:
        flags.append(f"runs read here came from a backend that is not a vendor's: {', '.join(others)}")
    judges = sorted({str(s["backend"]) for s in judge_sessions().values()
                     if s["backend"] not in REAL_BACKENDS and not is_free(str(s["backend"] or ""))})
    if judges:
        flags.append(f"judge sessions ran on a backend that is not a vendor's: {', '.join(judges)}")
    for rel, wanted in HARNESS_SHA.items():
        if wanted and sha(ROOT / rel) != wanted:
            flags.append(f"`{rel}` differs from the course's copy: your runs or these checks depend on it")
    models = {r.start.get("model") for r in runs}
    if len(models) > 1:
        flags.append(f"the runs name {len(models)} models: {', '.join(sorted(map(str, models)))}")
    return flags


def main(argv: list[str]) -> int:
    if argv[:1] == ["--probe"]:
        print(json.dumps(_probe(json.loads(sys.stdin.read())), default=str))
        return 0
    try:
        report = json.loads((ROOT / "reports" / "LAB_07.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"reports/LAB_07.json could not be read ({exc}); checking what can be checked without it.\n")
        report = {}
    if not isinstance(report, dict):
        report = {}
    g = load_golden()
    runs, scripted = load_runs()
    remote = Remote()
    sections, computed, claim = [], {}, None
    try:
        claim = build_claim(g, runs, remote)
    except Exception:
        print(raised("reading Part C's arms"))
    try:
        sec, _ = check_golden(g)
        sections.append(sec)
    except Exception:
        sections.append(Section("Grounded golden set", 16, notes=[raised("this check")]))
    try:
        sec_claim, computed = check_claim(g, claim, report)
    except Exception:
        sec_claim = Section("Claim settled", 10, notes=[raised("this check")])
    for check, name, pts in [(lambda: check_maths(computed), "The maths", 12),
                             (check_metrics, "Trajectory metrics", 10),
                             (lambda: check_same_tasks(g, claim, runs), "Same tasks, bar first", 10)]:
        try:
            sections.append(check())
        except Exception:
            sections.append(Section(name, pts, notes=[raised("this check")]))
    sections.append(sec_claim)
    for check, name, pts in [(lambda: check_failures(claim, report), "First failures", 6),
                             (lambda: check_judge(report), "Judge validated", 16)]:
        try:
            sections.append(check())
        except Exception:
            sections.append(Section(name, pts, notes=[raised("this check")]))
    sections.append(Section("Read", 20, manual=True, notes=["read by staff from reports/LAB_07.md"]))

    arms = {a: len(claim.arms[a]) for a in ("A", "B")} if claim else {}
    print(f"Assignment 7 check · golden tasks: {len(g.tasks)} · Part C runs: arm A {arms.get('A', 0)}, "
          f"arm B {arms.get('B', 0)} · tracker databases read: {len(remote.files)}")
    if scripted:
        print(f"  {scripted} runs on a scripted model are left out: they test your code, and score nothing")
    print()
    earned = possible = 0.0
    for sec in sections:
        score = "staff" if sec.manual else f"{round(sec.earned, 2):>5g} / {sec.possible:g}"
        print(f"{sec.name:<28} {score}")
        for note in sec.notes:
            for i, line in enumerate(str(note).splitlines()):
                print(f"{'    - ' if i == 0 else '      '}{line}")
        if not sec.manual:
            earned += sec.earned
            possible += sec.possible
    print(f"\nAutomated: {round(earned, 2):g} / {possible:g}   (plus up to 20 from staff for the report)")
    if computed.get("claim"):
        cl = computed["claim"]
        print(f"  measured: the difference {cl['difference']:.3f}, 95% interval [{cl['interval'][0]:.3f}, "
              f"{cl['interval'][1]:.3f}]; verdict by your bar: {cl.get('verdict', 'unknown')}")
    flags = integrity_flags(runs)
    print("\nIntegrity flags (no points; staff review): " + ("none" if not flags else ""))
    for flag in flags:
        print(f"    - Integrity flag: {flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
