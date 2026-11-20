# agent-issue-4629-s01-c440db — issue #4629: Adding a recipient moved our weekly export from Monday to Thursday

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: agent (ways/agent.py); model: claude-haiku-5-5
Termination: turn_limit — 4 model calls
Full trace: fixtures/traces7/agent-issue-4629-s01-c440db.jsonl; end state: fixtures/traces7/agent-issue-4629-s01-c440db.state.json

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
| c1 | 1 | issues_read | {"issue": "issue-4629"} | issue-4629: Adding a recipient moved our weekly export from Monday to Thursday Opened by ap-aging-owner on 2026-11-10 Our weekly "AP aging" export has always arrived on Monday mornings. Last Thursday I added a colleague to its recipients with `PATCH /reports/:id`, sending the same `schedule` with one more address. No email came … [excerpt; use :tool] | False |
| c2 | 2 | code_search | {"query": "nextRunAt", "path_glob": null, "response_format": "concise"} | {"query": "nextRunAt", "query_valid": true, "count": 15, "truncated": true, "index_age": "47 days ago", "results": [{"path": "src/api/reports.ts", "line": 6, "excerpt": "import { nextRunAt } from \"../export/scheduler\";"}, {"path": "src/api/reports.ts", "line": 55, "excerpt": "return schedule ? nextRunAt(schedule.cadence, now) … [excerpt; use :tool] | False |
| c3 | 3 | code_read_file | {"path": "src/api/reports.ts", "response_format": "concise"} | src/api/reports.ts (7,627 characters) import { Router, type Request } from "express"; import { z } from "zod"; import { reportRepo } from "../db/repos/reportRepo"; import { transactionRepo } from "../db/repos/transactionRepo"; import { writeCsv, type ExportFile } from "../export/csv"; import { nextRunAt } from "../export/schedul… [excerpt; use :tool] | False |
| c4 | 4 | code_read_file | {"path": "src/export/scheduler.ts", "response_format": "concise"} | src/export/scheduler.ts (2,865 characters) import { reportRepo } from "../db/repos/reportRepo"; import { transactionRepo } from "../db/repos/transactionRepo"; import { formatExportFilename, type ExportFormat } from "../exportUtils"; import { logger } from "../logger"; import { sendEmail } from "../notifications/email"; import { … [excerpt; use :tool] | False |

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

Maintainer history: Fixed in #968: src/api/reports.ts keeps next_run_at when a schedule edit leaves the cadence unchanged.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4629.md (original issue)
  [2] fixtures/closed_issues.yaml issue #4629 (maintainer resolution)
  [3] fixtures/repo/src/api/reports.ts
  [4] fixtures/repo/src/export/scheduler.ts
  [5] fixtures/repo/src/db/repos/reportRepo.ts

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

### fixtures/repo/src/export/scheduler.ts (84 lines; SHA256 63e9682da470)

```text
22:   const next = new Date(from.getTime());
23:   next.setUTCHours(RUN_HOUR_UTC, 0, 0, 0);
24:   switch (cadence) {
25:     case "daily":
26:       if (next <= from) next.setUTCDate(next.getUTCDate() + 1);
27:       break;
28:     case "weekly":
29:       next.setUTCDate(next.getUTCDate() + 7);
30:       break;
31:     case "monthly":
32:       next.setUTCMonth(next.getUTCMonth() + 1, 1);
33:       break;
34:   }
35:   return next;
36: }
37: 
38: async function runScheduledExport(report: Report, now: Date): Promise<void> {
41: 
42:   const rows = await transactionRepo.listForReport(report);
43:   const file = await writers[schedule.format](rows);
44:   const filename = formatExportFilename(report.name, schedule.format, now);
45: 
46:   await sendEmail({
47:     ...scheduledExportEmail(report, schedule.recipients, rows.length),
48:     attachments: [{ filename, content: file.body, contentType: file.contentType }],
49:   });
50:   await reportRepo.markScheduleRun(report.id, nextRunAt(schedule.cadence, now));
51: }
52: 
53: /** Runs every export whose next_run_at has passed. Returns how many were sent. */
54: export async function runDueExports(now: Date = new Date()): Promise<number> {
55:   const due = await reportRepo.listDueSchedules(now);
56:   let sent = 0;
57:   for (const report of due) {
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
