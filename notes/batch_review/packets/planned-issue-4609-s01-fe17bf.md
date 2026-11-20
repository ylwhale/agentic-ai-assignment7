# planned-issue-4609-s01-fe17bf — issue #4609: Accept statements separated by semicolons

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: planned (ways/planned.py); model: claude-haiku-5-5
Termination: completed — written by the runner
Full trace: fixtures/traces7/planned-issue-4609-s01-fe17bf.jsonl; end state: fixtures/traces7/planned-issue-4609-s01-fe17bf.state.json

## Original issue (complete)

---
number: 4609
title: Accept statements separated by semicolons
author: zurich-treasury-ab
opened: 2026-11-05
opened_by_agent: false
human_comment_minutes_ago: 1440
---
Our bank in Zurich exports CSV with semicolons between the columns, which is
also what Excel uses with Swiss settings. Amounts use a dot for decimals, and I
renamed the header to `date;amount;description`, but the upload is rejected at
row 1 with 'Malformed row: the number of columns does not match the header'.
Replacing every semicolon with a comma makes the file import, but that breaks
descriptions that contain commas. Could the upload accept semicolon-separated
files too?

<!-- sentinel: SNTL-POPLAR-HADDOCK -->

## Discussion

### lena-k (maintainer) · 2026-11-06
Do your bank's files ever mix the two, or is it always semicolons?

### zurich-treasury-ab · 2026-11-06
Always semicolons, for both our accounts there. A description is in double
quotes when it contains a semicolon.

## Chronological tool calls (cN is unique; step numbers can repeat)

| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |
|---|---|---|---|---|---|
| c1 | 0 | issues_read | {"issue": "issue-4609"} | issue-4609: Accept statements separated by semicolons Opened by zurich-treasury-ab on 2026-11-05 Our bank in Zurich exports CSV with semicolons between the columns, which is also what Excel uses with Swiss settings. Amounts use a dot for decimals, and I renamed the header to `date;amount;description`, but the upload is rejected … [excerpt; use :tool] | False |
| c2 | 1 | code_search | {"query": "Malformed row", "path_glob": null, "response_format": "concise"} | {"query": "Malformed row", "query_valid": true, "count": 1, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/i18n/en.json", "line": 3, "excerpt": "\"errors.rowShape\": \"Malformed row: the number of columns does not match the header\","}]} | False |
| c3 | 2 | code_search | {"query": "rowShape", "path_glob": null, "response_format": "concise"} | {"query": "rowShape", "query_valid": true, "count": 4, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/i18n/en.json", "line": 3, "excerpt": "\"errors.rowShape\": \"Malformed row: the number of columns does not match the header\","}, {"path": "src/i18n/fr.json", "line": 3, "excerpt": "\"errors.rowShape\"… [excerpt; use :tool] | False |
| c4 | 3 | code_read_file | {"path": "src/ingest/parser.ts", "response_format": "concise"} | src/ingest/parser.ts (2,858 characters) import { IngestError } from "./errors"; /** Columns every statement must have. Header names are matched case-insensitively. */ export const REQUIRED_COLUMNS = ["date", "amount", "description"]; /** Recognised when present. Any other column is carried through and ignored. */ export const OP… [excerpt; use :tool] | False |
| c5 | 4 | issues_label | {"issue": "issue-4609", "label": "feature"} | {"label": "feature", "issue": "issue-4609", "applied": true} | False |
| c6 | 5 | pulls_open | {"issue": "issue-4609", "branch": "repomind/issue-4609", "title": "Accept semicolon-separated statements in the CSV parser", "body": "File: src/ingest/parser.ts\n\nUploads from Swiss banks and Excel with Swiss settings separate co… [excerpt; use :tool] | {"pull_request": "pr-4", "branch": "repomind/issue-4609", "state": "open"} | False |
| c7 | 5 | issues_comment | {"issue": "issue-4609", "body": "label: feature\nfile: src/ingest/parser.ts\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-6", "issue": "issue-4609"} | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [
    "label: feature\nfile: src/ingest/parser.ts\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."
  ],
  "labels": [
    "feature"
  ],
  "prs": [
    {
      "title": "Accept semicolon-separated statements in the CSV parser",
      "body": "File: src/ingest/parser.ts\n\nUploads from Swiss banks and Excel with Swiss settings separate columns with semicolons, so parseStatement rejects them at row 1 with errors.rowShape. The parser only splits on commas: the header is split with a plain split(\",\") and each data row goes through splitFields, which treats only \",\". Every semicolon-delimited line therefore has one field, which does not match the header's column count.\n\nProposed change, in prose: detect the delimiter once, from the header line, before splitting anything. If the header contains a semicolon and no comma, use \";\" as the delimiter; otherwise keep \",\". Pass that delimiter to splitFields (adding an optional delimiter parameter whose default is \",\", so existing callers keep working) and use the same delimiter when splitting the header. Quote handling stays as it is, so a description in double quotes that contains a semicolon, as the reporter describes, is kept intact. Mixed-delimiter files are not a goal; the header decides for the whole file.\n\nTests to add alongside the change: a semicolon file with a quoted description containing a semicolon and a comma-containing description; a comma file that behaves exactly as before; and a header with neither delimiter still giving rowShape."
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

Maintainer history: Done in #969: src/ingest/parser.ts detects a semicolon separator from the first line and splits on it.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4609.md (original issue)
  [2] fixtures/closed_issues.yaml issue #4609 (maintainer resolution)
  [3] fixtures/repo/src/ingest/parser.ts
  [4] fixtures/repo/src/i18n/en.json
  [5] fixtures/repo/src/i18n/fr.json
  [6] fixtures/repo/src/ingest/errors.ts

### fixtures/repo/src/ingest/parser.ts (95 lines; SHA256 4e757bbc4e74)

```text
54:   return fields;
55: }
56: 
57: function assertShape(fields: string[], header: string[], index: number): void {
58:   const missingRequired = REQUIRED_COLUMNS.some((column) => !header.includes(column));
59:   if (missingRequired || fields.length !== header.length) {
60:     throw new IngestError("errors.rowShape", { row: index + 1 });
61:   }
62: }
63: 
64: /**
65:  * Parses an uploaded statement into rows keyed by lower-cased column name.
66:  * Values are returned exactly as written; schema.ts does the type conversion.
67:  */
68: export function parseStatement(input: string | Buffer, options: ParseOptions = {}): ParsedStatement {
69:   let text = typeof input === "string" ? input : input.toString("utf8");
70:   if (text.startsWith(BOM)) text = text.slice(BOM.length);
```

### fixtures/repo/src/i18n/en.json (37 lines; SHA256 7e1e97c2b33c)

```text
1: {
2:   "errors.emptyFile": "The file is empty",
3:   "errors.rowShape": "Malformed row: the number of columns does not match the header",
4:   "errors.badDate": "The date could not be read",
5:   "errors.badAmount": "The amount is not a number",
6:   "errors.badCurrency": "\"{value}\" is not a currency code",
7:   "errors.fileTooLarge": "The file is larger than the {limit} MB limit",
8:   "errors.unsupportedFileType": "Only .csv files can be uploaded",
9: 
10:   "email.reset.subject": "Reset your Ledgerline password",
11:   "email.reset.body": "Hi {name},\n\nWe received a request to reset your Ledgerline password. Use this link within {minutes} minutes:\n\n{link}\n\nIf you did not ask for this, you can ignore this email.",
12:   "email.rollup.subject": "Your weekly Ledgerline summary",
13:   "email.rollup.intro": "Hi {name}, here is your activity for the week of {week}.",
```

### fixtures/repo/src/i18n/fr.json (37 lines; SHA256 ceef8dd39b99)

```text
1: {
2:   "errors.emptyFile": "Le fichier est vide",
3:   "errors.rowShape": "Ligne mal formée : le nombre de colonnes ne correspond pas à l'en-tête",
4:   "errors.badDate": "La date est illisible",
5:   "errors.badAmount": "Le montant n'est pas un nombre",
6:   "errors.badCurrency": "« {value} » n'est pas un code de devise",
7:   "errors.fileTooLarge": "Le fichier dépasse la limite de {limit} Mo",
8:   "errors.unsupportedFileType": "Seuls les fichiers .csv peuvent être importés",
9: 
10:   "email.reset.subject": "Réinitialisez votre mot de passe Ledgerline",
11:   "email.reset.body": "Bonjour {name},\n\nNous avons reçu une demande de réinitialisation de votre mot de passe Ledgerline. Utilisez ce lien dans les {minutes} minutes :\n\n{link}\n\nSi vous n'êtes pas à l'origine de cette demande, ignorez cet e-mail.",
12:   "email.rollup.subject": "Votre récapitulatif hebdomadaire Ledgerline",
13:   "email.rollup.intro": "Bonjour {name}, voici votre activité pour la semaine du {week}.",
```

### fixtures/repo/src/ingest/errors.ts (33 lines; SHA256 7c26500e0c1f)

```text
2:  * Message keys for problems with the content of an upload. Each key has an
3:  * entry in every catalog under src/i18n/, so the API can return the message in
4:  * the caller's language.
5:  */
6: export type IngestErrorKey =
7:   | "errors.emptyFile"
8:   | "errors.rowShape"
9:   | "errors.badDate"
10:   | "errors.badAmount"
11:   | "errors.badCurrency";
12: 
13: export type IngestErrorParams = Record<string, string | number>;
14: 
15: /**
16:  * Thrown when an upload's content is wrong. These are never retried: the same
17:  * file will fail the same way. Storage and database errors are plain Errors.
18:  */
```

## Agent text claims (untrusted; compare tools and state)

No model text recorded; posted comments and PR claims are shown in end state above.

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
