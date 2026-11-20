# planned-issue-4633-s01-a5f973 — issue #4633: dedupe.ts misses overlapping days when two statements are uploaded together

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: planned (ways/planned.py); model: claude-haiku-5-5
Termination: completed — written by the runner
Full trace: fixtures/traces7/planned-issue-4633-s01-a5f973.jsonl; end state: fixtures/traces7/planned-issue-4633-s01-a5f973.state.json

## Original issue (complete)

---
number: 4633
title: dedupe.ts misses overlapping days when two statements are uploaded together
author: recon-team-milan
opened: 2026-11-11
opened_by_agent: false
human_comment_minutes_ago: 240
---
Duplicate detection in `src/ingest/dedupe.ts` doesn't handle overlapping
statements uploaded together. I uploaded our September and October statements
straight after each other; both contain 28 to 30 September, and those three
days are now in the ledger twice (both uploads say 0 duplicates). On our test
account I uploaded the same two files a few minutes apart, and the second one
reported 9 duplicates, as it should. So dedupe.ts must be missing a case.

<!-- sentinel: SNTL-PECAN-MINNOW -->

## Discussion

### ben-ops (maintainer) · 2026-11-12
Thanks. Roughly how long was there between the two uploads, and how big are
the files?

### recon-team-milan · 2026-11-12
About ten seconds apart, around 2,000 rows each. Both had finished importing
within a minute.

## Chronological tool calls (cN is unique; step numbers can repeat)

| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |
|---|---|---|---|---|---|
| c1 | 0 | issues_read | {"issue": "issue-4633"} | issue-4633: dedupe.ts misses overlapping days when two statements are uploaded together Opened by recon-team-milan on 2026-11-11 Duplicate detection in `src/ingest/dedupe.ts` doesn't handle overlapping statements uploaded together. I uploaded our September and October statements straight after each other; both contain 28 to 30 S… [excerpt; use :tool] | False |
| c2 | 1 | code_search | {"query": "duplicate", "path_glob": null, "response_format": "concise"} | {"query": "duplicate", "query_valid": true, "count": 27, "truncated": true, "index_age": "47 days ago", "results": [{"path": "README.md", "line": 4, "excerpt": "clean, deduplicated transaction ledger, and produces reports that finance teams"}, {"path": "README.md", "line": 12, "excerpt": "- Duplicate detection across overlapping… [excerpt; use :tool] | False |
| c3 | 2 | code_read_file | {"path": "src/ingest/dedupe.ts", "response_format": "concise"} | src/ingest/dedupe.ts (1,217 characters) import type { IncomingTransaction } from "../types"; /** * Overlapping statements (two monthly exports that share a few days, or the * same file uploaded twice) produce the same transaction more than once. * Rows with the same key are treated as one transaction. */ export const dedupeKey =… [excerpt; use :tool] | False |
| c4 | 3 | issues_label | {"issue": "issue-4633", "label": "bug"} | {"label": "bug", "issue": "issue-4633", "applied": true} | False |
| c5 | 4 | pulls_open | {"issue": "issue-4633", "branch": "repomind/issue-4633", "title": "Catch overlapping days when two statements are uploaded together", "body": "File: src/ingest/dedupe.ts\n\nProblem: two statements uploaded close together (about te… [excerpt; use :tool] | {"pull_request": "pr-14", "branch": "repomind/issue-4633", "state": "open"} | False |
| c6 | 4 | issues_comment | {"issue": "issue-4633", "body": "label: bug\nfile: src/ingest/dedupe.ts\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-19", "issue": "issue-4633"} | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [
    "label: bug\nfile: src/ingest/dedupe.ts\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."
  ],
  "labels": [
    "bug"
  ],
  "prs": [
    {
      "title": "Catch overlapping days when two statements are uploaded together",
      "body": "File: src/ingest/dedupe.ts\n\nProblem: two statements uploaded close together (about ten seconds apart, both finished within a minute) both keep the shared days 28 to 30 September, and both uploads report 0 duplicates. Uploading the same two files a few minutes apart reports 9 duplicates, so the key logic works when one upload has already been stored before the other is checked.\n\nWhat this file does: dedupe() drops a row when its key is in `seen` or appears earlier in the same `rows` array. keysFor() builds `seen` from transactions already stored on the account. The dedupe key is date|amount|description.\n\nProposed change: make sure the second upload's duplicate check sees the first upload's rows even when the two uploads are processed without the first one being committed yet. In practice this means the key set used by dedupe() should be built from the stored ledger at the moment of checking, or the check should be serialized per account so an upload's keys are visible to the next one. Add a test with two overlapping statements processed back to back, expecting the shared days to be counted as duplicates.\n\nNot yet verified: the caller that builds `seen` (src/api/uploads.ts) was not read in this step, so the exact timing gap is a hypothesis to confirm before the change is final."
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
- Comment names src/ingest/dedupe.ts; maintainer resolution names ['src/ingest/worker.ts']. Compare original source before deciding correctness.

## Independent evidence (read directly from fixtures, not agent claims)

Maintainer history: Fixed in #973: src/ingest/worker.ts now holds a per-account lock while it reads stored rows and inserts new ones, so overlapping uploads for one account import one after the other. dedupe.ts was correct.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4633.md (original issue)
  [2] fixtures/closed_issues.yaml issue #4633 (maintainer resolution)
  [3] fixtures/repo/src/ingest/worker.ts
  [4] fixtures/repo/src/ingest/dedupe.ts
  [5] fixtures/repo/README.md
  [6] fixtures/repo/docs/API.md
  [7] fixtures/repo/src/api/reports.ts
  [8] fixtures/repo/src/api/uploads.ts
  [9] fixtures/repo/src/db/migrations/001_init.sql

### fixtures/repo/src/ingest/worker.ts (111 lines; SHA256 3f7adf417340)

```text
35:     duplicates = result.duplicates;
36:     inserted = await transactionRepo.insertMany(upload.accountId, upload.id, result.unique);
37:   }
38: 
39:   await completeJob(job, { inserted, duplicates });
40: 
41:   // Once the rows are in the ledger the original file is no longer needed.
42:   await storage.remove(upload.key);
43:   log.info({ rows: incoming.length, inserted, duplicates }, "import complete");
44: }
45: 
46: async function runOnce(): Promise<boolean> {
47:   const job = await claimNext();
48:   if (!job) return false;
49: 
50:   try {
51:     await processJob(job);
77:   if (expired.length > 0) logger.info({ count: expired.length }, "purged expired failed uploads");
78:   return expired.length;
79: }
80: 
81: /**
82:  * Starts `queue.concurrency` polling loops plus the hourly purge. The returned
83:  * function stops polling and resolves once in-flight jobs have finished.
84:  */
85: export function startWorker(): () => Promise<void> {
86:   let stopping = false;
87: 
88:   const loop = async () => {
89:     while (!stopping) {
90:       let didWork = false;
91:       try {
92:         didWork = await runOnce();
93:       } catch (err) {
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
```

### fixtures/repo/README.md (89 lines; SHA256 9194f545893b)

```text
1: # Ledgerline
2: 
3: Ledgerline turns the CSV files that banks and accounting tools export into a
4: clean, deduplicated transaction ledger, and produces reports that finance teams
5: can download as CSV or XLSX.
6: 
7: Current version: 3.2.1. See [CHANGELOG.md](CHANGELOG.md) for what changed.
8: 
9: ## Features
10: 
11: - CSV upload with header and row checks before anything is queued
12: - Duplicate detection across overlapping statements
13: - Saved reports filtered by date range and category
14: - Exports as CSV or XLSX, on demand or on a schedule (emailed as an attachment)
15: - Password reset and weekly rollup emails, in English and French
16: 
17: ## Requirements
18: 
19: - Node.js 18.18 or newer
20: - PostgreSQL 14 or newer
21: - An S3-compatible bucket for uploaded files (AWS S3 or MinIO)
22: - An SMTP relay for outgoing mail
```

### fixtures/repo/docs/API.md (89 lines; SHA256 40de5c4d2bed)

```text
52:   "ignoredColumns": [],
53:   "preview": [{ "date": "2026-03-01", "amount": "-4.20", "description": "Coffee" }]
54: }
55: ```
56: 
57: `GET /uploads/:id` returns `status` (`pending`, `importing`, `imported`,
58: `failed`, `purged`), the `inserted` and `duplicates` counts, and `error` and
59: `row` for failed imports.
60: 
61: ## Reports
62: 
63: | Method | Path | Notes |
64: | --- | --- | --- |
65: | GET | `/reports` | Paginated: `?page=1&pageSize=25` (max 100) |
66: | POST | `/reports` | `{ accountId, name, from, to, categories?, schedule? }` |
67: | GET | `/reports/:id` | The report plus the first 50 matching rows as `preview` |
68: | PATCH | `/reports/:id` | Any subset of the create fields |
69: | DELETE | `/reports/:id` | 204 |
70: | POST | `/reports/:id/duplicate` | Copy without the schedule |
71: | GET | `/reports/:id/totals` | Count, inflow and outflow per currency |
72: | GET | `/reports/:id/export` | Download; see below |
73: 
74: `schedule` is `{ cadence: "daily" | "weekly" | "monthly", format, recipients: [email, ...] }`
75: or `null`.
76: 
77: ### Export
78: 
79: `GET /reports/:id/export?format=csv`
80: 
```

## Agent text claims (untrusted; compare tools and state)

No model text recorded; posted comments and PR claims are shown in end state above.

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
