"""Reproducible trace-derived trajectory metrics (Assignment 7, section 15.5)."""
from __future__ import annotations
import json

WRITES = frozenset({
    "post_comment", "open_pr", "apply_label", "close_issue", "push_commit", "merge_pr",
    "issues_comment", "pulls_open", "issues_label", "issues_close", "branches_push", "pulls_merge",
})
COMMENT_WRITES = frozenset({"post_comment", "issues_comment"})


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _identifiers(call: dict) -> list[str]:
    paths = [str(x) for x in (call.get("paths") or []) if x]
    if paths:
        return paths
    out = []
    for value in (call.get("input") or {}).values():
        if isinstance(value, (list, tuple)):
            out += [str(x) for x in value if x is not None]
        elif value is not None and not isinstance(value, dict):
            out.append(str(value))
    return out


def _appears(identifier: str, text: str) -> bool:
    identifier, text = identifier.lower(), text.lower()
    if len(identifier) < 3:
        return False
    if identifier in text:
        return True
    name = identifier.rsplit("/", 1)[-1]
    return "/" in identifier and len(name) >= 3 and name in text


def metrics(lines: list[dict], task) -> dict:
    calls = [line for line in lines if line.get("type") == "tool_call"]
    expected = set(task.reference["tools"])
    used = {line["name"] for line in calls}
    seen = set()
    repeats = 0
    for line in calls:
        key = (line["name"], canonical(line.get("input")))
        repeats += key in seen
        seen.add(key)

    comments = [c for c in calls if c["name"] in COMMENT_WRITES]
    final_comment = str((comments[-1].get("input") or {}).get("body") or "") if comments else ""
    orphans = 0
    for index, call in enumerate(calls):
        if call["name"] in WRITES:
            continue
        later = " ".join(canonical(c.get("input")) for c in calls[index + 1:]) + " " + final_comment
        orphans += not any(_appears(identifier, later) for identifier in _identifiers(call))

    ends = [r for r in lines if r.get("type") == "run_end"]
    end = ends[-1] if ends else {}
    return {
        "step_count": len(calls) - int(task.reference["calls"]),
        "precision": len(used & expected) / len(used) if used else None,
        "recall": len(used & expected) / len(expected) if expected else 1.0,
        "repeats": repeats,
        "orphans": orphans,
        "no_tools": not calls,
        "cost_usd": float((end.get("totals") or {}).get("cost_usd") or 0.0),
        "latency_s": float(end.get("elapsed_s") or 0.0),
    }
