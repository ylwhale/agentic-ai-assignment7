"""Assignment 7, Part B, task 4: five trajectory metrics, by counting (slide 26;
checks/FORMATS.md, section 15.5).

    from eval.metrics import metrics
    metrics(lines, task)
    # {"step_count": 3, "precision": 0.8, "recall": 1.0, "repeats": 1, "orphans": 1,
    #  "no_tools": False, "cost_usd": 0.0412, "latency_s": 18.2}

`lines` is one run's trace, as a list of dicts (one per JSON line of
runs/<run_id>.jsonl, or of a recorded run in fixtures/traces7/); `task` is its golden
task, whose `reference` holds the calls and tools a good run makes. The definitions,
exactly; the checker counts the same way on the recorded runs:

- A **call** is a `tool_call` line, in order, whatever it returned. A resumed run's
  calls are every `tool_call` line, before its `resume` line and after.
- **step_count**: the run's calls, minus the task's reference count,
  `task.reference["calls"]`.
- **precision**: of the distinct tool names the run called, the share that are in the
  task's reference tools, `task.reference["tools"]`; None when it called none.
- **recall**: of the reference tools, the share the run called at least once.
- **repeats**: the calls whose name and input are identical to an earlier call's,
  each extra call counted once. Compare inputs in canonical form, keys sorted and no
  whitespace, as `canonical` below writes them.
- **orphans**: the reads whose output no later step uses. A read is a call whose
  name is not in WRITES. Its identifiers are the paths it returned (its `paths`), or,
  when it returned none, the values in its input as text: every value that is not
  null and not an object, a list's items one by one, numbers and booleans written as
  Python's str() writes them. A read is used when one of
  its identifiers appears, ignoring case, in the canonical input of a later call or
  in the run's final comment, the `body` of its last call in COMMENT_WRITES; a path
  also appears when its file name alone does (`exportUtils.ts` for
  `src/exportUtils.ts`). Only identifiers of three characters or more count.
- **no_tools**: True when the run made no call at all (slide 28).
- **cost_usd** and **latency_s**: the last `run_end` line's `totals.cost_usd` and
  `elapsed_s`.

Slide 27's trace, fixtures/traces7/s27.jsonl with fixtures/traces7/s27.task.yaml,
gives 3, 0.8, 1.0, 1 and 1.
"""

from __future__ import annotations

import json

# Writes, by role name and by RepoMind's tool names: their output is what they changed,
# so none is ever an orphan.
WRITES = frozenset({
    "post_comment", "open_pr", "apply_label", "close_issue", "push_commit", "merge_pr",
    "issues_comment", "pulls_open", "issues_label", "issues_close", "branches_push", "pulls_merge",
})
COMMENT_WRITES = frozenset({"post_comment", "issues_comment"})


def canonical(value) -> str:
    """A tool input in one standard form: keys sorted, no whitespace."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def metrics(lines: list[dict], task) -> dict:
    raise NotImplementedError("Part B, task 4")
