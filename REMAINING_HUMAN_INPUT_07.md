# Remaining human input and execution order

The 40 historical reviews and nine-category taxonomy are complete and protected.
They are not the same as the 60 separate Part D output labels.

## API credential and completed Part C

The ignored `.env` is accessible and real ping succeeded. Both arms completed
all five sweeps on the frozen eight tasks. Threshold commit `756817f` was pushed
before sweep four. The measured claim fails; see `reports/PART_C_ANALYSIS_07.md`
and `reports/PART_C_PROVENANCE_07.json`. Usage is 2,691,051/20,000,000 tokens;
priced experiment cost is $0.643755. No credentials are printed or committed.

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

## Completed experiment and remaining judge execution

Part C is complete; do not create a replacement threshold or change the subset.
All 67 failed runs have explicitly disclosed Codex-assisted trace analyses in
`eval/failures_ai.csv`. The original human 40-review dataset is unchanged.

For audit/reproduction of the existing artifacts (no new model calls):

```bash
.venv/bin/python -m eval.failure_review_07 validate
.venv/bin/python -m eval.report_07
make test
make check-07
```

The generic judge draft predates the initial split in the working tree; this is
openly disclosed in runtime provenance, not retroactively re-dated. The committed
split precedes this session's extensions and all label-driven judge development.

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
