# agent-issue-4626-s01-e9cb13 — issue #4626: Reports generated together are listed in a different order every day

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: agent (ways/agent.py); model: claude-haiku-5-5
Termination: turn_limit — 4 model calls
Full trace: fixtures/traces7/agent-issue-4626-s01-e9cb13.jsonl; end state: fixtures/traces7/agent-issue-4626-s01-e9cb13.state.json

## Original issue (complete)

---
number: 4626
title: Reports generated together are listed in a different order every day
author: ops-lead-porto
opened: 2026-11-10
opened_by_agent: false
human_comment_minutes_ago: 1440
---
Six of our scheduled reports are generated in the 06:00 run, all within the
same second. In the recent reports list they come out in a different order
every day, so people hunt for theirs; reports generated together should be in
alphabetical order. I'm fairly sure the cause is
`ORDER BY created_at DESC, id` in `src/db/repos/reportRepo.ts`: breaking ties
by id is as good as random. It should break ties by name.

<!-- sentinel: SNTL-BEECH-STURGEON -->

## Discussion

### priya-s (maintainer) · 2026-11-10
Is this the recent reports list on the dashboard, or the paginated list of
saved reports?

### ops-lead-porto · 2026-11-11
The recent reports list on the dashboard, the one with the number of
recipients on each line. The saved reports list is fine.

## Chronological tool calls (cN is unique; step numbers can repeat)

| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |
|---|---|---|---|---|---|
| c1 | 1 | issues_read | {"issue": "issue-4626"} | issue-4626: Reports generated together are listed in a different order every day Opened by ops-lead-porto on 2026-11-10 Six of our scheduled reports are generated in the 06:00 run, all within the same second. In the recent reports list they come out in a different order every day, so people hunt for theirs; reports generated tog… [excerpt; use :tool] | False |
| c2 | 2 | code_search | {"query": "ORDER BY created_at", "path_glob": null, "response_format": "concise"} | {"query": "ORDER BY created_at", "query_valid": true, "count": 1, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/db/repos/reportRepo.ts", "line": 64, "excerpt": "`SELECT ${COLUMNS} FROM reports WHERE user_id = $1 ORDER BY created_at DESC, id LIMIT $2 OFFSET $3`,"}]} | False |
| c3 | 2 | code_search | {"query": "recent", "path_glob": "src/**", "response_format": "concise"} | {"query": "recent", "query_valid": true, "count": 1, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/report.tsx", "line": 1, "excerpt": "// One line per report, for the dashboard's list of recent reports."}]} | False |
| c4 | 3 | code_read_file | {"path": "src/db/repos/reportRepo.ts", "response_format": "concise"} | src/db/repos/reportRepo.ts (4,161 characters) import type { Report, ReportSchedule } from "../../types"; import { db } from "../client"; interface ReportRecord { id: string; user_id: string; account_id: string; name: string; date_from: string; date_to: string; categories: string[]; schedule: ReportSchedule \| null; next_run_at: D… [excerpt; use :tool] | False |
| c5 | 3 | code_read_file | {"path": "src/report.tsx", "response_format": "concise"} | src/report.tsx (309 characters) // One line per report, for the dashboard's list of recent reports. import React from "react"; import type { Report } from "./Report"; export function ReportLine({ report }: { report: Report }) { return ( <li> {report.title} <small>{report.deliveredTo.length} recipients</small> </li> ); } | False |
| c6 | 4 | code_search | {"query": "reportRepo.list", "path_glob": "src/**", "response_format": "concise"} | {"query": "reportRepo.list", "query_valid": true, "count": 2, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/api/reports.ts", "line": 105, "excerpt": "const { items, total } = await reportRepo.list(currentUser(req).id, params.pageSize, params.offset);"}, {"path": "src/export/scheduler.ts", "line": 55, … [excerpt; use :tool] | False |
| c7 | 4 | code_search | {"query": "ReportLine", "path_glob": "src/**", "response_format": "concise"} | {"query": "ReportLine", "query_valid": true, "count": 1, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/report.tsx", "line": 5, "excerpt": "export function ReportLine({ report }: { report: Report }) {"}]} | False |

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

Maintainer history: No matching closed resolution. Inspect source; absence is not proof of success.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4626.md (original issue)
  [2] fixtures/repo/src/db/repos/reportRepo.ts
  [3] fixtures/repo/src/report.tsx
  [4] fixtures/repo/src/api/reports.ts
  [5] fixtures/repo/src/export/scheduler.ts

### fixtures/repo/src/db/repos/reportRepo.ts (132 lines; SHA256 28d71ce9eec6)

```text
58: 
59: export const reportRepo = {
60:   async list(userId: string, limit: number, offset: number): Promise<{ items: Report[]; total: number }> {
61:     const [rows, [{ total }]] = await Promise.all([
62:       // id breaks ties so paging is stable when created_at is equal.
63:       db.query<ReportRecord>(
64:         `SELECT ${COLUMNS} FROM reports WHERE user_id = $1 ORDER BY created_at DESC, id LIMIT $2 OFFSET $3`,
65:         [userId, limit, offset],
66:       ),
67:       db.query<{ total: number }>("SELECT count(*)::int AS total FROM reports WHERE user_id = $1", [userId]),
68:     ]);
69:     return { items: rows.map(toReport), total };
70:   },
71: 
72:   async get(id: string, userId: string): Promise<Report | null> {
73:     const row = await db.maybeOne<ReportRecord>(`SELECT ${COLUMNS} FROM reports WHERE id = $1 AND user_id = $2`, [
74:       id,
```

### fixtures/repo/src/report.tsx (11 lines; SHA256 84046468bf9a)

```text
1: // One line per report, for the dashboard's list of recent reports.
2: import React from "react";
3: import type { Report } from "./Report";
4: 
5: export function ReportLine({ report }: { report: Report }) {
6:   return (
7:     <li>
8:       {report.title} <small>{report.deliveredTo.length} recipients</small>
9:     </li>
10:   );
11: }
```

### fixtures/repo/src/api/reports.ts (237 lines; SHA256 eb9b0b6ea12e)

```text
99: 
100: // GET /reports
101: reportsRouter.get(
102:   "/",
103:   asyncHandler(async (req, res) => {
104:     const params = parsePage(req.query as Record<string, unknown>);
105:     const { items, total } = await reportRepo.list(currentUser(req).id, params.pageSize, params.offset);
106:     res.json(toPage(items.map(serialize), total, params));
107:   }),
108: );
109: 
110: // GET /reports/:id
111: reportsRouter.get(
112:   "/:id",
113:   asyncHandler(async (req, res) => {
114:     const report = await loadOwnedReport(req);
115:     const preview = await transactionRepo.listForReport(report, { limit: PREVIEW_ROWS });
```

### fixtures/repo/src/export/scheduler.ts (84 lines; SHA256 63e9682da470)

```text
49:   });
50:   await reportRepo.markScheduleRun(report.id, nextRunAt(schedule.cadence, now));
51: }
52: 
53: /** Runs every export whose next_run_at has passed. Returns how many were sent. */
54: export async function runDueExports(now: Date = new Date()): Promise<number> {
55:   const due = await reportRepo.listDueSchedules(now);
56:   let sent = 0;
57:   for (const report of due) {
58:     try {
59:       await runScheduledExport(report, now);
60:       sent += 1;
61:     } catch (err) {
62:       // Left due, so the next tick tries again.
63:       logger.error({ err, reportId: report.id }, "scheduled export failed");
64:     }
65:   }
```

## Agent text claims (untrusted; compare tools and state)

No model text recorded; posted comments and PR claims are shown in end state above.

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
