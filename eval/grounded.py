"""Assignment 7, Part A, task 5: the grounded check of one run on one golden task
(checks/FORMATS.md, section 15.2).

    from eval.grounded import check, check_run
    result = check(task, state)          # an end state you already have
    result = check_run(run_id, task)     # a run's end state, read from the tracker
    result["passed"], result["facts"], result["why"]

`task` is a golden task (harness.tasks.load_task); `state` is one run's end state as
harness.tasks.end_state returns it from the tracker, or harness.tasks.load_state reads
it from fixtures/traces7/<run_id>.state.json: for each issue, the run's comments, the
labels on it, its open pull requests, whether the run closed it, how many of its pull
requests the run merged, and its pushes (section 15.3).

Return {"passed": bool, "facts": {name: "present" | "missing" | "wrong"}, "why": [str]}:
one entry in `facts` for each fact the task's expected end state must contain, named
as you like; `passed` is True exactly when every fact is present; `why` says, for
each fact that is not, what the state held instead. Read the state, never a model's
words: parse a comment with harness.formats.parse_triage_comment, and look for a
secret with harness.tasks.secret_values.
"""

from __future__ import annotations

from harness.formats import parse_triage_comment  # noqa: F401
from harness.tasks import end_state, secret_values  # noqa: F401
from harness.tracker import Tracker


def check(task, state: dict) -> dict:
    raise NotImplementedError("Part A, task 5")


def check_run(run_id: str, task, tracker: Tracker | None = None) -> dict:
    """The check on a run's end state, read from the tracker."""
    tracker = tracker or Tracker(flaky=False, readback_fail=False)
    return check(task, end_state(tracker, run_id, task))
