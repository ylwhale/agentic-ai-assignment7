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

## Remaining work at the Part C checkpoint (historical)

The human-authored Part D criterion/confirmation and 60 human labels/reasons
remain separate dependencies. No assistant supplies or suggests these labels.
Real development/test/perturbation/historical judge verdicts have not been
claimed as complete. No final lab-07 submission tag or Canvas submission has
been made. The staff-reviewed 20 points require a separate final report audit.

The generic judge draft existed before the initial split in the working tree;
this is disclosed rather than retroactively re-dated. Current code enforces
examples-only prompt labels and a frozen configuration before held-out testing.

## Final Assignment 7 verification — November 20, 2026

The earlier 66/80 result represents the Part C checkpoint, before Part D was completed. The final working copy now includes the completed human reviews, judge criterion, reference labels, and judge validation results.

### Automated Verification

- `make test`: 164 tests run, 162 passed, 2 expected skips, with no failures or errors.
- `make check-07`: **80/80 automated points, no integrity flags**.
- All seven automated grading categories pass.

### Completed Human Work

- **Part A:** 40 historical traces were independently reviewed, and 30 golden tasks were labeled using the original issues, source code, and maintainer resolutions.
- **Part D:** The judge criterion was independently reviewed and finalized. All 60 reference outputs were independently labeled with supporting reasons.
- The older review documentation format and completed human-work records are explained in `notes/HUMAN_WORK_PROVENANCE_07.md`.

### Judge Validation

- The 60 completed reference labels are stored in `eval/labels/labels.csv`.
- The finalized judge criterion is stored in `eval/judge/criterion.md`.
- Judge validation outputs include three test runs, formatting and length perturbations, and recorded-run verdicts.
- The automated checker successfully validates the judge results and their reported statistics.
