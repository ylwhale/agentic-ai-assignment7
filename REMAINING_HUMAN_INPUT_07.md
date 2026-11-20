# Remaining human input and execution order

The 40 historical reviews and nine-category taxonomy are complete and protected.
They are not the same as the 60 separate Part D output labels.

## API credential

Configure `GEMINI_API_KEY` in the execution environment or the repository's
ignored `.env`. Do not paste the value into chat. A key exported in a separate
Terminal does not automatically enter Codex's environment; `.env` is supported
by the experiment driver. The driver never prints or executes its contents.

Once accessible, Codex can run the real pilots. No real Part C result, threshold
spread, or final advantage has been invented while the credential is absent.

## Human-authored criterion and 60 labels

The existing `eval/judge/criterion.md` is an inherited assisted draft. It has not
been certified as your independently authored criterion. Write or revise that
file yourself, including your pass/fail rule and unsupported-evidence cases.
The assistant will not author or suggest those decisions.

From the repository root:

```bash
.venv/bin/python notes/human_judge_cli.py --confirm-criterion
.venv/bin/python notes/human_judge_cli.py --batch 60
.venv/bin/python notes/human_judge_cli.py --validate
```

The first command shows your file and records a hash only after you type `HUMAN`
to attest your own authorship/review. Later criterion edits invalidate that
confirmation. The label command shows one full original output at a time and
asks for **your** pass/fail, **your** concrete reason, and a separate save
confirmation. It supplies no labels or reasons. It makes backups and preserves
previous labels; Ctrl-C stops safely. Use the same command to resume.

The exact CSV format is:

```text
id,label,reason
```

It must contain all IDs j01–j60 exactly once, a human `pass` or `fail`, and a
nonempty human reason. `eval/labels/labels.csv` currently contains only its
header. No example label is provided here. Do not edit the frozen split.

After the files are ready, tell Codex so it can validate them without changing
your judgments. The model judge uses examples only from the examples split;
tuning uses tuning outputs; test labels remain held out until the judge is frozen.

## Remaining automated stages, in order

The subset/split freeze commit is already pushed. A generic judge draft existed before this audit; that fact is disclosed in the runtime provenance rather than retroactively re-dated. The implementation and
pre-pilot design must also be committed/pushed before the driver starts.

```bash
.venv/bin/python -m eval.experiment_07 preflight
.venv/bin/python -m eval.experiment_07 pilot
.venv/bin/python -m eval.experiment_07 threshold
```

The pilot command displays only SD and cost. The threshold command calculates
from actual complete pilot cells and never overwrites a threshold. Then commit
and push the actual threshold before starting the next stage:

```bash
git add eval/thresholds/claim.yaml eval/pilot_spread.json
git commit -m "Precommit claim threshold after three pilot sweeps"
git push origin main
.venv/bin/python -m eval.experiment_07 finish
.venv/bin/python -m eval.failure_review_07 prepare
```

Codex must inspect every actual failed run and record trace-backed first-failure
annotations with cause and authorship. No first-failure judgment comes from the
preparation command. Validate annotations before rebuilding the final report.

Once your Part D inputs are complete, judge development/evaluation proceeds:

```bash
.venv/bin/python -m eval.judge examples
.venv/bin/python -m eval.judge tuning
```

Only examples/tuning data may guide prompt revisions. Use `--revision v2` (and a new name for each iteration) on examples/tuning commands to retain prior development verdicts instead of overwriting them. Commit the final generic
judge code/prompt and your criterion, labels and authorship confirmation. Then:

```bash
.venv/bin/python -m eval.judge freeze
git add eval/judge/frozen.json
git commit -m "Freeze judge configuration before held-out evaluation"
git push origin main
.venv/bin/python -m eval.judge test 1
.venv/bin/python -m eval.judge test 2
.venv/bin/python -m eval.judge test 3
.venv/bin/python -m eval.judge versions
.venv/bin/python -m eval.judge recorded
.venv/bin/python -m eval.report_07
```

The freeze hashes judge code, generic prompt, human criterion/confirmation,
labels, split, settings, pricing and input outputs. Test commands reject later
changes and resume partial verdict files with matching provenance. Every model
verdict remains separate from human labels and has a metered session reference.

Final verification is `make test` then `make check-07`. Final commit/tag/push
and staff-report audit happen only after actual experiments and human inputs
are complete. No final submission tag or Canvas completion is claimed early.
