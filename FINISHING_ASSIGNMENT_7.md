# Assignment 7 — current completion state

The repository has 40 independently reviewed/tagged historical traces and nine
human-defined categories. Their document and taxonomy are preserved unchanged.
The last new category was seen at Review #33, followed by seven observations
without a new category: preliminary saturation, not exhaustive saturation.

The golden set now has 30 source-grounded distinct issue tasks. The original
27 were retained and g28–g30 cover intended behavior, an existing fix and a
closed duplicate. The official grounded check remains 16/16; trajectory metrics
remain 10/10. Numerical functions pass the official probes; the final four
mathematics points require actual Part C data and its stratum summaries.

The original review-helper failures were caused by copying the growing human
ledger into tests that expected 17 entries. Tests now use a deterministic
synthetic ledger in a temporary root, preserving the original safety checks.
No human work was changed to fit a test.

The unchanged eight-task subset and label-independent 8/26/26 judge split were
committed and pushed as `a96a722` before real experiments and the new judge code.
Origin uses the equivalent working HTTPS URL after SSH authentication failed.
No Git timestamps, histories, results or labels were fabricated.

The permitted programming is implemented: exact statistics and SE; complete
experiment matrices; trace/tracker-backed exports; spread-only pilots; a genuine
pilot-derived threshold with commit/push gates; actual failed-trace evidence;
protected human label entry; examples-only judge prompts; a frozen and resumable
metered judge; calibration, correction/coin guard, bootstrap, reliability and
perturbation summaries; and reports that retain pending values when evidence is
absent. All model calls remain under the unchanged course ceilings.

## Actual remaining dependencies

- `GEMINI_API_KEY` was not accessible during the initial audit and ping failed
  before a model call. No real Part C run has been claimed as complete.
- `eval/thresholds/claim.yaml` must be computed from three actual pilot sweeps,
  then committed/pushed before sweep four. The design file is not that threshold.
- `eval/judge/criterion.md` is an inherited assisted draft; the student must
  personally write/revise and confirm the criterion.
- `eval/labels/labels.csv` currently has only its header. All 60 separate
  pass/fail labels and reasons must be entered by the student.
- Real frozen-judge verdicts and all actual Part C first-failure analyses must be
  produced from the resulting evidence before final reports, tag and submission.

Exact credential/human-input commands and the remaining reproducible execution
order are in [REMAINING_HUMAN_INPUT_07.md](REMAINING_HUMAN_INPUT_07.md). Runtime
pricing and Git provenance are in
[reports/RUNTIME_PROVENANCE_07.md](reports/RUNTIME_PROVENANCE_07.md).

## Verification

```bash
make test
make check-07
```

A current partial checker score is not a completed assignment. No final
`lab-07` submission tag or Canvas submission is claimed until the actual
experiments, human-only inputs, metered verdicts, reports and final checks exist.
The staff-reviewed 20 points require a separate reading of the report even if
the automated 80 are eventually satisfied.
