#!/usr/bin/env python3
"""Create human-reviewable evidence pages for Assignment 7 Part A.

Place this script in PROJECT_ROOT/notes/review_traces.py, then run:
    python notes/review_traces.py

Only observed facts are extracted. No correctness judgments are generated.
The script never overwrites notes/trace-review.md or golden labels.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def compress(value: object, limit: int = 240) -> str:
    """Keep table cells readable without changing source files."""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    text = str(value or "").replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text.replace("|", "\\|").replace("`", "'")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    project = Path(__file__).resolve().parent.parent
    trace_dir = project / "fixtures" / "traces7"
    pool = project / "fixtures" / "issues" / "pool"
    output_dir = project / "notes" / "trace-evidence"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not trace_dir.is_dir() or not pool.is_dir():
        raise SystemExit("Could not find fixtures; save this script in the project's notes/ folder.")

    paths = sorted(p for p in trace_dir.glob("*.jsonl") if p.name != "s27.jsonl")
    index = [
        "# Historical run evidence — Assignment 7 Part A",
        "",
        "These pages extract facts from the provided traces; they do NOT classify runs as correct or incorrect.",
        "Review at least 40 runs against their original issues and relevant code/resolutions, then write your own first-failure notes in `notes/trace-review.md`.",
        "",
        "| Run | Issue | Tool calls | End reason | Comments | Labels | PRs |",
        "|---|---:|---:|---|---:|---:|---:|",
    ]
    count = 0
    for path in paths:
        events = load_jsonl(path)
        state_path = path.with_suffix(".state.json")
        if not state_path.exists():
            print("SKIP missing state:", path.name)
            continue
        outer = json.loads(state_path.read_text(encoding="utf-8"))
        issue_num = str(outer.get("issue", ""))
        issue_file = pool / (issue_num + ".md")
        issue_source = issue_file.read_text(encoding="utf-8") if issue_file.exists() else "(Original issue file not found)"
        state = outer.get("state", {}).get(issue_num, {})
        tools = [e for e in events if e.get("type") == "tool_call"]
        end = next((e for e in reversed(events) if e.get("type") == "end"), {})
        labels = state.get("labels", [])
        comments = state.get("comments", [])
        prs = state.get("prs", [])
        title = next((line[7:].strip() for line in issue_source.splitlines() if line.startswith("title: ")), "")
        lines = [
            f"# Run: {path.stem}", "",
            f"**Issue:** #{issue_num} — {title}",
            f"**Agent way:** {outer.get('way', '(unknown)')}",
            f"**Termination:** {end.get('terminal_reason', '(missing)')} — {end.get('detail', '')}",
            f"**Source:** `fixtures/traces7/{path.name}`", "",
            "## Original issue", "", issue_source.strip(), "",
            "## Tool calls", "",
            "| Step | Tool | Arguments | Outcome / result excerpt | Error? |",
            "|---:|---|---|---|---|",
        ]
        for e in tools:
            lines.append(
                f"| {e.get('step', '')} | `{e.get('name', '')}` | "
                f"{compress(e.get('input'), 260)} | {compress(e.get('result_excerpt') or e.get('result'), 360)} | "
                f"{e.get('is_error', False)} |"
            )
        lines += [
            "", "## Recorded end state", "",
            f"- Labels: `{json.dumps(labels, ensure_ascii=False)}`",
            f"- Comment count: {len(comments)}",
            f"- PR count: {len(prs)}",
            f"- Closed: `{state.get('closed', '(missing)')}`",
            f"- Merges: `{state.get('merges', '(missing)')}`",
            f"- Pushes: `{json.dumps(state.get('pushes', []), ensure_ascii=False)}`",
            f"- Elsewhere: `{json.dumps(state.get('elsewhere', []), ensure_ascii=False)}`",
            "",
            "### Comments actually posted", "",
        ]
        for n, comment in enumerate(comments, 1):
            lines.append(f"**Comment {n}:**")
            lines.append("````text")
            lines.append(str(comment))
            lines.append("````")
        if not comments:
            lines.append("(none)")
        lines.extend(["", "### PRs actually opened", ""])
        for n, pr in enumerate(prs, 1):
            lines.append(f"**PR {n}:** {pr.get('title', '(untitled)')}")
            lines.append("````text")
            lines.append(str(pr.get("body", "")))
            lines.append("````")
        if not prs:
            lines.append("(none)")
        lines.extend([
            "", "## Human review — complete independently", "",
            "- Decision made (act / refuse / stop): ",
            "- Last correct call (or 'before any call'): ",
            "- First wrong call (or 'none' / 'stopped too early'): ",
            "- First-failure note in your own words: ",
            "- Evidence for correctness: ",
            "", "**Check source code and any closed-issue resolution before deciding.**", "",
        ])
        output_path = output_dir / (path.stem + ".md")
        if not output_path.exists():
            output_path.write_text("\n".join(lines), encoding="utf-8")
        index.append(
            f"| [{path.stem}](trace-evidence/{output_path.name}) | {issue_num} | {len(tools)} | "
            f"{compress(end.get('terminal_reason'), 32)} | {len(comments)} | {len(labels)} | {len(prs)} |"
        )
        count += 1
    (project / "notes" / "trace-evidence-index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"Generated {count} evidence files in notes/trace-evidence/")
    print("Open notes/trace-evidence-index.md for the index.")
    print("Existing notes/trace-review.md was not changed.")


if __name__ == "__main__":
    main()
