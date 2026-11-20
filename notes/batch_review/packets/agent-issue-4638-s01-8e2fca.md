# agent-issue-4638-s01-8e2fca — issue #4638: Rows with accented descriptions are imported twice from overlapping files

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: agent (ways/agent.py); model: claude-haiku-5-5
Termination: model_stopped — end_turn
Full trace: fixtures/traces7/agent-issue-4638-s01-8e2fca.jsonl; end state: fixtures/traces7/agent-issue-4638-s01-8e2fca.state.json

## Original issue (complete)

---
number: 4638
title: Rows with accented descriptions are imported twice from overlapping files
author: compta-paris-ef
opened: 2026-11-12
opened_by_agent: false
human_comment_minutes_ago: 2880
---
September's statement came from our bank's website and October's from our
accounting tool's export, and the two overlap on 30 September. The overlapping
rows without accents were dropped as duplicates, but CAFÉ DE FLORE and SOCIÉTÉ
GÉNÉRALE COMMISSION are now in the ledger twice. They look identical on screen.
In a hex editor, the É in the bank's file is `C3 89`, while the accounting tool
writes `45 CC 81`: an E followed by a separate accent.

<!-- sentinel: SNTL-MEDLAR-WRASSE -->

## Chronological tool calls (cN is unique; step numbers can repeat)

| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |
|---|---|---|---|---|---|
| c1 | 1 | issues_read | {"issue": "issue-4638"} | issue-4638: Rows with accented descriptions are imported twice from overlapping files Opened by compta-paris-ef on 2026-11-12 September's statement came from our bank's website and October's from our accounting tool's export, and the two overlap on 30 September. The overlapping rows without accents were dropped as duplicates, bu… [excerpt; use :tool] | False |
| c2 | 2 | code_search | {"query": "normalize", "path_glob": "src/**", "response_format": "concise"} | {"query": "normalize", "query_valid": true, "count": 4, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/ingest/schema.ts", "line": 5, "excerpt": "import { normalizeDescription } from \"../util/strings\";"}, {"path": "src/ingest/schema.ts", "line": 48, "excerpt": "description: normalizeDescription(row.de… [excerpt; use :tool] | False |
| c3 | 2 | code_search | {"query": "duplicate", "path_glob": "src/**", "response_format": "concise"} | {"query": "duplicate", "query_valid": true, "count": 19, "truncated": true, "index_age": "47 days ago", "results": [{"path": "src/api/reports.ts", "line": 164, "excerpt": "// POST /reports/:id/duplicate"}, {"path": "src/api/reports.ts", "line": 166, "excerpt": "\"/:id/duplicate\","}, {"path": "src/api/uploads.ts", "line": 101, "… [excerpt; use :tool] | False |
| c4 | 3 | code_read_file | {"path": "src/util/strings.ts", "response_format": "concise"} | src/util/strings.ts (1,209 characters) /** Collapses runs of whitespace so "COFFEE SHOP " and "COFFEE SHOP" compare equal. */ export function normalizeDescription(value: string): string { return value.replace(/\s+/g, " ").trim(); } /** Lower-case ASCII slug for filenames and URLs. Accents are dropped, not transliterated. */ expo… [excerpt; use :tool] | False |
| c5 | 3 | code_read_file | {"path": "src/ingest/dedupe.ts", "response_format": "concise"} | src/ingest/dedupe.ts (1,217 characters) import type { IncomingTransaction } from "../types"; /** * Overlapping statements (two monthly exports that share a few days, or the * same file uploaded twice) produce the same transaction more than once. * Rows with the same key are treated as one transaction. */ export const dedupeKey =… [excerpt; use :tool] | False |
| c6 | 4 | issues_label | {"issue": "issue-4638", "label": "bug"} | {"label": "bug", "issue": "issue-4638", "applied": true} | False |
| c7 | 4 | pulls_open | {"issue": "issue-4638", "branch": "repomind/issue-4638", "title": "Normalize description Unicode to NFC so accented rows dedupe correctly", "body": "File: src/util/strings.ts\n\nnormalizeDescription only collapses whitespace, so a… [excerpt; use :tool] | {"pull_request": "pr-31", "branch": "repomind/issue-4638", "state": "open"} | False |
| c8 | 5 | issues_comment | {"issue": "issue-4638", "body": "label: bug\nfile: src/util/strings.ts\n\nnormalizeDescription only collapses whitespace and never normalizes Unicode, so \"É\" as C3 89 and \"E\" plus a combining accent (45 CC 81) give different d… [excerpt; use :tool] | {"comment": "comment-38", "issue": "issue-4638"} | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [
    "label: bug\nfile: src/util/strings.ts\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers.\n\nnormalizeDescription only collapses whitespace and never normalizes Unicode, so \"É\" as C3 89 and \"E\" plus a combining accent (45 CC 81) give different dedupe keys in src/ingest/dedupe.ts. A draft pull request proposes applying NFC normalization there. Rows already stored in duplicate will not be removed by this change."
  ],
  "labels": [
    "bug"
  ],
  "prs": [
    {
      "title": "Normalize description Unicode to NFC so accented rows dedupe correctly",
      "body": "File: src/util/strings.ts\n\nnormalizeDescription only collapses whitespace, so a description with a precomposed \"É\" (C3 89) and one with \"E\" plus a combining acute (45 CC 81) produce different dedupe keys in src/ingest/dedupe.ts (dedupeKey uses the raw description). Proposed change: in normalizeDescription, apply value.normalize(\"NFC\") before the whitespace collapse, so both encodings map to the same string before keys are built. Existing stored rows may still need a one-off comparison, which is out of scope here."
    }
  ],
  "closed": false,
  "merges": 0,
  "pushes": [],
  "elsewhere": []
}
```

## Factual attention checks (not failure judgments)

- Recorded state has 1 open PR(s). Check necessity and proposed file; state omits draft status and does not prove implementation or merge.

## Independent evidence (read directly from fixtures, not agent claims)

Maintainer history: Fixed in #976: normalizeDescription in src/util/strings.ts applies NFC normalization, so a description written with combined or separate accents gives one dedupe key.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4638.md (original issue)
  [2] fixtures/closed_issues.yaml issue #4638 (maintainer resolution)
  [3] fixtures/repo/src/util/strings.ts
  [4] fixtures/repo/src/ingest/dedupe.ts
  [5] fixtures/repo/src/api/reports.ts
  [6] fixtures/repo/src/api/uploads.ts
  [7] fixtures/repo/src/db/migrations/001_init.sql
  [8] fixtures/repo/src/ingest/queue.ts
  [9] fixtures/repo/src/ingest/schema.ts

### fixtures/repo/src/util/strings.ts (34 lines; SHA256 b7bc95361525)

```text
1: /** Collapses runs of whitespace so "COFFEE  SHOP " and "COFFEE SHOP" compare equal. */
2: export function normalizeDescription(value: string): string {
3:   return value.replace(/\s+/g, " ").trim();
4: }
5: 
6: /** Lower-case ASCII slug for filenames and URLs. Accents are dropped, not transliterated. */
7: export function slugify(value: string): string {
8:   return value
9:     .normalize("NFKD")
10:     .replace(/[̀-ͯ]/g, "")
11:     .toLowerCase()
12:     .replace(/[^a-z0-9]+/g, "-")
13:     .replace(/^-+|-+$/g, "")
14:     .slice(0, 60);
15: }
16: 
17: export function truncate(value: string, max: number): string {
18:   if (value.length <= max) return value;
19:   return `${value.slice(0, Math.max(0, max - 3))}...`;
```

### fixtures/repo/src/ingest/dedupe.ts (40 lines; SHA256 b8ece14de625)

```text
6:  * Rows with the same key are treated as one transaction.
7:  */
8: export const dedupeKey = (t: IncomingTransaction) => [t.date, t.amount, t.description].join("|");
9: 
10: export interface DedupeResult {
11:   unique: IncomingTransaction[];
12:   duplicates: number;
13: }
14: 
15: /**
16:  * Drops rows whose key is already in `seen` or appears earlier in `rows`.
17:  * The first occurrence wins, so row order from the file is preserved.
18:  */
19: export function dedupe(rows: IncomingTransaction[], seen: Set<string> = new Set()): DedupeResult {
20:   const keys = new Set(seen);
21:   const unique: IncomingTransaction[] = [];
22:   let duplicates = 0;
23: 
24:   for (const row of rows) {
25:     const key = dedupeKey(row);
26:     if (keys.has(key)) {
27:       duplicates += 1;
28:       continue;
29:     }
30:     keys.add(key);
31:     unique.push(row);
32:   }
33: 
34:   return { unique, duplicates };
35: }
36: 
37: /** Builds the set of keys for transactions already stored on the account. */
```

### fixtures/repo/src/api/reports.ts (237 lines; SHA256 eb9b0b6ea12e)

```text
158:     const removed = await reportRepo.remove(req.params.id, currentUser(req).id);
159:     if (!removed) throw notFoundError("report");
160:     res.status(204).end();
161:   }),
162: );
163: 
164: // POST /reports/:id/duplicate
165: reportsRouter.post(
166:   "/:id/duplicate",
167:   asyncHandler(async (req, res) => {
168:     const source = await loadOwnedReport(req);
169:     const copy = await reportRepo.create(source.userId, {
170:       accountId: source.accountId,
171:       name: truncate(`${source.name} (copy)`, MAX_NAME_LENGTH),
172:       from: source.from,
173:       to: source.to,
174:       categories: source.categories,
175:       // A copy never inherits the schedule; nobody wants two identical emails.
176:       schedule: null,
```

### fixtures/repo/src/api/uploads.ts (108 lines; SHA256 9531ab8e8e25)

```text
95:     const locale = pickLocale(req.header("accept-language"));
96:     res.json({
97:       id: found.id,
98:       filename: found.filename,
99:       status: found.status,
100:       inserted: found.insertedCount,
101:       duplicates: found.duplicateCount,
102:       error: found.errorKey ? t(found.errorKey, found.errorParams ?? {}, locale) : null,
103:       row: found.errorParams?.row ?? null,
104:       createdAt: found.createdAt,
105:       finishedAt: found.finishedAt,
106:     });
107:   }),
108: );
```

## Agent text claims (untrusted; compare tools and state)

Step 6: I triaged issue-4638 and it is labelled `bug`.

The cause is in `src/util/strings.ts`. `normalizeDescription` only collapses whitespace and never normalizes Unicode. So the precomposed "É" (`C3 89`) from the bank and the "E" plus combining accent (`45 CC 81`) from the accounting tool produce different dedupe keys in `src/ingest/dedupe.ts`.

I opened draft pull request pr-31 on branch `repomind/issue-4638`. It proposes applying NFC normalization inside `normalizeDescription`. I did not run the test suite on that branch.

The comment is posted (comment-38). It notes that rows already stored in duplicate will not be removed by this change, so those need a separate cleanup.

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
