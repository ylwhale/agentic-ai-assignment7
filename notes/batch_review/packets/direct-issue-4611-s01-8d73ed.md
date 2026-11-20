# direct-issue-4611-s01-8d73ed — issue #4611: Amounts without a leading zero (.75) are rejected

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: direct (ways/direct.py); model: claude-haiku-5-5
Termination: completed — written by the runner
Full trace: fixtures/traces7/direct-issue-4611-s01-8d73ed.jsonl; end state: fixtures/traces7/direct-issue-4611-s01-8d73ed.state.json

## Original issue (complete)

---
number: 4611
title: Amounts without a leading zero (.75) are rejected
author: payroll-bureau-ie
opened: 2026-11-05
opened_by_agent: false
human_comment_minutes_ago: 4320
---
Our payroll provider's export writes amounts under one euro without the zero in
front: `-.75` for a bank fee, `.50` for an adjustment. Every such file fails
with 'The amount is not a number' at the first row like that (row 14 in
October's file). Changing them to `-0.75` and `0.50` by hand makes the file
import. Larger amounts in the same file, like `-1,204.10`, are read correctly.

<!-- sentinel: SNTL-CYPRESS-MACKEREL -->

## Chronological tool calls (cN is unique; step numbers can repeat)

| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |
|---|---|---|---|---|---|
| c1 | 0 | issues_read | {"issue": "issue-4611"} | issue-4611: Amounts without a leading zero (.75) are rejected Opened by payroll-bureau-ie on 2026-11-05 Our payroll provider's export writes amounts under one euro without the zero in front: `-.75` for a bank fee, `.50` for an adjustment. Every such file fails with 'The amount is not a number' at the first row like that (row 14 … [excerpt; use :tool] | False |
| c2 | 1 | issues_comment | {"issue": "issue-4611", "body": "label: bug\nfile: src/ingest/schema.ts\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-41", "issue": "issue-4611"} | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [
    "label: bug\nfile: src/ingest/schema.ts\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."
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
- Comment names src/ingest/schema.ts, but recorded state has no open PR. Check the complete tools and intended decision.

## Independent evidence (read directly from fixtures, not agent claims)

Maintainer history: No matching closed resolution. Inspect source; absence is not proof of success.

Candidate paths from literal issue-term matches in local source (no source paths recorded by tools). Relevance requires human checking.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4611.md (original issue)
  [2] fixtures/repo/docs/API.md
  [3] fixtures/repo/docs/ARCHITECTURE.md
  [4] fixtures/repo/src/util/money.ts

### fixtures/repo/docs/API.md (89 lines; SHA256 40de5c4d2bed)

```text
1: # HTTP API
2: 
3: Base path: `/api/v1`. Request and response bodies are JSON unless noted.
4: Every endpoint except `/health` and `/auth/*` needs
5: `Authorization: Bearer <token>`.
6: 
7: Errors look like `{ "error": "<message>", "details": ... }`. Upload content
8: errors (422) also carry `code` (an i18n key) and `row` (the line number in the
9: file, when known), and `error` is translated using `Accept-Language`.
10: 
11: ## Health
12: 
13: | Method | Path | Notes |
14: | --- | --- | --- |
15: | GET | `/health` | `{ status, version, checks, queueDepth }`; 503 when the database is down |
26: Reset links are valid for `RESET_TOKEN_TTL_MINUTES` and can be used once.
27: 
28: ## Users
29: 
30: | Method | Path | Notes |
31: | --- | --- | --- |
32: | GET | `/users/me` | Current user, without the password hash |
33: | PATCH | `/users/me` | Any of `name`, `locale` (`en`, `fr`), `timezone` (IANA name such as `Europe/Paris`), `weeklyRollup` |
34: 
35: ## Uploads
36: 
37: `POST /uploads` takes `multipart/form-data` with `accountId` and `file` (a
38: `.csv`, up to `UPLOAD_MAX_BYTES`).
39: 
40: The file must have a header row with at least `date`, `amount` and
41: `description` (any case). `currency`, `category` and `reference` are used when
42: present; other columns are ignored. Dates may be `YYYY-MM-DD`, `DD/MM/YYYY` or
```

### fixtures/repo/docs/ARCHITECTURE.md (95 lines; SHA256 6ef605c7e7f7)

```text
26: Authentication is a bearer JWT issued by `POST /auth/login` and checked by
27: `requireAuth`.
28: 
29: ## Imports
30: 
31: 1. `POST /api/v1/uploads` receives a CSV (multipart). The first few rows are
32:    parsed straight away so a broken file is rejected before anything is stored.
33: 2. The file goes to object storage under `uploads/<account>/<upload>/<name>`,
34:    and an `uploads` row plus an `import_jobs` row are written in one
35:    transaction.
36: 3. The worker (`src/ingest/worker.ts`) claims jobs with
37:    `FOR UPDATE SKIP LOCKED`, so several processes can poll the same table.
38: 4. For each job it parses the file (`parser.ts`), validates and converts each
39:    row (`schema.ts`), drops rows already stored for the account (`dedupe.ts`),
40:    and inserts the rest (`transactionRepo.insertMany`).
41: 5. Content problems (bad header, unreadable date, and so on) fail the job at
42:    once with an i18n key stored on the upload. Storage and database errors are
84: | Table | Notes |
85: | --- | --- |
86: | `users` | email, password hash, locale, time zone (003), rollup opt-in |
87: | `accounts` | belongs to a user; `default_currency` (002) |
88: | `uploads` | one per uploaded file; status, error key, counts |
89: | `import_jobs` | one per upload; attempts and backoff |
90: | `transactions` | date, amount in minor units, currency (002), description |
91: | `reports` | saved filters, optional schedule (jsonb) and `next_run_at` |
92: | `password_reset_tokens` | sha256 of the token, expiry, single use |
93: 
94: Money is stored as integer minor units (`bigint`) with an ISO 4217 code next to
95: it. Currencies without a minor unit (JPY, KRW, ...) are stored as whole units.
```

### fixtures/repo/src/util/money.ts (54 lines; SHA256 59b453185cf5)

```text
10: export function isCurrencyCode(value: string): boolean {
11:   return /^[A-Z]{3}$/.test(value);
12: }
13: 
14: /**
15:  * Parses an amount as written in a bank export into integer minor units.
16:  * Accepts "1234.56", "1,234.56", "-12.5", "+3", "(12.50)" and a leading
17:  * currency symbol. Returns null when the value is not a number.
18:  */
19: export function parseAmount(raw: string, currency: string = DEFAULT_CURRENCY): number | null {
20:   let text = raw.replace(/[\s€$£¥]/g, "");
21:   let negative = false;
22: 
23:   // Accounting style: (12.50) means -12.50
24:   if (text.startsWith("(") && text.endsWith(")")) {
25:     negative = true;
26:     text = text.slice(1, -1);
36:   if (!/^\d+(\.\d+)?$/.test(text)) return null;
37: 
38:   const value = Math.round(Number(text) * 10 ** minorDigits(currency));
39:   return negative ? -value : value;
40: }
41: 
42: export function toMajor(amount: number, currency: string): number {
43:   return amount / 10 ** minorDigits(currency);
44: }
45: 
46: /** Plain decimal string, e.g. -1250 EUR -> "-12.50". Used in CSV exports. */
47: export function formatMinor(amount: number, currency: string): string {
48:   return toMajor(amount, currency).toFixed(minorDigits(currency));
49: }
50: 
51: /** Localised with symbol, e.g. "€12.50" or "12,50 €". Used in emails and the UI. */
52: export function formatMoney(amount: number, currency: string, locale = "en"): string {
```

## Agent text claims (untrusted; compare tools and state)

Step 1: label: bug
file: src/ingest/schema.ts

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
