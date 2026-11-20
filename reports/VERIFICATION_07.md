# Part C checkpoint verification

- `make test`: **164 tests run, 162 passed, 2 expected skips**, no failures/errors.
- Original `tests.test_eval`: all 11 tests still pass unchanged.
- `make check-07`: **66/80 automated, no integrity flags**. Full credit for
  golden grounding (16), mathematics (12), metrics (10), task/threshold ordering
  (10), the real claim result (10), and all first failures/grids (6). The judge
  split contributes 2; the remaining 14 depend on Part D human input/real verdicts.
- Eight tasks × five sweeps × two arms: exactly 80 real finished result cells,
  no duplicates. All measured models are `gemini-3.5-flash-lite`.
- All 67 failed-run records validate tool names, adjacent call ordinals, actual
  steps, arms and trace hashes. They disclose Codex authorship and are not counted
  as the student's human historical reviews or Part D labels.
- Threshold `756817f` was committed/pushed before sweep four and remains unchanged.
  All 95 pilot measured trace/call files retain their pre-threshold hashes.
- Experiment usage is 2,691,051/20,000,000 tokens; priced run cost $0.643755.
  No over-budget override or model/arm/subset change was made.
- The 40-review document, human taxonomy, task subset and design retain the hashes
  captured at the start of this execution. No human observation was overwritten.
- Tracker and checkpoint SQLite databases pass read-only `PRAGMA integrity_check`.
- The plan-decoding diagnostic used zero model/tool calls and changed no measured
  trace or tracker record. Its counterfactual is not a new experiment result.
- The full checker output is preserved in `CHECK_07_PART_C.txt`; exact run/cost/
  timing metadata is in `PART_C_PROVENANCE_07.json`.

## Remaining work

The human-authored Part D criterion/confirmation and 60 human labels/reasons
remain separate dependencies. No assistant supplies or suggests these labels.
Real development/test/perturbation/historical judge verdicts have not been
claimed as complete. No final lab-07 submission tag or Canvas submission has
been made. The staff-reviewed 20 points require a separate final report audit.

The generic judge draft existed before the initial split in the working tree;
this is disclosed rather than retroactively re-dated. Current code enforces
examples-only prompt labels and a frozen configuration before held-out testing.
