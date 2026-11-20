# Assignment 7 — current completion state

## Completed and verified

- Forty independently reviewed/tagged historical traces and nine human-defined
  categories remain unchanged. Last new category at Review #33 followed by
  seven observations supports preliminary, not exhaustive, saturation.
- Thirty source-grounded distinct golden tasks: original 27 plus intended
  behavior, an existing fix and a closed duplicate. Official golden score 16/16.
- Exact reliability/statistics, per-sweep/per-stratum reports and five trajectory
  metrics. Official mathematics 12/12 and trajectory metrics 10/10.
- All 80 real Part C runs: five sweeps × eight frozen tasks × two arms. Recorded
  usage 2,691,051 tokens and priced cost $0.643755, under the unchanged 20-million
  assignment ceiling. All traces, call records, tracker and checkpoints retained.
- Actual pilot SDs and cost produced threshold commit `756817f`, pushed before
  sweep four. Subset/split `a96a722` was pushed before experiments; the design
  and implementation were also committed/pushed first.
- The plan/repeats claim fails: B−A = −0.475, 95% interval
  [−0.736588, −0.213412]. The pilot estimated seven sweeps per arm; the fixed five
  were retained and the power limitation is disclosed.
- All 67 grounded failures have Codex-assisted trace-inspection records with
  call ordinals, actual steps, sources, causes and hashes in `eval/failures_ai.csv`.
  Both grids are computed from these records. These are not student-authored
  human observations or Part D labels.
- Read-only checkpoint diagnostic reproduced the malformed-plan argument loss;
  it is not counted as an experiment or evidence of downstream success.

The checker awards 66/80 with no integrity flags: all Part A–C automated rows
have full credit; the label-independent judge split contributes 2 points.
The current test results and exact remaining status are in
`reports/VERIFICATION_07.md`.

## Remaining human-dependent work

`eval/judge/criterion.md` is an inherited assisted draft until the student writes
or revises it and explicitly confirms authorship. The 60 separate Part D human
labels/reasons must be entered in `eval/labels/labels.csv`. The historical 40
reviews do not replace those labels. No assistant writes or suggests them.

After those inputs are supplied: validate them; develop the generic judge only
on examples/tuning data; commit its configuration; freeze before held-out
inference; run three test passes, versions and historical comments through the
metered client; compute calibration, correction, bootstrap, reliability and
system-specific rates; and complete the final Part D discussion.

Exact commands are in [REMAINING_HUMAN_INPUT_07.md](REMAINING_HUMAN_INPUT_07.md).
All API calls remain under course ceilings; `.env` is ignored and never committed.
No final `lab-07` tag or Canvas completion is claimed while Part D is incomplete.
The staff-reviewed 20 points remain separate from the automated score.
