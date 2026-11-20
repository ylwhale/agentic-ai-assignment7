# workflow-issue-4615-s01-f75af0 — issue #4615: Upload file names with Cyrillic letters come back garbled

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: workflow (ways/workflow.py); model: claude-haiku-5-5
Termination: completed — written by the runner
Full trace: fixtures/traces7/workflow-issue-4615-s01-f75af0.jsonl; end state: fixtures/traces7/workflow-issue-4615-s01-f75af0.state.json

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
| c2 | 1 | code_search | {"query": "originalname", "path_glob": null, "response_format": "concise"} | {"query": "originalname", "query_valid": true, "count": 3, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/api/uploads.ts", "line": 60, "excerpt": "if (!file.originalname.toLowerCase().endsWith(\".csv\") \|\| !ACCEPTED_TYPES.has(file.mimetype)) {"}, {"path": "src/api/uploads.ts", "line": 68, "excerpt": "c… [excerpt; use :tool] | False |
| c3 | 1 | code_search | {"query": "latin1", "path_glob": null, "response_format": "concise"} | {"query": "latin1", "query_valid": true, "count": 0, "truncated": false, "index_age": "47 days ago", "results": []} | False |
| c4 | 1 | code_search | {"query": "Content-Disposition", "path_glob": null, "response_format": "concise"} | {"query": "Content-Disposition", "query_valid": true, "count": 2, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/api/reports.ts", "line": 221, "excerpt": "res.setHeader(\"Content-Disposition\", `attachment; filename=\"${filename}\"`);"}, {"path": "src/components/ExportButton.tsx", "line": 31, "excerpt"… [excerpt; use :tool] | False |
| c5 | 2 | issues_comment | {"issue": "issue-4615", "body": "label: bug\nfile: src/api/uploads.ts\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-46", "issue": "issue-4615"} | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [
    "label: bug\nfile: src/api/uploads.ts\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."
  ],
  "labels": [],
  "prs": [],
  "closed": false,
  "merges": 0,
  "pushes": [],
  "elsewhere": []
}
```

## Factual attention checks (not failure judgments)

- Comment says label 'bug'; actual recorded labels are []. A comment does not apply a label.
- Comment names src/api/uploads.ts, but recorded state has no open PR. Check the complete tools and intended decision.

## Independent evidence (read directly from fixtures, not agent claims)

Maintainer history: No matching closed resolution. Inspect source; absence is not proof of success.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4615.md (original issue)
  [2] fixtures/repo/src/api/reports.ts
  [3] fixtures/repo/src/api/uploads.ts
  [4] fixtures/repo/src/components/ExportButton.tsx

### fixtures/repo/src/api/reports.ts (237 lines; SHA256 eb9b0b6ea12e)

```text
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

### fixtures/repo/src/api/uploads.ts (108 lines; SHA256 9531ab8e8e25)

```text
54:     const user = currentUser(req);
55:     const { accountId } = bodySchema.parse(req.body);
56:     await assertOwnsAccount(accountId, user.id);
57: 
58:     const file = req.file;
59:     if (!file) throw new HttpError(400, "file is required");
60:     if (!file.originalname.toLowerCase().endsWith(".csv") || !ACCEPTED_TYPES.has(file.mimetype)) {
61:       throw new HttpError(415, t("errors.unsupportedFileType", {}, pickLocale(req.header("accept-language"))));
62:     }
63: 
64:     // Parse the first few rows now so a broken file is rejected before it is stored and queued.
65:     const preview = parseStatement(file.buffer, { limit: PREVIEW_ROWS });
66: 
67:     const id = randomUUID();
68:     const key = uploadKey(accountId, id, file.originalname);
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
```

### fixtures/repo/src/components/ExportButton.tsx (75 lines; SHA256 0e1001fbb180)

```text
25:   }
26: 
27:   const blob = await res.blob();
28:   const url = URL.createObjectURL(blob);
29:   const link = document.createElement("a");
30:   link.href = url;
31:   link.download = filenameFromDisposition(res.headers.get("content-disposition")) ?? `report.${format}`;
32:   document.body.appendChild(link);
33:   link.click();
34:   link.remove();
35:   URL.revokeObjectURL(url);
36: }
37: 
38: interface ExportButtonProps {
39:   reportId: string;
40:   defaultFormat?: ExportFormat;
41: }
```

## Agent text claims (untrusted; compare tools and state)

Step 1: ["originalname", "latin1", "Content-Disposition"]
Step 2: label: bug
file: src/api/uploads.ts

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
