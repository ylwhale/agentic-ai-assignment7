# Run: workflow-issue-4615-s01-f75af0

**Issue:** #4615 — Upload file names with Cyrillic letters come back garbled
**Agent way:** workflow
**Termination:** completed — written by the runner
**Source:** `fixtures/traces7/workflow-issue-4615-s01-f75af0.jsonl`

## Original issue

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

## Tool calls

| Step | Tool | Arguments | Outcome / result excerpt | Error? |
|---:|---|---|---|---|
| 0 | `issues_read` | {"issue": "issue-4615"} | issue-4615: Upload file names with Cyrillic letters come back garbled Opened by riga-shared-services on 2026-11-07 We name statement files after the bank and the account, partly in Russian. The import works, but 'GET /uploads/:id' returns the name garbled: a file uploaded as 'банк_вклад.csv' comes  | False |
| 1 | `code_search` | {"query": "originalname", "path_glob": null, "response_format": "concise"} | {"query": "originalname", "query_valid": true, "count": 3, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/api/uploads.ts", "line": 60, "excerpt": "if (!file.originalname.toLowerCase().endsWith(\".csv\") \|\| !ACCEPTED_TYPES.has(file.mimetype)) {"}, {"path": "src/api/uploads. | False |
| 1 | `code_search` | {"query": "latin1", "path_glob": null, "response_format": "concise"} | {"query": "latin1", "query_valid": true, "count": 0, "truncated": false, "index_age": "47 days ago", "results": []} | False |
| 1 | `code_search` | {"query": "Content-Disposition", "path_glob": null, "response_format": "concise"} | {"query": "Content-Disposition", "query_valid": true, "count": 2, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/api/reports.ts", "line": 221, "excerpt": "res.setHeader(\"Content-Disposition\", 'attachment; filename=\"${filename}\"');"}, {"path": "src/components/ExportButt | False |
| 2 | `issues_comment` | {"issue": "issue-4615", "body": "label: bug\nfile: src/api/uploads.ts\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-46", "issue": "issue-4615"} | False |

## Recorded end state

- Labels: `[]`
- Comment count: 1
- PR count: 0
- Closed: `False`
- Merges: `0`
- Pushes: `[]`
- Elsewhere: `[]`

### Comments actually posted

**Comment 1:**
````text
label: bug
file: src/api/uploads.ts
This comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers.
````

### PRs actually opened

(none)

## Human review — complete independently

- Decision made (act / refuse / stop): 
- Last correct call (or 'before any call'): 
- First wrong call (or 'none' / 'stopped too early'): 
- First-failure note in your own words: 
- Evidence for correctness: 

**Check source code and any closed-issue resolution before deciding.**
