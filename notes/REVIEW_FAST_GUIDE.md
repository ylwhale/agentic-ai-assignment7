# Fast historical trace review

This workflow prepares evidence and saves your individually confirmed Part A
reviews. It makes no model/API calls, supplies no human decisions or observations,
and does not touch Part D labels, the golden set, or the assignment checker.

## Start or resume

From the repository root:

```bash
source .venv/bin/activate
python notes/review_fast.py
```

For a five-review session:

```bash
python notes/review_fast.py --batch 5
```

Read the issue, tool table, recorded final state, and independent evidence.
On a terminal the evidence opens in a pager; press `q` to return to the prompts.
Enter your expected decision, observed workflow, last correct call, first wrong
call (or `none` / `stopped too early`), own observation, assessment, and evidence
references. Each field is retained as an **unconfirmed draft** as you proceed.

Use `a/r/s` for act/refuse/stop and `s/f/u` for successful/failed/uncertain.
For calls, use the unique `cN` from the table: steps can repeat, and even the same
tool can run several times at one step. A unique step number or tool + step also
works. `start` means before any correct call. For checked evidence, enter the
listed source numbers (for example `2,3`) **only for sources you actually checked**.
The original issue alone does not replace code or matching maintainer history.

The confirmation screen contains all your fields and any factual warnings.
Type uppercase **`SAVE`** to confirm one review. `edit` revisits the fields.
No other answer saves a completed review. `:q`, Ctrl-C, or EOF pauses; starting
the same command resumes drafts. Enter retains your prior draft answer. An
unverified CSV row can also be resumed. Every resumed review needs fresh `SAVE`.
The next unreviewed run opens automatically after saving.

## Inspect more evidence at any prompt

- `:tool cN`: full arguments and returned result, not the table excerpt.
- `:trace`: complete original JSONL, including proposed and rejected calls.
- `:control`: validation, rejection, revision, and termination events.
- `:source N`: complete original independent source, with line numbers.
- `:packet`: all prepared source excerpts.
- `:q`: pause without saving a completed review.

Viewing evidence never marks it as checked. You supply checked references.
Maintainer and source evidence is read from fixtures directly. Model text and
posted comments are claims; the recorded end state establishes effects.
Open PRs do not establish implemented changes or merges. End state omits the
draft flag, so consult tool inputs/results if it matters.

## Commands

```bash
python notes/review_fast.py --status
python notes/review_fast.py --prepare       # refresh all pending evidence, preserve human CSV fields
python notes/review_fast.py --preview       # demonstrate next review; no prompts or saved review
python notes/review_fast.py --run direct-issue-4636-s01-548b9b --batch 1
python notes/review_fast.py --validate      # writes factual audit.json, flags legacy gaps
python notes/review_fast.py --history       # original backup and save history
```

The original `human_review_cli.py --status` / `--run` interfaces still work.
Its interactive save now shares the safe writer. The existing CSV workflow also
works: edit your own human fields, enter `verified=yes` yourself after independent
review, then run `batch_review.py apply --dry-run` and `batch_review.py apply`.
The latter treats your explicit CSV `verified=yes` as its original confirmation
contract. Never bulk-fill that field for unexamined traces.

## Storage and recovery

- `notes/trace-review.md` is the completion authority. Its existing 17 sections
  were preserved byte for byte. No new review was saved during implementation.
- `notes/batch_review/queue.csv` keeps the existing columns. Machine judgment
  candidate columns remain blank; human fields are preserved by run ID.
- `packets/<run>.md` is the concise packet; `<run>.json` contains the complete
  tool inputs/results, final state, claims, control events, references, and hashes.
  Packets are machine preparation and never count as reviewed runs.
- `drafts/` contains only unconfirmed human inputs. It never supplies verification.
- `backups/` preserves the original review document and CSV before replacement.
- `preservation.json` hashes the 17 original Run sections and points to the exact
  original document backup. Later confirmed records are hashed in `history/`.
- `history/` records each explicit confirmation, exact human fields, evidence
  hashes, backup, and warnings. An interrupted write is recovered against the
  Markdown commit; an uncommitted write intent never counts as a review.

Writes use a shared process lock, atomic replacement, and backups. All prior Run
sections are compared before every save. Changed evidence blocks a stale save.
If a crash occurs between the Markdown commit and the pending-queue update,
`--prepare` rebuilds the queue from the authoritative Markdown without duplicates.
Avoid editing the same files in another editor while saving: the lock coordinates
these scripts, not arbitrary external editors.

## Coverage and failure taxonomy

Selection balances underrepresented implementations, termination conditions,
recorded labels, source areas, maintainer-history language (including duplicate,
withdrawn, template-test, declined/private cases), and potential write risks.
These are sampling signals, not correctness judgments. Prepared source paths
come from original issue/history references and tool metadata; when none exist,
literal local-source search provides explicitly marked candidates for checking.

Only after writing an individual observation, tag it with **your own** categories:

```bash
python notes/review_fast.py --tag RUN_ID
python notes/review_fast.py --taxonomy
```

No category names are suggested. The report counts user-confirmed tags, shows
where categories first appeared, and reports subsequent tagged reviews with no
new category. It reports saturation as unestablished while records are untagged;
coverage and the final saturation conclusion remain your judgment. It does not
write the assignment's final synthesis for you.

## Audit boundary

The repository README says the instructor's handout is separate. No handout was
found locally; the supplied follow-up was the stale machine evidence summary,
not the handout. Implementation follows the user's explicit requirements,
`checks/FORMATS.md` sections 15.1–15.3, and the existing review format. The exact
separate Part A handout remains unverified.

The original 17 entries are unique saved reviews. Some older entries lack
structured evidence references, and some observations say “draft for review.”
`--validate` reports those legacy gaps without rewriting or discarding the
records. Presence in the old document does not independently prove confirmation
provenance. Read `notes/batch_review/audit.json` before asserting submission
readiness. New workflow records require valid references and explicit confirmation.

## Tests

```bash
python -m unittest tests.test_review_fast tests.test_batch_review -v
python -m unittest discover -s tests -t .
```

All synthetic reviewer answers used by tests are confined to temporary copies.
They are never saved into the real review document or judge labels.
