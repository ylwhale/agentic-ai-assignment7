# agent-issue-4633-s01-76d741 — issue #4633: dedupe.ts misses overlapping days when two statements are uploaded together

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: agent (ways/agent.py); model: claude-haiku-5-5
Termination: turn_limit — 4 model calls
Full trace: fixtures/traces7/agent-issue-4633-s01-76d741.jsonl; end state: fixtures/traces7/agent-issue-4633-s01-76d741.state.json

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
| c1 | 1 | issues_read | {"issue": "issue-4633"} | issue-4633: dedupe.ts misses overlapping days when two statements are uploaded together Opened by recon-team-milan on 2026-11-11 Duplicate detection in `src/ingest/dedupe.ts` doesn't handle overlapping statements uploaded together. I uploaded our September and October statements straight after each other; both contain 28 to 30 S… [excerpt; use :tool] | False |
| c2 | 2 | code_search | {"query": "dedupe", "path_glob": "src/**", "response_format": "concise"} | {"query": "dedupe", "query_valid": true, "count": 7, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/ingest/dedupe.ts", "line": 8, "excerpt": "export const dedupeKey = (t: IncomingTransaction) => [t.date, t.amount, t.description].join(\"\|\");"}, {"path": "src/ingest/dedupe.ts", "line": 10, "excerpt": "e… [excerpt; use :tool] | False |
| c3 | 3 | code_read_file | {"path": "src/ingest/dedupe.ts", "response_format": "concise"} | src/ingest/dedupe.ts (1,217 characters) import type { IncomingTransaction } from "../types"; /** * Overlapping statements (two monthly exports that share a few days, or the * same file uploaded twice) produce the same transaction more than once. * Rows with the same key are treated as one transaction. */ export const dedupeKey =… [excerpt; use :tool] | False |
| c4 | 3 | code_read_file | {"path": "src/ingest/worker.ts", "response_format": "concise"} | src/ingest/worker.ts (3,944 characters) import { config } from "../config"; import { transactionRepo } from "../db/repos/transactionRepo"; import { logger } from "../logger"; import { storage } from "../storage"; import { addDays } from "../util/dates"; import { dedupe, keysFor } from "./dedupe"; import { isIngestError } from ".… [excerpt; use :tool] | False |
| c5 | 4 | code_search | {"query": "concurrency", "path_glob": "src/**", "response_format": "concise"} | {"query": "concurrency", "query_valid": true, "count": 4, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/config.ts", "line": 20, "excerpt": "queue: { concurrency: number; pollIntervalMs: number; maxAttempts: number };"}, {"path": "src/config.ts", "line": 78, "excerpt": "concurrency: int(\"QUEUE_CONCURR… [excerpt; use :tool] | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [],
  "labels": [],
  "prs": [],
  "closed": false,
  "merges": 0,
  "pushes": [],
  "elsewhere": []
}
```

## Factual attention checks (not failure judgments)

- Recorded state has 0 comments; termination alone does not establish completion.

## Independent evidence (read directly from fixtures, not agent claims)

Maintainer history: Fixed in #973: src/ingest/worker.ts now holds a per-account lock while it reads stored rows and inserts new ones, so overlapping uploads for one account import one after the other. dedupe.ts was correct.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4633.md (original issue)
  [2] fixtures/closed_issues.yaml issue #4633 (maintainer resolution)
  [3] fixtures/repo/src/ingest/worker.ts
  [4] fixtures/repo/src/ingest/dedupe.ts
  [5] fixtures/repo/src/config.ts

### fixtures/repo/src/ingest/worker.ts (111 lines; SHA256 3f7adf417340)

```text
1: import { config } from "../config";
2: import { transactionRepo } from "../db/repos/transactionRepo";
3: import { logger } from "../logger";
4: import { storage } from "../storage";
5: import { addDays } from "../util/dates";
6: import { dedupe, keysFor } from "./dedupe";
7: import { isIngestError } from "./errors";
8: import { parseStatement } from "./parser";
9: import { claimNext, completeJob, failJob, listFailedUploadsBefore, markUploadPurged, type ImportJob } from "./queue";
10: import { toTransaction } from "./schema";
11: 
12: /** Failed uploads stay in storage this long so the original file can be inspected. */
13: export const FAILED_UPLOAD_RETENTION_DAYS = 7;
14: 
15: const PURGE_INTERVAL_MS = 60 * 60 * 1000;
16: 
28: 
29:   let inserted = 0;
30:   let duplicates = 0;
31:   if (incoming.length > 0) {
32:     const dates = incoming.map((t) => t.date).sort();
33:     const existing = await transactionRepo.listInRange(upload.accountId, dates[0], dates[dates.length - 1]);
34:     const result = dedupe(incoming, keysFor(existing));
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
76:   }
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
```

### fixtures/repo/src/ingest/dedupe.ts (40 lines; SHA256 b8ece14de625)

```text
2: 
3: /**
4:  * Overlapping statements (two monthly exports that share a few days, or the
5:  * same file uploaded twice) produce the same transaction more than once.
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
```

### fixtures/repo/src/config.ts (100 lines; SHA256 0f8cb4d071bb)

```text
14:     bucket: string;
15:     region: string;
16:     endpoint?: string;
17:     accessKeyId: string;
18:     secretAccessKey: string;
19:   };
20:   queue: { concurrency: number; pollIntervalMs: number; maxAttempts: number };
21:   smtp: { host: string; port: number; user: string; pass: string; from: string };
22:   auth: { jwtSigningKey: string; tokenTtlMinutes: number; resetTokenTtlMinutes: number };
23:   uploads: { maxBytes: number };
24: }
25: 
26: // Everything in app.yaml is optional; secrets only ever come from the environment.
27: type FileConfig = Partial<{
28:   env: Env;
29:   port: number;
30:   logLevel: LogLevel;
72:       region: process.env.S3_REGION ?? file.storage?.region ?? "eu-west-1",
73:       endpoint: process.env.S3_ENDPOINT ?? file.storage?.endpoint,
74:       accessKeyId: required("S3_ACCESS_KEY"),
75:       secretAccessKey: required("S3_SECRET_KEY"),
76:     },
77:     queue: {
78:       concurrency: int("QUEUE_CONCURRENCY", file.queue?.concurrency ?? 2),
79:       pollIntervalMs: int("QUEUE_POLL_INTERVAL_MS", file.queue?.pollIntervalMs ?? 2_000),
80:       maxAttempts: int("QUEUE_MAX_ATTEMPTS", file.queue?.maxAttempts ?? 5),
81:     },
82:     smtp: {
83:       host: required("SMTP_HOST"),
84:       port: int("SMTP_PORT", file.smtp?.port ?? 587),
85:       user: required("SMTP_USER"),
86:       pass: required("SMTP_PASS"),
87:       from: process.env.SMTP_FROM ?? file.smtp?.from ?? "Ledgerline <no-reply@ledgerline.app>",
88:     },
```

## Agent text claims (untrusted; compare tools and state)

Step 4: The cause looks like a race in `worker.ts`: each job reads existing rows before dedupe and insert, and with several polling loops two overlapping uploads can run at the same time, so neither sees the other's rows. I'll check the config default for concurrency before I settle on the file.

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
