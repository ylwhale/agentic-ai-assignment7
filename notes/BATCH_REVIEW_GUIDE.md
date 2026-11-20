# Faster historical review workflow (Assignment 7, Part A)

This tool **automates evidence preparation and insertion** of human-verified review
entries. It cannot legitimately replace the assignment's requirement that you
inspect at least 40 historical runs and independently record the first wrong
step or success. The separate Part D judge-label rule is also unchanged.

## Recommended interactive workflow

Run `python notes/review_fast.py` to review and resume interactively, or add
`--batch 5` for a five-review session. Type `SAVE` separately for each completed
review. See [REVIEW_FAST_GUIDE.md](REVIEW_FAST_GUIDE.md) for inspection commands,
validation, backups, taxonomy, and legacy-review audit limitations.

The CSV workflow below remains supported. `prepare` now reads raw historical
fixtures and creates full evidence packets for every pending run. It retains all
existing CSV columns and human entries, while leaving machine judgment candidates
blank. `apply` additionally validates tool references and independent evidence.

## Install

The review scripts are already installed in `notes/` and use the existing project
requirements. Activate `.venv` from the repository root.

## 1. Generate a full batch

From the project root, with `.venv` activated:

```bash
python notes/batch_review.py prepare
python notes/batch_review.py status
```

It creates:

- `notes/batch_review/queue.csv`: one row per **unreviewed** trace, with
  machine-extracted facts and blank fields for your assessment.
- `notes/batch_review/evidence-summary.md`: a compact, source-grounded summary
  and tool-call sequence for every pending trace.

The summary is **not a completed review**. Flags such as
`BOUNDS_TERMINATION` and `NO_COMMENT_RECORDED` are factual signals, not judgments;
a no-change or refusal case may legitimately have no PR or public comment.
The last **observed** tool call is not necessarily the last **correct** call.

## 2. Inspect each run and fill your fields

Open the queue in a CSV editor (Excel, Numbers, VS Code, or a plain text editor).
For details on a particular run:

```bash
python notes/batch_review.py inspect --run agent-issue-4618-s01-f00cae
python notes/batch_review.py inspect --run agent-issue-4618-s01-f00cae --full
```

Check the original issue, the full tool sequence, the recorded final state,
and original code or independent maintainer resolution. Then fill the following
columns **yourself** for each run you have genuinely reviewed:

| Column | Your input |
|---|---|
| `expected_decision` | `act`, `refuse`, or `stop` |
| `actual_decision` | What the agent actually attempted |
| `last_correct_call` | Tool and step, or `before any call` |
| `first_incorrect_call` | Tool and step, `none`, or `stopped too early` |
| `observation` | Your own evidence-based paragraph (at least 40 characters) |
| `assessment` | `successful`, `failed`, or `uncertain` |
| `source_checked` | Which original code or maintainer resolution you checked |
| `verified` | Enter `yes` **only after independently checking the review** |

Use only one line per run. In a CSV editor, save as UTF-8 CSV and preserve the
original header and `run_id` column. To speed up, you can fill as many reviews
as you want before applying them in one batch.

**Example:** The Run 14 trace's final state reports zero comments and PRs and
a turn limit. That supports an *incompleteness concern*, but its correct
interpretation still depends on whether the task required a write. Never
classify runs based on terminal reason alone.

## 3. Import your verified reviews into permanent notes

```bash
python notes/batch_review.py apply --dry-run
python notes/batch_review.py apply
python notes/batch_review.py status
```

The tool checks required columns and refuses to import invalid verified rows.
It skips any run IDs already in `notes/trace-review.md`, appends verified reviews
before the review template, updates the 40-run progress count and issues list,
and makes a timestamped backup under `notes/batch_review/backups/` first.

If you interrupt a session, simply resume editing the CSV. If another tool
adds new permanent reviews in the meantime, `prepare` refreshes the pending
rows while retaining your entries for still-pending runs.

## 4. Complete the manual synthesis

After at least 40 distinct reviews, manually group the first-failure categories
and write the saturation analysis in the existing section of
`notes/trace-review.md`. The program does not invent those conclusions.

## Safety notes

- Running `prepare` does **not** change `notes/trace-review.md`.
- Running `apply` never treats blank or unverified rows as human reviews.
- This tool never touches `settings.yaml`, `reports/LAB_07.md`, your Git history,
  the golden tasks, or Part D human judge labels.
- Back up `notes/trace-review.md` before editing it independently, especially
  if you use another editor simultaneously with the batch queue.
