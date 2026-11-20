# planned-issue-4615-s01-c6aced — issue #4615: Upload file names with Cyrillic letters come back garbled

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: planned (ways/planned.py); model: claude-haiku-5-5
Termination: completed — written by the runner
Full trace: fixtures/traces7/planned-issue-4615-s01-c6aced.jsonl; end state: fixtures/traces7/planned-issue-4615-s01-c6aced.state.json

## Original issue (complete)

---
number: 4615
title: Upload file names with Cyrillic letters come back garbled
author: riga-shared-services
opened: 2026-11-07
opened_by_agent: false
human_comment_minutes_ago: 240
---
We name statement files after the bank and the account, partly in Russian. The
import works, but `GET /uploads/:id` returns the name garbled: a file uploaded
as `банк_вклад.csv` comes back as `Ð±Ð°Ð½Ðº_Ð²ÐºÐ»Ð°Ð´.csv`. It isn't only
Cyrillic: `relevé_octobre.csv` from our Lyon office comes back as
`relevÃ©_octobre.csv`. Our reconciliation script matches uploads to files by
name, so it can't find these. Names in plain ASCII are fine.

<!-- sentinel: SNTL-ELDER-TURBOT -->

## Discussion

### ben-ops (maintainer) · 2026-11-09
Thanks. Are these uploaded through the web form, or by your own script?

### riga-shared-services · 2026-11-09
Both. The web form in Chrome and our curl script give the same result.

## Chronological tool calls (cN is unique; step numbers can repeat)

| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |
|---|---|---|---|---|---|
| c1 | 0 | issues_read | {"issue": "issue-4615"} | issue-4615: Upload file names with Cyrillic letters come back garbled Opened by riga-shared-services on 2026-11-07 We name statement files after the bank and the account, partly in Russian. The import works, but `GET /uploads/:id` returns the name garbled: a file uploaded as `банк_вклад.csv` comes back as `Ð±Ð°Ð½Ðº_Ð²ÐºÐ»Ð°Ð´.cs… [excerpt; use :tool] | False |
| c2 | 1 | code_search | {"query": "latin1", "path_glob": null, "response_format": "concise"} | {"query": "latin1", "query_valid": true, "count": 0, "truncated": false, "index_age": "47 days ago", "results": []} | False |
| c3 | 2 | code_search | {"query": "filename", "path_glob": null, "response_format": "concise"} | {"query": "filename", "query_valid": true, "count": 34, "truncated": true, "index_age": "47 days ago", "results": [{"path": "docs/ARCHITECTURE.md", "line": 57, "excerpt": "names, column order and filename rules shared by both writers live in"}, {"path": "docs/CONFIG.md", "line": 33, "excerpt": "Migrations are plain SQL files in … [excerpt; use :tool] | False |
| c4 | 3 | code_read_file | {"path": "src/api/uploads.ts", "response_format": "concise"} | src/api/uploads.ts (3,782 characters) import { randomUUID } from "crypto"; import { Router, type NextFunction, type Request, type Response } from "express"; import multer from "multer"; import { z } from "zod"; import { config } from "../config"; import { db } from "../db/client"; import { pickLocale, t } from "../i18n"; import … [excerpt; use :tool] | False |
| c5 | 4 | issues_label | {"issue": "issue-4615", "label": "bug"} | {"label": "bug", "issue": "issue-4615", "applied": true} | False |
| c6 | 5 | pulls_open | {"issue": "issue-4615", "branch": "repomind/issue-4615", "title": "Keep non-ASCII upload file names intact when storing and returning them", "body": "File: src/api/uploads.ts\n\nThe upload handler in POST /uploads takes file.origi… [excerpt; use :tool] | {"pull_request": "pr-6", "branch": "repomind/issue-4615", "state": "open"} | False |
| c7 | 5 | issues_comment | {"issue": "issue-4615", "body": "label: bug\nfile: src/api/uploads.ts\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-8", "issue": "issue-4615"} | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [
    "label: bug\nfile: src/api/uploads.ts\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."
  ],
  "labels": [
    "bug"
  ],
  "prs": [
    {
      "title": "Keep non-ASCII upload file names intact when storing and returning them",
      "body": "File: src/api/uploads.ts\n\nThe upload handler in POST /uploads takes file.originalname from multer and uses it unchanged for the extension check, for the storage key (uploadKey) and for the filename saved with createUploadWithJob. GET /uploads/:id then returns that saved value. Names such as банк_вклад.csv come back as Ð±Ð°Ð½Ðº_Ð²ÐºÐ»Ð°Ð´.csv, which is the pattern of UTF-8 bytes read as Latin-1. The likely cause is that the multipart filename reaches multer undecoded, so the name is already mojibake before this handler sees it. This is a hypothesis from the code and the report; it has not been reproduced.\n\nProposed change: at the start of the POST handler, before the extension check, normalise file.originalname. Re-decode it from Latin-1 bytes to UTF-8 when that round trip yields valid text, and leave plain ASCII names unchanged. Use the normalised name for the .csv check, uploadKey and the filename passed to createUploadWithJob, so the stored name and the GET response are both correct. Also confirm that the web form and curl paths produce the same bytes, since the reporter saw the same result from both.\n\nOpen question: uploads already stored with garbled names will still return them. A one-off repair of the filename column, or a note to the reporter, may be needed. The reconciliation script in the report matches by name, so that matters for existing rows as well as new ones."
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

Maintainer history: No matching closed resolution. Inspect source; absence is not proof of success.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4615.md (original issue)
  [2] fixtures/repo/src/api/uploads.ts
  [3] fixtures/repo/docs/ARCHITECTURE.md
  [4] fixtures/repo/docs/CONFIG.md
  [5] fixtures/repo/src/api/reports.ts
  [6] fixtures/repo/src/components/ExportButton.tsx

### fixtures/repo/src/api/uploads.ts (108 lines; SHA256 9531ab8e8e25)

```text
69:     await storage.put(key, file.buffer, "text/csv");
70:     await createUploadWithJob({
71:       id,
72:       accountId,
73:       userId: user.id,
74:       key,
75:       filename: file.originalname,
76:       sizeBytes: file.size,
77:     });
78: 
79:     res.status(202).json({
80:       id,
81:       status: "pending",
82:       columns: preview.header,
83:       ignoredColumns: preview.header.filter((column) => !KNOWN_COLUMNS.has(column)),
84:       preview: preview.rows,
85:     });
92:     const found = await findUpload(req.params.id, currentUser(req).id);
93:     if (!found) throw notFoundError("upload");
94: 
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

### fixtures/repo/docs/ARCHITECTURE.md (95 lines; SHA256 6ef605c7e7f7)

```text
51: 
52: ## Reports and exports
53: 
54: A report is a saved filter: account, date range, optional categories, and an
55: optional schedule. `GET /reports/:id/export` loads the matching transactions
56: and hands them to a writer in `src/export/` (`csv.ts` or `xlsx.ts`). Format
57: names, column order and filename rules shared by both writers live in
58: `src/exportUtils.ts`.
59: 
60: Scheduled exports (`src/export/scheduler.ts`) check every five minutes for
61: reports whose `next_run_at` has passed, email the file as an attachment, and
62: set the next run.
63: 
64: ## Notifications
65: 
66: All mail goes through `src/notifications/email.ts` (nodemailer over SMTP, with
67: retries). Message bodies are built in `templates.ts` from the i18n catalogs.
```

### fixtures/repo/docs/CONFIG.md (77 lines; SHA256 b372eb16c5ac)

```text
27: | Variable | Default | Description |
28: | --- | --- | --- |
29: | `DB_URL` | required | PostgreSQL connection string |
30: | `DB_POOL_SIZE` | `10` | Maximum connections per process |
31: | `DB_STATEMENT_TIMEOUT_MS` | `15000` | Per-statement timeout |
32: 
33: Migrations are plain SQL files in `src/db/migrations/`, applied in filename
34: order.
35: 
36: ## Object storage
37: 
38: | Variable | Default | Description |
39: | --- | --- | --- |
40: | `S3_BUCKET` | required | Bucket for uploaded files |
41: | `S3_REGION` | `eu-west-1` | Region |
42: | `S3_ENDPOINT` | unset | Custom endpoint for S3-compatible stores such as MinIO. Enables path-style addressing. |
43: | `S3_ACCESS_KEY` | required | Access key id |
```

### fixtures/repo/src/api/reports.ts (237 lines; SHA256 eb9b0b6ea12e)

```text
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
17: import { truncate } from "../util/strings";
18: import { currentUser } from "./auth";
19: import { asyncHandler, badRequest, notFoundError } from "./errors";
212:     const rows = await transactionRepo.listForReport(report, { limit: MAX_EXPORT_ROWS + 1 });
213:     if (rows.length > MAX_EXPORT_ROWS) {
214:       throw badRequest(`report has more than ${MAX_EXPORT_ROWS} rows; narrow the date range to export it`);
215:     }
216: 
217:     const file = await renderExport(format, rows);
218:     const filename = formatExportFilename(report.name, format);
219: 
220:     res.setHeader("Content-Type", file.contentType);
221:     res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
222:     res.setHeader("Content-Length", String(file.body.length));
223:     res.setHeader("Cache-Control", "no-store");
224:     res.send(file.body);
225: 
226:     logger.info(
227:       {
228:         reportId: report.id,
229:         format,
230:         rows: rows.length,
231:         bytes: file.body.length,
```

## Agent text claims (untrusted; compare tools and state)

No model text recorded; posted comments and PR claims are shown in end state above.

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
