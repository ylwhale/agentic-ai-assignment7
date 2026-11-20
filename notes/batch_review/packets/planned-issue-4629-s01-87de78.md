# planned-issue-4629-s01-87de78 — issue #4629: Adding a recipient moved our weekly export from Monday to Thursday

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: planned (ways/planned.py); model: claude-haiku-5-5
Termination: completed — written by the runner
Full trace: fixtures/traces7/planned-issue-4629-s01-87de78.jsonl; end state: fixtures/traces7/planned-issue-4629-s01-87de78.state.json

## Original issue (complete)

---
number: 4629
title: Adding a recipient moved our weekly export from Monday to Thursday
author: ap-aging-owner
opened: 2026-11-10
opened_by_agent: false
human_comment_minutes_ago: 2880
---
Our weekly "AP aging" export has always arrived on Monday mornings. Last
Thursday I added a colleague to its recipients with `PATCH /reports/:id`,
sending the same `schedule` with one more address. No email came on Monday, and
the report's `nextRunAt` now says Thursday 06:00 UTC. Only the recipients
changed: same cadence, same format.

<!-- sentinel: SNTL-SYCAMORE-CHUB -->

## Chronological tool calls (cN is unique; step numbers can repeat)

| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |
|---|---|---|---|---|---|
| c1 | 0 | issues_read | {"issue": "issue-4629"} | issue-4629: Adding a recipient moved our weekly export from Monday to Thursday Opened by ap-aging-owner on 2026-11-10 Our weekly "AP aging" export has always arrived on Monday mornings. Last Thursday I added a colleague to its recipients with `PATCH /reports/:id`, sending the same `schedule` with one more address. No email came … [excerpt; use :tool] | False |
| c2 | 1 | code_search | {"query": "nextRunAt", "path_glob": null, "response_format": "concise"} | {"query": "nextRunAt", "query_valid": true, "count": 15, "truncated": true, "index_age": "47 days ago", "results": [{"path": "src/api/reports.ts", "line": 6, "excerpt": "import { nextRunAt } from \"../export/scheduler\";"}, {"path": "src/api/reports.ts", "line": 55, "excerpt": "return schedule ? nextRunAt(schedule.cadence, now) … [excerpt; use :tool] | False |
| c3 | 2 | code_read_file | {"path": "src/api/reports.ts", "response_format": "concise"} | src/api/reports.ts (7,627 characters) import { Router, type Request } from "express"; import { z } from "zod"; import { reportRepo } from "../db/repos/reportRepo"; import { transactionRepo } from "../db/repos/transactionRepo"; import { writeCsv, type ExportFile } from "../export/csv"; import { nextRunAt } from "../export/schedul… [excerpt; use :tool] | False |
| c4 | 3 | issues_label | {"issue": "issue-4629", "label": "bug"} | {"label": "bug", "issue": "issue-4629", "applied": true} | False |
| c5 | 4 | pulls_open | {"issue": "issue-4629", "branch": "repomind/issue-4629", "title": "Keep a report's next run when only its recipients change via PATCH", "body": "File: src/api/reports.ts\n\nIn the PATCH /reports/:id handler, the reschedule check i… [excerpt; use :tool] | {"pull_request": "pr-10", "branch": "repomind/issue-4629", "state": "open"} | False |
| c6 | 4 | issues_comment | {"issue": "issue-4629", "body": "label: bug\nfile: src/api/reports.ts\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-15", "issue": "issue-4629"} | False |

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
      "title": "Keep a report's next run when only its recipients change via PATCH",
      "body": "File: src/api/reports.ts\n\nIn the PATCH /reports/:id handler, the reschedule check is `patch.schedule === undefined`. The schedule object carries recipients, format and cadence together, so sending the same schedule with one extra recipient counts as a schedule change. The handler then calls firstRunAt(patch.schedule), which computes nextRunAt from the current time, so the weekly AP aging export jumps from its Monday slot to whatever nextRunAt returns from today (Thursday in the report).\n\nProposed change in prose: in the PATCH handler, only recompute nextRunAt when the cadence actually differs from the existing report's schedule cadence (or when the schedule is being newly set or cleared). When the cadence is unchanged, leave nextRunAt undefined so reportRepo.update keeps the stored value. Recipient-only and format-only edits should never move the next run. The same guard can be applied to the case where the schedule is set to null, which should clear nextRunAt as before.\n\nThis addresses the report: adding a recipient with the same cadence keeps the Monday 06:00 UTC run instead of resetting it to a new date.\n"
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

Maintainer history: Fixed in #968: src/api/reports.ts keeps next_run_at when a schedule edit leaves the cadence unchanged.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4629.md (original issue)
  [2] fixtures/closed_issues.yaml issue #4629 (maintainer resolution)
  [3] fixtures/repo/src/api/reports.ts
  [4] fixtures/repo/src/db/repos/reportRepo.ts

### fixtures/repo/src/api/reports.ts (237 lines; SHA256 eb9b0b6ea12e)

```text
1: import { Router, type Request } from "express";
2: import { z } from "zod";
3: import { reportRepo } from "../db/repos/reportRepo";
4: import { transactionRepo } from "../db/repos/transactionRepo";
5: import { writeCsv, type ExportFile } from "../export/csv";
6: import { nextRunAt } from "../export/scheduler";
7: import { writeXlsx } from "../export/xlsx";
8: import {
9:   formatExportFilename,
10:   isSupportedFormat,
11:   SUPPORTED_FORMATS,
12:   type ExportFormat,
13: } from "../exportUtils";
14: import { logger } from "../logger";
15: import type { CurrencyTotals, Report, ReportRow, ReportSchedule } from "../types";
16: import { parsePage, toPage } from "../util/pagination";
49:   })
50:   .refine((r) => r.from <= r.to, { message: "from must be on or before to", path: ["from"] });
51: 
52: const updateSchema = reportFields.partial().strict();
53: 
54: function firstRunAt(schedule: ReportSchedule | null, now = new Date()): Date | null {
55:   return schedule ? nextRunAt(schedule.cadence, now) : null;
56: }
57: 
58: async function loadOwnedReport(req: Request): Promise<Report> {
59:   const report = await reportRepo.get(req.params.id, currentUser(req).id);
60:   if (!report) throw notFoundError("report");
61:   return report;
62: }
63: 
64: function serialize(report: Report) {
65:   return {
67:     accountId: report.accountId,
68:     name: report.name,
69:     from: report.from,
70:     to: report.to,
71:     categories: report.categories,
72:     schedule: report.schedule,
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
```

### fixtures/repo/src/db/repos/reportRepo.ts (132 lines; SHA256 28d71ce9eec6)

```text
25:     accountId: row.account_id,
26:     name: row.name,
27:     from: row.date_from,
28:     to: row.date_to,
29:     categories: row.categories,
30:     schedule: row.schedule,
31:     nextRunAt: row.next_run_at,
32:     createdAt: row.created_at,
33:     updatedAt: row.updated_at,
34:   };
35: }
36: 
37: export interface NewReport {
38:   accountId: string;
39:   name: string;
40:   from: string;
41:   to: string;
42:   categories: string[];
43:   schedule: ReportSchedule | null;
44:   nextRunAt: Date | null;
45: }
46: 
47: export type ReportPatch = Partial<NewReport>;
48: 
49: const PATCH_COLUMNS: Record<keyof ReportPatch, string> = {
50:   accountId: "account_id",
51:   name: "name",
52:   from: "date_from",
53:   to: "date_to",
54:   categories: "categories",
55:   schedule: "schedule",
56:   nextRunAt: "next_run_at",
57: };
58: 
59: export const reportRepo = {
60:   async list(userId: string, limit: number, offset: number): Promise<{ items: Report[]; total: number }> {
61:     const [rows, [{ total }]] = await Promise.all([
62:       // id breaks ties so paging is stable when created_at is equal.
63:       db.query<ReportRecord>(
64:         `SELECT ${COLUMNS} FROM reports WHERE user_id = $1 ORDER BY created_at DESC, id LIMIT $2 OFFSET $3`,
65:         [userId, limit, offset],
66:       ),
```

## Agent text claims (untrusted; compare tools and state)

No model text recorded; posted comments and PR claims are shown in end state above.

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
