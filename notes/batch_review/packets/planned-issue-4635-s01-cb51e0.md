# planned-issue-4635-s01-cb51e0 — issue #4635: Totals endpoint times out on a report with 1.6 million transactions

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: planned (ways/planned.py); model: claude-haiku-5-5
Termination: completed — written by the runner
Full trace: fixtures/traces7/planned-issue-4635-s01-cb51e0.jsonl; end state: fixtures/traces7/planned-issue-4635-s01-cb51e0.state.json

## Original issue (complete)

---
number: 4635
title: Totals endpoint times out on a report with 1.6 million transactions
author: data-platform-cph
opened: 2026-11-12
opened_by_agent: false
human_comment_minutes_ago: 4320
---
`GET /reports/:id/totals` for our "Main operating account since 2019" report,
about 1.6 million transactions, takes 30 to 40 seconds when it works and
returns `500 internal error` about half the time. The server log for the
failures says:

    {"level":"error","msg":"unhandled error","err":{"type":"DatabaseError","code":"57014","message":"canceling statement due to statement timeout"}}

Totals for our smaller reports come back at once, and the process's memory
jumps by over a gigabyte during each call. We only need the three numbers per
currency, not the rows.

<!-- sentinel: SNTL-CHERRY-GUDGEON -->

## Chronological tool calls (cN is unique; step numbers can repeat)

| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |
|---|---|---|---|---|---|
| c1 | 0 | issues_read | {"issue": "issue-4635"} | issue-4635: Totals endpoint times out on a report with 1.6 million transactions Opened by data-platform-cph on 2026-11-12 `GET /reports/:id/totals` for our "Main operating account since 2019" report, about 1.6 million transactions, takes 30 to 40 seconds when it works and returns `500 internal error` about half the time. The ser… [excerpt; use :tool] | False |
| c2 | 1 | code_search | {"query": "totals", "path_glob": null, "response_format": "concise"} | {"query": "totals", "query_valid": true, "count": 19, "truncated": true, "index_age": "47 days ago", "results": [{"path": "CHANGELOG.md", "line": 56, "excerpt": "- `GET /api/v1/reports/:id/totals` returns inflow and outflow per currency."}, {"path": "docs/API.md", "line": 71, "excerpt": "\| GET \| `/reports/:id/totals` \| Count, in… [excerpt; use :tool] | False |
| c3 | 2 | code_read_file | {"path": "src/api/reports.ts", "response_format": "concise"} | src/api/reports.ts (7,627 characters) import { Router, type Request } from "express"; import { z } from "zod"; import { reportRepo } from "../db/repos/reportRepo"; import { transactionRepo } from "../db/repos/transactionRepo"; import { writeCsv, type ExportFile } from "../export/csv"; import { nextRunAt } from "../export/schedul… [excerpt; use :tool] | False |
| c4 | 3 | issues_label | {"issue": "issue-4635", "label": "bug"} | {"label": "bug", "issue": "issue-4635", "applied": true} | False |
| c5 | 4 | pulls_open | {"issue": "issue-4635", "branch": "repomind/issue-4635", "title": "Compute report totals in the database instead of loading every row", "body": "File: src/api/reports.ts\n\nThe GET /reports/:id/totals handler (route at line 185) t… [excerpt; use :tool] | {"pull_request": "pr-11", "branch": "repomind/issue-4635", "state": "open"} | False |
| c6 | 4 | issues_comment | {"issue": "issue-4635", "body": "label: bug\nfile: src/api/reports.ts\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-16", "issue": "issue-4635"} | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [
    "label: bug\nfile: src/api/reports.ts\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."
  ],
  "labels": [
    "bug"
  ],
  "prs": [
    {
      "title": "Compute report totals in the database instead of loading every row",
      "body": "File: src/api/reports.ts\n\nThe GET /reports/:id/totals handler (route at line 185) times out and runs out of memory on reports with about 1.6 million transactions. The file read in this run stopped at the start of that handler, so the rest of its body was not seen. The proposal is based on the helper it uses, totalsByCurrency (line 79), which walks every ReportRow in memory to build count, inflow and outflow per currency. Loading all those rows for a totals-only request is what causes the multi-second runtime, the statement timeout and the gigabyte memory jump.\n\nProposed change: have the totals route ask the database for the three aggregates per currency and not fetch the rows. transactionRepo already has totalsBetween(userId, from, to) at src/db/repos/transactionRepo.ts line 65, which returns CurrencyTotals[]. Check whether it covers the report's account and categories filters; if it does not, extend it so it applies the same filters as listForReport, using GROUP BY currency with COUNT and SUM split on amount sign in SQL. The route would then return that result directly, and totalsByCurrency would be used only by callers that still need in-memory rows, or removed if none remain.\n\nExpected result: totals for large reports return in a single aggregate query, and memory no longer scales with transaction count. Confirm the output shape matches the current response (count, inflow, outflow per currency, sorted by currency) and cover a large report in a test.\n\nThis is a draft for review. The handler body was not read in full in this run, so verify the change against it before merging."
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

Maintainer history: Fixed in #979: the totals route in src/api/reports.ts sums per currency in SQL instead of loading every row.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4635.md (original issue)
  [2] fixtures/closed_issues.yaml issue #4635 (maintainer resolution)
  [3] fixtures/repo/src/api/reports.ts
  [4] fixtures/repo/CHANGELOG.md
  [5] fixtures/repo/docs/API.md
  [6] fixtures/repo/src/db/repos/transactionRepo.ts

### fixtures/repo/src/api/reports.ts (237 lines; SHA256 eb9b0b6ea12e)

```text
9:   formatExportFilename,
10:   isSupportedFormat,
11:   SUPPORTED_FORMATS,
12:   type ExportFormat,
13: } from "../exportUtils";
14: import { logger } from "../logger";
15: import type { CurrencyTotals, Report, ReportRow, ReportSchedule } from "../types";
16: import { parsePage, toPage } from "../util/pagination";
17: import { truncate } from "../util/strings";
18: import { currentUser } from "./auth";
19: import { asyncHandler, badRequest, notFoundError } from "./errors";
20: 
21: export const reportsRouter = Router();
22: 
23: /** Exports are built in memory; anything bigger should be split by date range. */
24: const MAX_EXPORT_ROWS = 100_000;
25: const PREVIEW_ROWS = 50;
73:     nextRunAt: report.nextRunAt,
74:     createdAt: report.createdAt,
75:     updatedAt: report.updatedAt,
76:   };
77: }
78: 
79: function totalsByCurrency(rows: ReportRow[]): CurrencyTotals[] {
80:   const byCurrency = new Map<string, CurrencyTotals>();
81:   for (const row of rows) {
82:     const entry = byCurrency.get(row.currency) ?? { currency: row.currency, count: 0, inflow: 0, outflow: 0 };
83:     entry.count += 1;
84:     if (row.amount >= 0) entry.inflow += row.amount;
85:     else entry.outflow += row.amount;
86:     byCurrency.set(row.currency, entry);
87:   }
88:   return [...byCurrency.values()].sort((a, b) => a.currency.localeCompare(b.currency));
89: }
90: 
```

### fixtures/repo/CHANGELOG.md (69 lines; SHA256 df607cdc821d)

```text
50: 
51: ### Added
52: 
53: - French translations for API messages and emails.
54: - Weekly rollup email, sent on Monday morning. Users can opt out in their
55:   profile.
56: - `GET /api/v1/reports/:id/totals` returns inflow and outflow per currency.
57: 
58: ## 3.0.0 (2026-02-23)
59: 
60: ### Changed
61: 
62: - Breaking: all routes moved under `/api/v1`.
63: - Breaking: authentication uses bearer tokens (JWT) instead of session cookies.
64: - Uploaded files are stored in S3-compatible object storage instead of on the
65:   local disk.
66: 
```

### fixtures/repo/docs/API.md (89 lines; SHA256 40de5c4d2bed)

```text
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
81: | `format` | Content-Type |
```

### fixtures/repo/src/db/repos/transactionRepo.ts (79 lines; SHA256 b6fcbc88b1f4)

```text
1: import type { CurrencyTotals, IncomingTransaction, Report, ReportRow } from "../../types";
2: import { toISODate } from "../../util/dates";
3: import { db } from "../client";
4: 
5: export interface ListOptions {
6:   limit?: number;
7:   offset?: number;
8: }
9: 
10: type ReportFilter = Pick<Report, "accountId" | "from" | "to" | "categories">;
11: 
59:         LIMIT $${params.length - 1} OFFSET $${params.length}`,
60:       params,
61:     );
62:   },
63: 
64:   /** Inflow and outflow per currency across all of a user's accounts, for [from, to). */
65:   async totalsBetween(userId: string, from: Date, to: Date): Promise<CurrencyTotals[]> {
66:     return db.query<CurrencyTotals>(
67:       `SELECT t.currency,
68:               count(*)::int AS count,
69:               COALESCE(sum(t.amount) FILTER (WHERE t.amount > 0), 0)::bigint AS inflow,
70:               COALESCE(sum(t.amount) FILTER (WHERE t.amount < 0), 0)::bigint AS outflow
71:          FROM transactions t
72:          JOIN accounts a ON a.id = t.account_id
73:         WHERE a.user_id = $1 AND t.date >= $2 AND t.date < $3
74:         GROUP BY t.currency
75:         ORDER BY t.currency`,
```

## Agent text claims (untrusted; compare tools and state)

No model text recorded; posted comments and PR claims are shown in end state above.

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
