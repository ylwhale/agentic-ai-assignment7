#!/usr/bin/env python3
"""Prepare and apply independently verified historical trace reviews.

Commands:
    python notes/batch_review.py prepare
    python notes/batch_review.py status
    python notes/batch_review.py inspect --run agent-issue-4618-s01-f00cae
    python notes/batch_review.py apply

The prepare step extracts facts and warning flags; it NEVER supplies human
judgments or claims that a run has been reviewed. The apply step imports only
rows explicitly completed and verified by the reviewer, with a safety backup.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path

try:
    from . import review_support as support
except ImportError:
    try:
        import review_support as support
    except ImportError:
        from notes import review_support as support

try:
    import yaml
except ImportError as exc:
    raise SystemExit("Install project requirements first: make setup") from exc

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "notes"
EVIDENCE = NOTES / "trace-evidence"
DOCUMENT = NOTES / "trace-review.md"
OUT = NOTES / "batch_review"
QUEUE = OUT / "queue.csv"
PREVIEW = OUT / "evidence-summary.md"
CLOSED = ROOT / "fixtures" / "closed_issues.yaml"

HUMAN_FIELDS = (
    "expected_decision", "actual_decision", "last_correct_call",
    "first_incorrect_call", "observation", "assessment", "source_checked",
    "verified",
)
FIELDS = (
    "run_id", "issue", "title", "way", "termination", "tool_count",
    "last_observed_tool", "last_observed_step", "labels", "comment_count",
    "pr_count", "merges", "pushes", "elsewhere", "mechanical_flags",
    "maintainer_resolution", "evidence_file",
    "machine_candidate_expected", "machine_candidate_last_observed",
    "machine_candidate_first_failure", "machine_candidate_assessment",
    "machine_draft_observation", *HUMAN_FIELDS,
)
CHOICES = {"act", "refuse", "stop"}
ASSESSMENTS = {"successful", "failed", "uncertain"}
VERIFIED = {"yes", "true", "verified"}


def completed() -> set[str]:
    if not DOCUMENT.exists():
        raise SystemExit(f"Missing review file: {DOCUMENT}")
    return set(support.review_blocks(DOCUMENT.read_text(encoding="utf-8")))


def ordered_evidence() -> list[Path]:
    paths = sorted(EVIDENCE.glob("*.md"))
    return [p for p in paths if p.name.startswith("agent-")] + [p for p in paths if not p.name.startswith("agent-")]


def resolutions() -> dict[int, str]:
    records = yaml.safe_load(CLOSED.read_text(encoding="utf-8"))
    return {int(record["issue"]): str(record["resolution"]) for record in records}


def pick(pattern: str, content: str, default: str = "") -> str:
    m = re.search(pattern, content, flags=re.M)
    return m.group(1).strip() if m else default


def parse_evidence(path: Path, closed: dict[int, str]) -> tuple[dict[str, str], list[tuple[str, str]]]:
    content = path.read_text(encoding="utf-8")
    issue_match = re.search(r"^\*\*Issue:\*\*\s*#(\d+)\s+\S+\s+(.+)", content, re.M)
    if not issue_match:
        raise ValueError(f"Can't parse issue heading: {path}")
    number, title = issue_match.groups()
    tool_section = content.split("## Tool calls", 1)[-1].split("## Recorded end state", 1)[0]
    calls = []
    for line in tool_section.splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|\s*`([A-Za-z_][A-Za-z_0-9]*)`\s*\|", line)
        if m:
            calls.append((m.group(1), m.group(2)))
    last_step, last_tool = calls[-1] if calls else ("", "")
    termination = pick(r"^\*\*Termination:\*\*\s*(.*)", content)
    labels = pick(r"^- Labels:\s*(.*)", content).strip("`")
    comments = pick(r"^- Comment count:\s*(\d+)", content, "0")
    prs = pick(r"^- PR count:\s*(\d+)", content, "0")
    merges = pick(r"^- Merges:\s*(.*)", content, "0").strip("`")
    pushes = pick(r"^- Pushes:\s*(.*)", content, "[]").strip("`")
    elsewhere = pick(r"^- Elsewhere:\s*(.*)", content, "[]").strip("`")
    flags = []
    if "turn_limit" in termination or "token_budget" in termination:
        flags.append("BOUNDS_TERMINATION")
    if comments == "0":
        flags.append("NO_COMMENT_RECORDED")
    if prs != "0":
        flags.append("PR_OPENED_CHECK_NECESSITY")
    if merges not in {"0", ""} or pushes not in {"[]", "", "0"} or elsewhere not in {"[]", "", "0"}:
        flags.append("CHECK_UNAUTHORIZED_WRITES")
    resolution = closed.get(int(number), "")
    if re.search(r"\b(no change|nothing changed|already fixed|duplicate|withdrawn|declined|deleted)\b", resolution, flags=re.I):
        flags.append("CHECK_NO_CHANGE_OR_REFUSAL_EXPECTATION")
    # Tentative machine-only hints. These are NEVER imported as human fields.
    if re.match(r"(?i)^(fixed|done|docs updated)", resolution):
        candidate_expected = "act (provisional)"
    else:
        candidate_expected = "inspect issue and maintainer history"
    if "turn_limit" in termination and comments == "0":
        candidate_failure = "stopped too early IF a triage action was required"
        candidate_assessment = "possible incomplete workflow; verify"
    else:
        candidate_failure = "not inferred; inspect each tool and final state"
        candidate_assessment = "not inferred; check correctness and authorization"
    candidate_last = f"{last_tool} at step {last_step}" if calls else "before any call"
    draft_observation = (
        f"Machine-extracted only: Run {path.stem} ended {termination}; "
        f"recorded {len(calls)} tool calls, {comments} comments, {prs} PRs, "
        f"labels {labels}. The last OBSERVED call was {candidate_last}; "
        f"it is not necessarily correct. Independently compare every action "
        f"with the original issue, source code, and maintainer history."
    )
    row = {
        "run_id": path.stem, "issue": number, "title": title, "way": pick(r"^\*\*Agent way:\*\*\s*(.*)", content),
        "termination": termination, "tool_count": str(len(calls)),
        "last_observed_tool": last_tool, "last_observed_step": last_step,
        "labels": labels, "comment_count": comments, "pr_count": prs,
        "merges": merges, "pushes": pushes, "elsewhere": elsewhere,
        "mechanical_flags": ";".join(flags),
        "maintainer_resolution": resolution if resolution else "NO CLOSED-ISSUE RESOLUTION; inspect original code",
        "evidence_file": f"notes/trace-evidence/{path.name}",
        "machine_candidate_expected": candidate_expected,
        "machine_candidate_last_observed": candidate_last,
        "machine_candidate_first_failure": candidate_failure,
        "machine_candidate_assessment": candidate_assessment,
        "machine_draft_observation": draft_observation,
    }
    return row, calls


def read_queue() -> dict[str, dict[str, str]]:
    if not QUEUE.exists():
        return {}
    with QUEUE.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len({r['run_id'] for r in rows}):
        raise ValueError('Duplicate run ID in queue.csv; no rows were discarded')
    return {r['run_id']: r for r in rows}


def write_queue(rows: list[dict[str, str]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    import io
    stream = io.StringIO(newline='')
    with stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        support.atomic_write(QUEUE, stream.getvalue())


def prepare() -> None:
    if (ROOT / 'fixtures/traces7').is_dir():
        store = support.Store(ROOT)
        packets = store.prepare(FIELDS)
        print(f'Prepared {len(packets)-len(store.blocks())} pending evidence packets; human fields preserved.')
        print('No permanent reviews or human judgments generated. Start: python notes/review_fast.py')
        return
    done = completed()
    old = read_queue()
    closed = resolutions()
    rows = []
    preview = [
        "# Historical trace review - machine-extracted evidence",
        "",
        "**NOT HUMAN REVIEWED.** These facts and warnings are a preparation aid.",
        "Do not count or submit an item as a reviewed run until you inspect it and",
        "complete its human fields in queue.csv with `verified=yes`.", "",
        f"Existing reviewed runs in permanent notes: **{len(done)}**.", "",
    ]
    for path in ordered_evidence():
        if path.stem in done:
            continue
        row, calls = parse_evidence(path, closed)
        prior = old.get(path.stem, {})
        for field in HUMAN_FIELDS:
            row[field] = prior.get(field, "")
        rows.append(row)
        preview.extend([
            f"## {row['run_id']} - issue #{row['issue']}", "",
            f"- **Issue:** {row['title']}",
            f"- **Way / termination:** `{row['way']}` / `{row['termination']}`",
            f"- **Recorded final state:** labels {row['labels']}; comments {row['comment_count']}; PRs {row['pr_count']}; merges {row['merges']}; pushes {row['pushes']}; elsewhere {row['elsewhere']}",
            f"- **Last observed call (NOT necessarily last correct):** `{row['last_observed_tool']}` at step {row['last_observed_step']}",
            f"- **Mechanical warning flags (NOT failure judgments):** {row['mechanical_flags'] or 'none'}",
            f"- **Provisional expected decision (MACHINE, UNVERIFIED):** {row['machine_candidate_expected']}",
            f"- **Provisional first failure (MACHINE, UNVERIFIED):** {row['machine_candidate_first_failure']}",
            f"- **Provisional assessment (MACHINE, UNVERIFIED):** {row['machine_candidate_assessment']}",
            f"- **Machine observation draft (NOT a human assessment):** {row['machine_draft_observation']}",
            f"- **Maintainer history:** {row['maintainer_resolution']}",
            f"- **Complete source:** `{row['evidence_file']}`", "",
            "| Step | Tool |", "|---|---|",
        ])
        preview.extend(f"| {step} | `{tool}` |" for step, tool in calls)
        preview.extend(["", "**Human decision, first failure, own observation:** not generated.", "", "---", ""])
    write_queue(rows)
    PREVIEW.write_text("\n".join(preview) + "\n", encoding="utf-8")
    print(f"Prepared {len(rows)} pending reviews in {QUEUE.relative_to(ROOT)}")
    print(f"Evidence summary: {PREVIEW.relative_to(ROOT)}")
    print("Existing verified entries in queue.csv were preserved by run ID.")
    print("No permanent reviews were added and no manual labels were generated.")


def ready_row(row: dict[str, str]) -> tuple[bool, str]:
    if (row.get("verified") or "").strip().lower() not in VERIFIED:
        return False, "not marked verified=yes"
    missing = [field for field in HUMAN_FIELDS[:-1] if not (row.get(field) or "").strip()]
    if missing:
        return False, "missing " + ", ".join(missing)
    if row["expected_decision"].lower() not in CHOICES:
        return False, "expected_decision must be act/refuse/stop"
    if row["assessment"].lower() not in ASSESSMENTS:
        return False, "assessment must be successful/failed/uncertain"
    if len(row["observation"].strip()) < 40:
        return False, "observation must be at least 40 characters"
    if re.search(r"[\r\n]", row["first_incorrect_call"]):
        return False, "first_incorrect_call cannot be multiline"
    if (ROOT / 'fixtures/traces7').is_dir():
        try:
            packet = support.extract(ROOT,row['run_id'])
            checked = dict(row)
            for name in ('last_correct_call','first_incorrect_call'):
                checked[name] = support.resolve_call(row.get(name,''),packet,first=name=='first_incorrect_call')
            errors = support.validate_record(checked,packet,ROOT)
        except ValueError as exc:
            return False, str(exc)
        if errors:
            return False, '; '.join(errors)
    return True, ""


def review_section(row: dict[str, str], number: int) -> str:
    maintainer = row["maintainer_resolution"]
    return "\n".join([
        f"## Run {number} - Issue #{row['issue']}", "",
        f"**Run ID:** `{row['run_id']}`", "",
        f"**Issue title:** {row['title']}", "",
        f"**Agent implementation:** `{row['way']}`", "",
        f"**Full original evidence:** `{row['evidence_file']}`", "",
        "### Recorded End State (mechanically extracted)", "",
        f"- Termination: `{row['termination']}`",
        f"- Labels: {row['labels']}",
        f"- Comments: {row['comment_count']}",
        f"- PRs: {row['pr_count']}",
        f"- Merges: {row['merges']}; pushes: {row['pushes']}; other writes: {row['elsewhere']}", "",
        "### Human Review Findings", "",
        f"**Expected decision:** {row['expected_decision']}", "",
        f"**Actual decision:** {row['actual_decision']}", "",
        f"**Last correct call:** {row['last_correct_call']}", "",
        f"**First incorrect call:** {row['first_incorrect_call']}", "",
        f"**My observation:** {row['observation']}", "",
        f"**Assessment:** {row['assessment']}", "",
        "### Independent Evidence", "",
        f"**Source checked:** {row['source_checked']}", "",
        f"**Maintainer resolution:** {maintainer}", "",
        "---", "",
    ]) + "\n"


def apply(dry_run: bool = False) -> None:
    if not QUEUE.exists():
        raise SystemExit("No queue.csv found. Run 'prepare' first.")
    if (ROOT / 'fixtures/traces7').is_dir():
        store = support.Store(ROOT)
        done = completed()
        ready = []
        errors = []
        for run, row in read_queue().items():
            # Identity is checked even for unverified rows.
            if not (ROOT / 'fixtures/traces7' / (run + '.jsonl')).is_file() or run == 's27':
                errors.append(f'{run}: unknown historical run')
                continue
            if run in done or (row.get('verified') or '').lower() not in VERIFIED:
                continue
            packet = support.extract(ROOT, run)
            for name in ('last_correct_call','first_incorrect_call'):
                try:
                    row[name] = support.resolve_call(row.get(name,''),packet,first=name=='first_incorrect_call')
                except ValueError as exc:
                    errors.append(f'{run}: {name}: {exc}')
            errors.extend(f'{run}: {msg}' for msg in support.validate_record(row,packet,ROOT))
            for msg in support.observation_warnings(row,packet):
                print(f'WARNING {run}: {msg}')
            ready.append((row,packet))
        errors.extend(store.preservation_errors())
        if errors:
            print('Nothing written:\n' + '\n'.join(errors))
            raise SystemExit(2)
        print(f'Verified and ready to import: {len(ready)}')
        if not dry_run:
            for row, packet in ready:
                # verified=yes in the human-edited CSV is the explicit confirmation
                # contract of the existing batch interface. No value is inferred.
                count = store.save(row,packet,confirmed=True)
                print(f"Saved {row['run_id']}; permanent total {count}/40")
        return
    done = completed()
    rows = list(read_queue().values())
    ready = []
    invalid = []
    for row in rows:
        if row["run_id"] in done:
            continue
        if (row.get("verified") or "").strip().lower() in VERIFIED:
            valid, msg = ready_row(row)
            (ready if valid else invalid).append(row if valid else (row["run_id"], msg))
    if invalid:
        print("Some verified rows are incomplete or invalid. Nothing was written:")
        for run, msg in invalid:
            print(f"  {run}: {msg}")
        raise SystemExit(2)
    print(f"Verified and ready to import: {len(ready)}")
    if not ready or dry_run:
        return
    document = DOCUMENT.read_text(encoding="utf-8")
    marker = "## Template - Additional Run Reviews"
    # Existing hand-edited notes use an em dash in this marker.
    if marker not in document:
        marker = "## Template \u2014 Additional Run Reviews"
    if marker not in document:
        raise SystemExit("Cannot find review template marker; no changes made.")
    count = len(done)
    new_sections = []
    new_issues = []
    for row in ready:
        count += 1
        new_sections.append(review_section(row, count))
        new_issues.append(row["issue"])
    new_document = document.replace(marker, "\n".join(new_sections) + "\n" + marker, 1)
    new_document = re.sub(r"\*\*Runs reviewed so far:\*\*\s*\d+", f"**Runs reviewed so far:** {count}", new_document, count=1)
    new_document = re.sub(r"\*\*Runs remaining to meet the minimum:\*\*\s*\d+", f"**Runs remaining to meet the minimum:** {max(0, 40-count)}", new_document, count=1)
    match = re.search(r"\*\*Issues examined:\*\*[^\n]*", new_document)
    if match:
        for issue in new_issues:
            if not re.search(rf"#{issue}(?![0-9])", new_document[match.start():match.end()]):
                new_document = new_document[:match.end()] + f", #{issue}" + new_document[match.end():]
                match = re.search(r"\*\*Issues examined:\*\*[^\n]*", new_document)
    backup_dir = OUT / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = backup_dir / f"trace-review-{stamp}.md"
    backup.write_text(document, encoding="utf-8")
    support.atomic_write(DOCUMENT, new_document)
    print(f"Saved {len(ready)} independently verified reviews. Permanent total: {count}/40")
    print(f"Backup: {backup.relative_to(ROOT)}")
    print("Re-run prepare to remove the imported rows from the pending queue.")


def status() -> None:
    done = completed()
    pending = [p.stem for p in ordered_evidence() if p.stem not in done]
    queue = read_queue()
    ready = sum(1 for run, row in queue.items() if run not in done and ready_row(row)[0])
    print(f"Permanent reviews: {len(done)}/40; still needed: {max(0, 40-len(done))}")
    print(f"Pending traces: {len(pending)}; verified queue rows ready to apply: {ready}")
    if pending:
        print("Next: " + ", ".join(pending[:8]))
    if not QUEUE.exists():
        print("No queue yet. Run: python notes/batch_review.py prepare")


def inspect(run_id: str, full: bool = False) -> None:
    if (ROOT / 'fixtures/traces7').is_dir():
        packet = support.extract(ROOT,run_id)
        if full:
            print(support.render_packet(packet,source_limit=1000))
            print('FULL RECORDED TOOL INPUTS/RESULTS, CONTROL EVENTS AND STATES:')
            print(json.dumps({k:packet[k] for k in ('calls','control_events','all_recorded_states')},ensure_ascii=False,indent=2))
        else:
            row = support.machine_row(packet)
            for key in ('run_id','issue','title','way','termination','labels','comment_count','pr_count','mechanical_flags','maintainer_resolution','evidence_file'):
                print(f'{key}: {row[key]}')
            for call in packet['calls']:
                print(f"  c{call['call']}: step {call['step']}: {call['name']}")
            print(f'Full evidence: python notes/batch_review.py inspect --run {run_id} --full')
        return
    path = EVIDENCE / (run_id + ".md")
    if not path.is_file():
        raise SystemExit(f"Trace not found: {path}")
    if full:
        print(path.read_text(encoding="utf-8"))
    else:
        row, calls = parse_evidence(path, resolutions())
        for field in ("run_id", "issue", "title", "way", "termination", "labels", "comment_count", "pr_count", "mechanical_flags", "maintainer_resolution", "evidence_file"):
            print(f"{field}: {row[field]}")
        print("Tool calls:")
        for step, tool in calls:
            print(f"  step {step}: {tool}")
        print("To inspect original issue, tool outputs, comments and PRs:")
        print(f"  python notes/batch_review.py inspect --run {run_id} --full")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare", help="Generate/refresh evidence queue, preserving human fields")
    sub.add_parser("status", help="Check completed and pending reviews")
    ins = sub.add_parser("inspect", help="Inspect one source trace")
    ins.add_argument("--run", required=True, help="Exact run ID")
    ins.add_argument("--full", action="store_true", help="Print unabridged evidence")
    app = sub.add_parser("apply", help="Import only validated, verified queue rows")
    app.add_argument("--dry-run", action="store_true", help="Show how many would be imported")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "status":
        status()
    elif args.command == "inspect":
        inspect(args.run, args.full)
    else:
        apply(args.dry_run)


if __name__ == "__main__":
    main()
