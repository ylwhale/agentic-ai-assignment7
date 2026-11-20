"""Metered judge and calibration maths for Assignment 7 Part D.

The 60 *human* labels are never produced by this module. They must be authored
independently. This module only produces model verdicts in separate files and
statistics that compare those verdicts to the completed human labels.

    python -m eval.judge test 1
    python -m eval.judge test 2
    python -m eval.judge test 3
    python -m eval.judge versions
    python -m eval.judge recorded
    python -m eval.judge test 1 --scripted  # free plumbing, not graded
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
from contextlib import nullcontext
import json
import random
import re
from pathlib import Path

import yaml
from harness import ROOT
from harness.meter import judge_session
from harness.settings import load_settings
from harness.runner import Ledger
from eval import validation_07 as validation
from notes.review_support import atomic_write, json_write

OUTPUTS = ROOT / "fixtures" / "judge" / "outputs"
VERDICTS = ROOT / "eval" / "judge" / "verdicts"
PROMPT = ROOT / "prompts" / "judge.md"


class CoinJudge(ValueError):
    """The judge's sensitivity plus specificity is statistically useless for correction."""


def correct(p: float, tpr: float, tnr: float) -> float:
    denominator = tpr + tnr - 1
    if abs(denominator) <= 0.1 + 1e-12:
        raise CoinJudge("TPR + TNR is within 0.1 of 1; correction is not identifiable")
    return max(0.0, min(1.0, (p + tnr - 1) / denominator))


def rates(verdicts: dict[str, str], labels: dict[str, str]) -> tuple[float, float]:
    positives = [k for k, label in labels.items() if label == "pass" and k in verdicts]
    negatives = [k for k, label in labels.items() if label == "fail" and k in verdicts]
    tpr = sum(verdicts[k] == "pass" for k in positives) / len(positives) if positives else 0.0
    tnr = sum(verdicts[k] == "fail" for k in negatives) / len(negatives) if negatives else 0.0
    return tpr, tnr


def bootstrap(verdicts: dict[str, str], labels: dict[str, str], p: float,
              resamples: int = 2000, seed: int = 0) -> tuple[float | None, float | None]:
    if resamples < 2000:
        raise ValueError("bootstrap requires at least 2000 resamples")
    shared = sorted(k for k in labels if k in verdicts)
    if not shared:
        return None, None
    rng = random.Random(seed)
    estimates = []
    for _ in range(resamples):
        draw = [rng.choice(shared) for _ in shared]
        passes = sum(labels[k] == "pass" for k in draw)
        fails = len(draw) - passes
        if not passes or not fails:
            continue
        tpr = sum(labels[k] == "pass" and verdicts[k] == "pass" for k in draw) / passes
        tnr = sum(labels[k] == "fail" and verdicts[k] == "fail" for k in draw) / fails
        try:
            estimates.append(correct(p, tpr, tnr))
        except CoinJudge:
            continue
    estimates.sort()
    return (estimates[int(0.025 * (len(estimates) - 1))],
            estimates[int(0.975 * (len(estimates) - 1))]) if estimates else (None, None)


def load_outputs(root: Path = ROOT) -> dict[str, dict]:
    return {path.stem: json.loads(path.read_text())
            for path in sorted((root / "fixtures" / "judge" / "outputs").glob("*.json"))}


def _parse(text: str) -> tuple[str, str]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Judge did not return JSON: {cleaned[:150]!r}") from exc
    verdict = str(data.get("answer") or "").strip().lower()
    rationale = str(data.get("reasoning") or "").strip()
    if verdict not in ("pass", "fail") or not rationale or "\n" in rationale:
        raise ValueError(f"Judge reply needs one-line reasoning and Pass/Fail answer: {data!r}")
    return verdict, rationale


def _input(output: dict, comment: str) -> str:
    item = {"issue": output.get("issue"), "tool_evidence": output.get("evidence"), "comment": comment}
    return json.dumps(item, ensure_ascii=False, indent=2)


def _recorded_comments(root: Path = ROOT) -> list[tuple[str, dict]]:
    out = []
    for path in sorted((root / "fixtures" / "traces7").glob("agent-*.jsonl")):
        records = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        comments = [r for r in records if r.get("type") == "tool_call" and
                    r.get("name") in ("issues_comment", "post_comment") and not r.get("is_error")]
        if not comments:
            continue
        before = records[:records.index(comments[-1])]
        evidence = [{"tool": r.get("name"), "input": r.get("input"),
                     "result": r.get("result") or r.get("result_excerpt")}
                    for r in before if r.get("type") == "tool_call"]
        issue_num = records[0].get("issue")
        issue_file = root / "fixtures" / "issues" / "pool" / f"{issue_num}.md"
        issue_text = issue_file.read_text() if issue_file.exists() else f"Issue {issue_num}"
        out.append((path.stem, {"issue": {"number": issue_num, "body": issue_text},
                                "evidence": evidence,
                                "comment": (comments[-1].get("input") or {}).get("body", "")}))
    return out


def _items(kind: str, root: Path = ROOT) -> list[tuple[str, dict, str, str | None]]:
    if kind == "recorded":
        return [(rid, record, record["comment"], None) for rid, record in _recorded_comments(root)]
    parts = validation.split(root)
    selected = parts[kind] if kind in {"examples", "tuning"} else parts["test"]
    items = load_outputs(root)
    if kind == "versions":
        return [(i, items[i], items[i]["versions"][version], version)
                for i in selected for version in ("list", "long")]
    return [(i, items[i], items[i]["comment"], None) for i in selected]


def configuration(root=ROOT):
    settings = load_settings(root/"settings.yaml")
    paths = ("eval/judge.py", "eval/validation_07.py", "prompts/judge.md",
             "eval/judge/criterion.md", "eval/judge/human_criterion.json",
             "eval/labels/split.yaml", "eval/labels/labels.csv", "settings.yaml", "pricing.yaml")
    return {"files":{p:validation.sha(root/p) for p in paths},
            "model":settings.model, "provider":settings.provider,
            "outputs":{p.name:validation.sha(p) for p in sorted((root/"fixtures/judge/outputs").glob("*.json"))}}


def freeze(root=ROOT):
    validation.criterion(root)
    validation.labels(root)
    validation.split(root)
    for relative in ("eval/judge.py", "eval/validation_07.py", "prompts/judge.md", "eval/labels/split.yaml"):
        validation.committed(root,relative)
    path=root/"eval/judge/frozen.json"
    current=configuration(root)
    if path.exists():
        prior=json.loads(path.read_text())
        if prior["configuration"]!=current:
            raise validation.InputError("Existing judge freeze differs; preserve its verdicts and resolve provenance before refreezing")
        return prior
    from harness.clock import now
    record={"frozen_at":now(),"commit":validation.git(root,"rev-parse","HEAD"),
            "configuration":current,
            "development_ids":validation.split(root)["examples"]+validation.split(root)["tuning"]}
    json_write(path,record)
    return record


def check_frozen(root=ROOT):
    path=root/"eval/judge/frozen.json"
    if not path.exists():
        raise validation.InputError("Freeze the judge before testing: python -m eval.judge freeze")
    validation.committed(root,"eval/judge/frozen.json")
    data=json.loads(path.read_text())
    if data["configuration"]!=configuration(root):
        raise validation.InputError("Judge configuration, criterion, labels, or data changed after freezing; do not continue the frozen test")
    return data


def make_prompt(root=ROOT, *, scripted=False):
    """Only examples labels enter the prompt; test labels are never returned here."""
    criterion=(root/"eval/judge/criterion.md").read_text() if scripted else validation.criterion(root)
    base=(root/"prompts/judge.md").read_text()
    examples=[]
    if not scripted:
        ids=validation.split(root)["examples"]
        human=validation.labels(root,allowed=set(ids))
        outputs=load_outputs(root)
        examples=[{"id":i,"input":json.loads(_input(outputs[i],outputs[i]["comment"])),
                   "human_verdict":human[i]} for i in ids]
    return base+"\n\nHuman-authored criterion:\n"+criterion+"\n\nExamples split only:\n"+json.dumps(examples,ensure_ascii=False)


def run_verdicts(kind,number=None,*,root=ROOT,scripted=False,session_factory=judge_session,revision=None):
    if revision and (kind not in {'examples','tuning'} or not re.fullmatch(r'[A-Za-z0-9_-]+',revision)):
        raise validation.InputError('Named revisions are only for examples/tuning development, never held-out test runs')
    name=f"test-{number}" if kind=="test" else kind
    if revision:name+='-'+revision
    out_name=f"{name}_scripted" if scripted else name.replace("-","_")
    output=root/"eval/judge/verdicts"/f"{out_name}.jsonl"
    output.parent.mkdir(parents=True,exist_ok=True)
    if not scripted:
        from eval.experiment_07 import load_local_environment
        load_local_environment(root)
        validation.criterion(root)
        validation.labels(root)
        validation.committed(root,"eval/labels/split.yaml")
        if kind not in {"examples","tuning"}:
            check_frozen(root)
    prompt=make_prompt(root,scripted=scripted)
    prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()
    items=_items(kind,root)
    expected={(i,v) for i,_,_,v in items}
    prior=[json.loads(line) for line in output.read_text().splitlines() if line.strip()] if output.exists() else []
    seen=set()
    for row in prior:
        key=(row.get("id"),row.get("version"))
        if key not in expected or key in seen or row.get("answer") not in {"pass","fail"} or not row.get("reasoning"):
            raise validation.InputError("Existing verdict file has duplicate, unknown or invalid rows; nothing overwritten")
        if not scripted:
            session_path=root/'runs/judge'/f"{row.get('session')}.jsonl"
            if row.get('prompt_sha256')!=prompt_hash or not session_path.is_file():
                raise validation.InputError('Prior verdict lacks matching frozen prompt/session provenance; preserve it and resolve before resuming')
            records=[json.loads(line) for line in session_path.read_text().splitlines() if line.strip()]
            if not records or records[0].get('backend') not in {'anthropic','openai-compatible'}:
                raise validation.InputError('Prior real verdict names a non-vendor session')
        seen.add(key)
    pending=[item for item in items if (item[0],item[3]) not in seen]
    if not pending:
        return len(items)
    backend="harness.scripted:PassEverything" if scripted else None
    settings=load_settings(root/"settings.yaml")
    with session_factory(name,backend=backend,root=root) as session, output.open("a",encoding="utf-8") as sink:
        for index,(item_id,data,comment,version) in enumerate(pending,start=1):
            if not scripted and Ledger(root/"runs/_ledger.jsonl").spent_tokens()+session.client.total_tokens >= settings.lab_token_ceiling:
                raise validation.InputError("Lab token ceiling reached; no further judge calls started")
            response=session.client.create(system=prompt,messages=[{"role":"user","content":_input(data,comment)}])
            session.trace.model_call(index,response,purpose="judge")
            answer,reasoning=_parse(response.text)
            row={"id":item_id,"answer":answer,"reasoning":reasoning,"session":session.id,"model":response.model,
                 "prompt_sha256":prompt_hash,"call_step":index}
            if version:row["version"]=version
            sink.write(json.dumps(row,ensure_ascii=False)+"\n")
            sink.flush();os.fsync(sink.fileno())
    return len(items)


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind",choices=("examples","tuning","freeze","test","versions","recorded"))
    p.add_argument("number",type=int,nargs="?")
    p.add_argument("--scripted",action="store_true",help="free plumbing, never human labels or graded evidence")
    p.add_argument('--revision',help='preserve a separate examples/tuning prompt-development iteration')
    args=p.parse_args(argv)
    if args.kind=="test" and args.number not in (1,2,3):p.error("test requires number 1, 2 or 3")
    if args.kind!="test" and args.number is not None:p.error("only test takes a run number")
    try:
        if args.kind=="freeze":
            freeze();print("Judge configuration frozen. Commit and push eval/judge/frozen.json before test runs.")
        else:
            count=run_verdicts(args.kind,args.number,scripted=args.scripted,revision=args.revision)
            print(f"{count} verdicts complete for {args.kind}; existing verdicts preserved.")
            if args.scripted:print("SCRIPTED plumbing only; excluded from assignment evidence.")
    except (validation.InputError,ValueError,OSError) as exc:
        p.exit(2,str(exc)+"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
