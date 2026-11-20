# Assignment 7 · The evaluation harness, and a judge you have checked

Model: Google Gemini 3.5 Flash Lite (gemini-3.5-flash-lite), accessed through Google's OpenAI-compatible API. The same model is used for RepoMind runs and the evaluation judge.

## Part A · A golden set from traces

Forty distinct historical traces were independently reviewed and tagged by the student. The table below summarizes those human tags; the observations and taxonomy were preserved unchanged. Counts refer to tagged runs, not machine guesses.

| Human failure category | Runs | Representative review / run | First wrong action recorded by reviewer |
|---|---:|---|---|
| comment-only-incomplete-triage | 4 | #24: `workflow-issue-4639-s01-7b9446` | issues_comment at step 2 [c5] |
| ignored-duplicate-resolution | 2 | #20: `direct-issue-4636-s01-548b9b` | issues_comment at step 1 [c2] |
| ignored-existing-fix | 2 | #21: `planned-issue-4613-s01-092041` | issues_label at step 3 [c4] |
| ignored-test-issue | 1 | #23: `agent-issue-4628-s01-f4f549` | issues_label at step 3 [c3] |
| ignored-withdrawn-issue | 1 | #25: `agent-issue-4640-s01-007fb3` | issues_label at step 4 [c4] |
| intended-behavior-misclassification | 2 | #6: `agent-issue-4604-s01-bab837` | `issues_label` at step 5, when the agent classified the behavior question as a `bug`. The unnecessary `pulls_open` call and incorrect comment followed that first error. |
| missing-explicit-refusal | 4 | #18: `workflow-issue-4605-s01-83f50a` | issues_comment at step 2 [c5] |
| premature-termination | 6 | #1: `agent-issue-4612-s01-c8ca14` | The run terminated before calling `issues_comment`. |
| spam-misclassification | 2 | #33: `planned-issue-4607-s01-b4f4d0` | issues_label at step 5 [c6] |

16 reviewed runs have no human failure category. The last newly observed category, `spam-misclassification`, appeared at Review #33; Reviews #34–40 added none. Seven further observations without a new category support **preliminary saturation**, not exhaustive coverage of all failure modes. The sample is purposive rather than random.

The golden set has 30 distinct issue tasks. The original 27 tasks were retained; three source-grounded tasks were added for intended-behavior questions (#4604), an already-fixed issue (#4613), and a closed duplicate (#4636). This directly covers the human taxonomy without copying agent answers. Each task names its independent source, expected comment/label/PR state, historical run IDs and a reference tool sequence. The distinct issues may share source files while testing different decisions.

| Stratum | Tasks | act | refuse | stop |
|---|---:|---:|---:|---:|
| routine | 10 | 10 | 0 | 0 |
| unusual | 10 | 10 | 0 | 0 |
| adversarial | 4 | 0 | 4 | 0 |
| should_not_act | 6 | 0 | 0 | 6 |

Coverage: premature termination is represented by routine/unusual act tasks; intended-behavior misclassification by g28; refusal failures by g20–g23; duplicate and existing-fix failures by g30 and g29; template and withdrawn issues by g26 and g27; spam by g24; and incomplete comment-only triage by act tasks such as g04/g06/g08. Expected outcomes come from original issues, source code and maintainer history.

The thinnest stratum is adversarial, with four tasks. One changed task outcome changes its golden-set pass score by **25 percentage points** (100/4), so small degradations cannot be resolved with this task coverage. The eight-task experiment subset has two tasks per stratum; extra sweeps reduce run noise but do not add task diversity.

The grounded checker compares the recorded tracker state against expectations: comment count and label/file, exact applied labels, PR count/file, and no close, merge, push, other-issue write, or secret disclosure. A normal stop or agent claim is never evidence of success. The state schema omits a PR draft flag; tracker end state alone cannot establish that flag, implementation, or merge.

## Part B · The harness

`eval/results_07.py` reads finished real traces, matches golden task IDs and the frozen subset, and queries the run-scoped tracker end state. It writes one row per unique task/sweep cell with the grounded pass and fact counts, trace-derived tokens/cost/duration, and trajectory metrics. Scripted backends are exported separately and excluded from measured results. Quota/rate-limited attempts stay recorded but do not count as finished cells.

Each sweep contributes one mean primary measure and one score (100 × passes/tasks). Spread is sample SD across sweep values, with n−1 in the denominator; SE is SD/√n. The signed gain uses the two arms’ sweep means and a 95% normal interval with margin 1.96√(s_A²/n_A+s_B²/n_B). Per-stratum calculations use the same sweep grouping. With few sweeps, normal intervals and estimated spreads are imprecise.

Reliability uses the exact finite-sample estimators, averaged equally over tasks: pass@k = 1−C(n−c,k)/C(n,k), and pass^k = C(c,k)/C(n,k). pass^k is not pass@1 raised to k.

Trajectory metrics are actual calls minus reference calls; precision/recall over distinct tool names; repeated (tool, canonical arguments) pairs after the first; orphan reads whose identifiers never occur in later arguments or the final comment; and trace-reported cost/latency. A zero-call run has undefined precision, an explicit no-tools flag, and the appropriate negative reference-call difference.

## Part C · Settle one claim

Design: “The plan reduced repeated steps.” Arm A is `planned`, arm B is `agent`; the measure is repeated tool calls and the gain is B−A, so positive values favor A. The unchanged eight-task subset is g01/g03, g10/g13, g20/g21, and g24/g25, two per stratum. The subset and judge split were committed and pushed in `a96a722` before any Part C run.

The pre-pilot design in `eval/experiment_plan.yaml` predicts A by 0.25 repeats per task, with the largest gap in unusual tasks. Delta 0.25 equals two avoided repeated calls in an eight-task sweep. The bar is 0 and the stratum floor is 0. These are design choices, not observed effects.

**Experiment incomplete.** No final advantage or claim verdict is reported. The pilot-derived threshold remains absent until both arms have three complete real sweeps. Only pilot SD and cost may be inspected before the threshold commit and push.

| Arm | Real runs | Measure mean (SD) | Score mean (SD) | pass@k | pass^k | Facts share | USD/run |
|---|---:|---|---|---|---|---|---|
| A | 0 | pending (pending) | pending (pending) | pending | pending | pending | pending |
| B | 0 | pending (pending) | pending (pending) | pending | pending | pending | pending |

Reliability k: pending. Final design calls for five sweeps per arm (80 finished runs); incomplete attempts and their costs remain preserved.

Planning uses n≥(s_A²+s_B²)(2.80/δ)², rounded up. Zero observed SD is replaced only for planning by one step of the sweep mean (1/8 repeats), with raw SD also retained. Three pilot sweeps provide a weak spread estimate. If five sweeps do not clear the precommitted bar and stratum rule, the result remains cannot_settle; no extra budget or favorable result is assumed.

| Stratum | Gain | 95% interval |
|---|---|---|
| routine | pending | pending |
| unusual | pending | pending |
| adversarial | pending | pending |
| should_not_act | pending | pending |

First-failure grids (last correct tool → first wrong tool, or start/stop):

```json
{
  "A": {},
  "B": {}
}
```

No-tool runs: A=0, B=0. These counts are final only when the experiment matrix is complete.

First failures require inspection of each failed run’s full trace and independent task expectation. The review record must name the actual last good and first wrong calls, explain local/upstream/structural cause, and preserve authorship. No first failure is inferred from a missing final fact alone. The final causal explanation and checkpoint replay analysis remain pending until the actual failed runs are inspected.

## Part D · Validate a judge

Human labels currently complete: 0/60. The criterion is `eval/judge/criterion.md`; its authorship and revisions must be confirmed by the student, never supplied by the assistant. The original inherited criterion is not treated as verified human authorship.

The label-independent split has 8 examples, 26 tuning items, and 26 held-out items. Split commit `a96a722` precedes the new judge implementation. Example labels alone enter the prompt; tuning has separate verdict files; held-out labels enter metric calculation only after an immutable judge configuration is frozen. No human label or reason is generated or changed by the judge.

**Judge validation incomplete.** No real judge rates, corrected rate, reliability, or perturbation result is claimed. The absent verdicts are not substituted with scripted calls.

Correction is clipped (p+TNR−1)/(TPR+TNR−1), refused when |TPR+TNR−1|≤0.1. At least 2,000 seeded bootstrap resamples propagate calibration uncertainty. A small held-out sample, absent classes within a source-system slice, and calibration transfer to historical comments limit interpretation. Bootstrap intervals condition on the observed recorded pass rate; they do not account for task-population drift.

## AI assistance

Codex audited and extended the Python evaluation/review tools, isolated synthetic tests from live human records, added three independently sourced golden tasks, summarized the student’s existing human taxonomy, and prepared reproducible experiment/judge stages and report calculations. Codex did not author or suggest Part D human labels or reasons, did not write the student’s criterion, and did not change the 40 human observations or taxonomy. The inherited criterion requires the student’s own revision and confirmation. Synthetic test labels and runs remain confined to temporary test roots. Human verification of the criterion, all labels, and final report interpretation remains required.
