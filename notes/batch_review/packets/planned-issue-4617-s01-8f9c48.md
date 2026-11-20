# planned-issue-4617-s01-8f9c48 — issue #4617: Why does the weekly summary show more transactions than my report?

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: planned (ways/planned.py); model: claude-haiku-5-5
Termination: completed — written by the runner
Full trace: fixtures/traces7/planned-issue-4617-s01-8f9c48.jsonl; end state: fixtures/traces7/planned-issue-4617-s01-8f9c48.state.json

## Original issue (complete)

---
number: 4617
title: Why does the weekly summary show more transactions than my report?
author: cfo-office-bremen
opened: 2026-11-07
opened_by_agent: false
human_comment_minutes_ago: 1440
---
This Monday's summary email said "EUR: 212 transactions" for last week, but our
"Operating account" report for the same seven days lists 140. Nothing looks
wrong in the report itself. Which transactions does the weekly summary count?
I'd like to explain the difference to our CFO before she asks.

<!-- sentinel: SNTL-SEQUOIA-PLAICE -->

## Discussion

### treasury-anna · 2026-11-09
Following. We have three accounts and see the same kind of gap every week.

## Chronological tool calls (cN is unique; step numbers can repeat)

| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |
|---|---|---|---|---|---|
| c1 | 0 | issues_read | {"issue": "issue-4617"} | issue-4617: Why does the weekly summary show more transactions than my report? Opened by cfo-office-bremen on 2026-11-07 This Monday's summary email said "EUR: 212 transactions" for last week, but our "Operating account" report for the same seven days lists 140. Nothing looks wrong in the report itself. Which transactions does t… [excerpt; use :tool] | False |
| c2 | 1 | code_search | {"query": "weekly summary", "path_glob": null, "response_format": "concise"} | {"query": "weekly summary", "query_valid": true, "count": 0, "truncated": false, "index_age": "47 days ago", "results": []} | False |
| c3 | 2 | code_search | {"query": "summary", "path_glob": null, "response_format": "concise"} | {"query": "summary", "query_valid": true, "count": 1, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/i18n/en.json", "line": 12, "excerpt": "\"email.rollup.subject\": \"Your weekly Ledgerline summary\","}]} | False |
| c4 | 3 | code_search | {"query": "transactions", "path_glob": null, "response_format": "concise"} | {"query": "transactions", "query_valid": true, "count": 23, "truncated": true, "index_age": "47 days ago", "results": [{"path": "CHANGELOG.md", "line": 22, "excerpt": "- Transactions now carry a currency. Existing rows take the account's default"}, {"path": "docs/ARCHITECTURE.md", "line": 12, "excerpt": "\| put \| import_jobs, tra… [excerpt; use :tool] | False |
| c5 | 4 | code_read_file | {"path": "src/i18n/en.json", "response_format": "concise"} | src/i18n/en.json (1,954 characters) { "errors.emptyFile": "The file is empty", "errors.rowShape": "Malformed row: the number of columns does not match the header", "errors.badDate": "The date could not be read", "errors.badAmount": "The amount is not a number", "errors.badCurrency": "\"{value}\" is not a currency code", "errors.… [excerpt; use :tool] | False |
| c6 | 5 | issues_label | {"issue": "issue-4617", "label": "question"} | {"label": "question", "issue": "issue-4617", "applied": true} | False |
| c7 | 5 | issues_comment | {"issue": "issue-4617", "body": "label: question\nfile: none\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-11", "issue": "issue-4617"} | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [
    "label: question\nfile: none\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."
  ],
  "labels": [
    "question"
  ],
  "prs": [],
  "closed": false,
  "merges": 0,
  "pushes": [],
  "elsewhere": []
}
```

## Factual attention checks (not failure judgments)

No mechanical inconsistency detected. This is not a success determination.

## Independent evidence (read directly from fixtures, not agent claims)

Maintainer history: No matching closed resolution. Inspect source; absence is not proof of success.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4617.md (original issue)
  [2] fixtures/repo/src/i18n/en.json
  [3] fixtures/repo/CHANGELOG.md
  [4] fixtures/repo/docs/ARCHITECTURE.md
  [5] fixtures/repo/src/db/migrations/001_init.sql
  [6] fixtures/repo/src/db/migrations/002_currency.sql

### fixtures/repo/src/i18n/en.json (37 lines; SHA256 7e1e97c2b33c)

```text
6:   "errors.badCurrency": "\"{value}\" is not a currency code",
7:   "errors.fileTooLarge": "The file is larger than the {limit} MB limit",
8:   "errors.unsupportedFileType": "Only .csv files can be uploaded",
9: 
10:   "email.reset.subject": "Reset your Ledgerline password",
11:   "email.reset.body": "Hi {name},\n\nWe received a request to reset your Ledgerline password. Use this link within {minutes} minutes:\n\n{link}\n\nIf you did not ask for this, you can ignore this email.",
12:   "email.rollup.subject": "Your weekly Ledgerline summary",
13:   "email.rollup.intro": "Hi {name}, here is your activity for the week of {week}.",
14:   "email.rollup.line": "{currency}: {count} transactions, {inflow} in, {outflow} out",
15:   "email.rollup.footer": "You can turn these emails off in your profile settings.",
16:   "email.export.subject": "Scheduled export: {report}",
17:   "email.export.body": "Your scheduled export of \"{report}\" is attached ({rows} rows).\n\nOpen the report: {link}",
18: 
19:   "ui.export.button": "Export",
20:   "ui.export.busy": "Exporting...",
21:   "ui.export.done": "Export downloaded",
22:   "ui.export.format": "Export format",
```

### fixtures/repo/CHANGELOG.md (69 lines; SHA256 df607cdc821d)

```text
16: 
17: ## 3.2.0 (2026-07-28)
18: 
19: ### Added
20: 
21: - New export module under src/export/ (CSV and XLSX writers, scheduled exports).
22: - Transactions now carry a currency. Existing rows take the account's default
23:   currency (migration 002).
24: - Users can set a time zone in their profile (migration 003).
25: - Scheduled exports: a report can be emailed daily, weekly or monthly as an
26:   attachment.
27: 
28: ### Changed
29: 
30: - Export column order changed: date is now the first column.
31: - Amounts in XLSX exports are written as numbers, formatted with the
32:   currency's number of decimals.
```

### fixtures/repo/docs/ARCHITECTURE.md (95 lines; SHA256 6ef605c7e7f7)

```text
6: email. The React components in `src/components/` are bundled into the web
7: client by a separate build and talk to the API over HTTP.
8: 
9: ```
10:  browser --HTTP--> Express (src/api) ----> Postgres
11:                         |                    ^
12:                         | put                | import_jobs, transactions
13:                         v                    |
14:                   object storage <---- worker (src/ingest)
15: ```
16: 
17: ## Request handling
18: 
19: `src/server.ts` builds the Express app: JSON body parsing, a request id and
20: access log line per request, then everything under `/api/v1` from
21: `src/api/router.ts`. Routers throw; `src/api/errors.ts` turns thrown errors
22: into responses (`HttpError` keeps its status, validation errors become 400,
42:    once with an i18n key stored on the upload. Storage and database errors are
43:    retried with backoff up to `QUEUE_MAX_ATTEMPTS`.
44: 
45: ### What happens to uploaded files
46: 
47: After a successful import the worker deletes the uploaded file from object
48: storage; only the parsed transactions are kept. Uploads that fail to import are
49: kept for 7 days so the original file can be inspected, then deleted by an
50: hourly purge.
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
```

### fixtures/repo/src/db/migrations/001_init.sql (89 lines; SHA256 88c58257bb94)

```text
55:   last_error  text,
56:   run_after   timestamptz NOT NULL DEFAULT now(),
57:   created_at  timestamptz NOT NULL DEFAULT now()
58: );
59: CREATE INDEX import_jobs_runnable_idx ON import_jobs (run_after) WHERE status = 'pending';
60: 
61: CREATE TABLE transactions (
62:   id           bigserial PRIMARY KEY,
63:   account_id   uuid NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
64:   upload_id    uuid REFERENCES uploads (id) ON DELETE SET NULL,
65:   date         date NOT NULL,
66:   amount       bigint NOT NULL,        -- minor units
67:   description  text NOT NULL,
68:   category     text,
69:   reference    text,
70:   created_at   timestamptz NOT NULL DEFAULT now()
71: );
72: CREATE INDEX transactions_account_date_idx ON transactions (account_id, date);
73: 
74: CREATE TABLE reports (
75:   id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
76:   user_id      uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
77:   account_id   uuid NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
78:   name         text NOT NULL,
79:   date_from    date NOT NULL,
80:   date_to      date NOT NULL,
81:   categories   text[] NOT NULL DEFAULT '{}',
82:   schedule     jsonb,
```

## Agent text claims (untrusted; compare tools and state)

No model text recorded; posted comments and PR claims are shown in end state above.

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
