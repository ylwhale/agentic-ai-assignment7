# planned-issue-4611-s01-b3cbe5 — issue #4611: Amounts without a leading zero (.75) are rejected

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: planned (ways/planned.py); model: claude-haiku-5-5
Termination: completed — written by the runner
Full trace: fixtures/traces7/planned-issue-4611-s01-b3cbe5.jsonl; end state: fixtures/traces7/planned-issue-4611-s01-b3cbe5.state.json

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
| c2 | 1 | code_search | {"query": "The amount is not a number", "path_glob": null, "response_format": "concise"} | {"query": "The amount is not a number", "query_valid": true, "count": 1, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/i18n/en.json", "line": 5, "excerpt": "\"errors.badAmount\": \"The amount is not a number\","}]} | False |
| c3 | 2 | code_search | {"query": "badAmount", "path_glob": null, "response_format": "concise"} | {"query": "badAmount", "query_valid": true, "count": 4, "truncated": false, "index_age": "47 days ago", "results": [{"path": "src/i18n/en.json", "line": 5, "excerpt": "\"errors.badAmount\": \"The amount is not a number\","}, {"path": "src/i18n/fr.json", "line": 5, "excerpt": "\"errors.badAmount\": \"Le montant n'est pas un nombr… [excerpt; use :tool] | False |
| c4 | 3 | code_read_file | {"path": "src/ingest/schema.ts", "response_format": "concise"} | src/ingest/schema.ts (1,733 characters) import { z } from "zod"; import type { IncomingTransaction } from "../types"; import { parseStatementDate } from "../util/dates"; import { isCurrencyCode, parseAmount } from "../util/money"; import { normalizeDescription } from "../util/strings"; import { IngestError } from "./errors"; imp… [excerpt; use :tool] | False |
| c5 | 4 | issues_label | {"issue": "issue-4611", "label": "bug"} | {"label": "bug", "issue": "issue-4611", "applied": true} | False |
| c6 | 5 | pulls_open | {"issue": "issue-4611", "branch": "repomind/issue-4611", "title": "Accept amounts under one euro written without a leading zero, such as -.75 and .50", "body": "File: src/ingest/schema.ts\n\nThe row check in toTransaction calls pa… [excerpt; use :tool] | {"pull_request": "pr-5", "branch": "repomind/issue-4611", "state": "open"} | False |
| c7 | 5 | issues_comment | {"issue": "issue-4611", "body": "label: bug\nfile: src/ingest/schema.ts\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-7", "issue": "issue-4611"} | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [
    "label: bug\nfile: src/ingest/schema.ts\n\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."
  ],
  "labels": [
    "bug"
  ],
  "prs": [
    {
      "title": "Accept amounts under one euro written without a leading zero, such as -.75 and .50",
      "body": "File: src/ingest/schema.ts\n\nThe row check in toTransaction calls parseAmount(row.amount, currency) and throws errors.badAmount (\"The amount is not a number\") when the result is null, at line 42. Amounts such as `-.75` and `.50` come back null, while `-1,204.10` parses correctly, so the rejection comes from the amount parsing rather than from the row checks around it.\n\nProposed change: make the amount parsing accept a sign followed directly by a decimal point with no integer digits, and a bare leading decimal point, treating `-.75` as -0.75 and `.50` as 0.50 before the value is validated. Keep thousands separators working as they do now, and keep rejecting strings that are not numbers. The change belongs in the parsing that schema.ts relies on; the function parseAmount lives in src/util/money.ts, which was not read in this triage, so the exact edit there should be confirmed when the pull request is reviewed.\n\nAdd a test with a file containing `-.75`, `.50` and `-1,204.10` in the same import, and confirm all three rows import with the expected amounts."
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
  [1] fixtures/issues/pool/4611.md (original issue)
  [2] fixtures/repo/src/ingest/schema.ts
  [3] fixtures/repo/src/i18n/en.json
  [4] fixtures/repo/src/i18n/fr.json
  [5] fixtures/repo/src/ingest/errors.ts

### fixtures/repo/src/ingest/schema.ts (52 lines; SHA256 32b559852774)

```text
36:   const currency = (row.currency || defaults.currency).toUpperCase();
37:   if (!isCurrencyCode(currency)) {
38:     throw new IngestError("errors.badCurrency", { row: rowNumber, value: currency });
39:   }
40: 
41:   const amount = parseAmount(row.amount, currency);
42:   if (amount === null) throw new IngestError("errors.badAmount", { row: rowNumber });
43: 
44:   return {
45:     date,
46:     amount,
47:     currency,
48:     description: normalizeDescription(row.description),
49:     category: emptyToNull(row.category),
50:     reference: emptyToNull(row.reference),
51:   };
52: }
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
14:   "email.rollup.line": "{currency}: {count} transactions, {inflow} in, {outflow} out",
15:   "email.rollup.footer": "You can turn these emails off in your profile settings.",
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
14:   "email.rollup.line": "{currency} : {count} opérations, {inflow} en entrée, {outflow} en sortie",
15:   "email.rollup.footer": "Vous pouvez désactiver ces e-mails dans les paramètres de votre profil.",
```

### fixtures/repo/src/ingest/errors.ts (33 lines; SHA256 7c26500e0c1f)

```text
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
19: export class IngestError extends Error {
20:   readonly key: IngestErrorKey;
```

## Agent text claims (untrusted; compare tools and state)

No model text recorded; posted comments and PR claims are shown in end state above.

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
