"""Assignment 7 run-result exporter, from authoritative trace and tracker data.

Usage:
  python -m eval.results_07 --arm A --way planned --claim plan
  python -m eval.results_07 --arm B --way agent --claim plan
  python -m eval.results_07 --arm A --way planned --claim plan --scripted
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from harness import LAB, ROOT
from harness import switches as switch_board
from harness.backends import REAL_BACKENDS
from harness.formats import UNFINISHED
from harness.tasks import end_state, load_tasks, read_subset
from harness.trace import read_trace
from harness.tracker import Tracker
from eval.grounded import check
from eval.metrics import metrics
from notes.review_support import atomic_write


def finished_runs(way: str, switches: dict | None = None, root: Path = ROOT,
                  scripted: bool = False) -> list[list[dict]]:
    want = {**switch_board.DEFAULTS, **(switches or {})}
    out = []
    for path in sorted((root / "runs").glob("*.jsonl")):
        if path.name.startswith("_") or path.name.count(".") > 1:
            continue
        lines = read_trace(path)
        start = lines[0] if lines else {}
        if start.get("type") != "run_start" or start.get("lab") != LAB or start.get("way") != way:
            continue
        if {**switch_board.DEFAULTS, **(start.get("switches") or {})} != want:
            continue
        free = str(start.get("backend", "")).startswith("harness.scripted:") or start.get("backend") == "never-stops"
        if free != scripted:
            continue
        if not scripted and start.get('backend') not in REAL_BACKENDS:
            continue
        ends = [r.get("terminal_reason") for r in lines if r.get("type") == "end"]
        if not lines or lines[-1].get("type") != "run_end" or set(ends) & set(UNFINISHED):
            continue
        out.append(lines)
    return out


def call_record(run_id: str, root: Path = ROOT) -> list[dict]:
    path = root / "runs" / f"{run_id}.calls.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def _wasted(run_id: str, root: Path = ROOT) -> int:
    count = 0
    for line in call_record(run_id, root):
        if line.get("outcome") in ("rejected", "error", "protocol"):
            count += 1
        elif line.get("role") == "search" and re.search(r'"count":\s*0\b', str(line.get("result") or "")):
            count += 1
    return count


def _measure(claim: str, lines: list[dict], met: dict, passed: bool,
             state: dict, issue: int, run_id: str, root: Path) -> float | int:
    if claim == "tokens":
        return int((lines[-1].get("totals") or {}).get("total_tokens") or 0)
    if claim == "plan":
        return met["repeats"]
    if claim == "examples":
        return _wasted(run_id, root)
    if claim == "checkpoint":
        this = state.get(issue) or {}
        return max(0, len(this.get("comments") or []) - 1) + max(0, len(this.get("prs") or []) - 1)
    if claim == "split":
        return 100 if passed else 0
    raise ValueError(f"Unrecognized claim {claim!r}")


def build_rows(arm: str, way: str, claim: str, *, switches: dict | None = None,
               tasks_path: str = "eval/golden/v1/tasks", subset_path: str = "eval/subsets/claim.txt",
               scripted: bool = False, root: Path = ROOT) -> list[dict]:
    tasks = {t.id: t for t in load_tasks(root / tasks_path)}
    subset = set(read_subset(root / subset_path))
    tracker = Tracker(root, flaky=False, readback_fail=False)
    output = []
    for lines in finished_runs(way, switches=switches, scripted=scripted, root=root):
        first, last = lines[0], lines[-1]
        tid = first.get("task")
        if tid not in tasks or tid not in subset:
            continue
        task, run_id = tasks[tid], first["run_id"]
        state = end_state(tracker, run_id, task)
        grounded = check(task, state)
        met = metrics(lines, task)
        facts = grounded["facts"]
        present = sum(v == "present" for v in facts.values())
        output.append({
            "arm": arm, "way": way, "switches": first.get("switches") or switch_board.DEFAULTS,
            "run_id": run_id, "task": task.id, "stratum": task.stratum, "sweep": first.get("sweep"),
            "passed": grounded["passed"], "facts": {"present": present, "total": len(facts)},
            "measure": _measure(claim, lines, met, grounded["passed"], state, task.issue, run_id, root),
            "tokens": int((last.get("totals") or {}).get("total_tokens") or 0),
            "cost_usd": float((last.get("totals") or {}).get("cost_usd") or 0.0),
            "wall_clock_s": float(last.get("elapsed_s") or 0.0), "metrics": met,
            "started_at": first.get("started_at"),
            "terminal_reason": next((r.get('terminal_reason') for r in reversed(lines) if r.get('type')=='end'),None),
        })
    cells = [(r['task'],r['sweep']) for r in output]
    if len(cells) != len(set(cells)):
        raise ValueError('Duplicate finished task/sweep runs; preserve traces and resolve before exporting')
    return sorted(output, key=lambda x: (x["sweep"] or 0, x["task"], x["run_id"]))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arm", required=True, choices=("A", "B"))
    p.add_argument("--way", required=True)
    p.add_argument("--switch", action="append", default=[], metavar="NAME=VALUE")
    p.add_argument("--claim", required=True, choices=("tokens", "plan", "examples", "checkpoint", "split"))
    p.add_argument("--tasks", default="eval/golden/v1/tasks")
    p.add_argument("--subset", default="eval/subsets/claim.txt")
    p.add_argument("--scripted", action="store_true")
    args = p.parse_args(argv)
    switches = {}
    for value in args.switch:
        if "=" not in value:
            p.error(f"--switch must be NAME=VALUE, got {value!r}")
        name, setting = value.split("=", 1)
        name = name.lower()
        if name in ("flaky_writes", "readback_fail"):
            setting = setting.strip().lower() in ("true", "1", "on", "yes")
        switches[name] = setting
    rows = build_rows(args.arm, args.way, args.claim, switches=switches,
                      tasks_path=args.tasks, subset_path=args.subset, scripted=args.scripted)
    target = ROOT / "results" / (f"scripted_{args.arm}.jsonl" if args.scripted else f"{args.arm}.jsonl")
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(target,"".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    print(f"{len(rows)} finished {'scripted' if args.scripted else 'real'} runs -> {target.relative_to(ROOT)}")
    if not args.scripted and not rows:
        print("No live runs found. This is not evidence that the claim was tested.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
