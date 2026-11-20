# direct-issue-4625-s01-b6476b — issue #4625: CSV exports open in a single column in German Excel

**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**

Implementation: direct (ways/direct.py); model: claude-haiku-5-5
Termination: completed — written by the runner
Full trace: fixtures/traces7/direct-issue-4625-s01-b6476b.jsonl; end state: fixtures/traces7/direct-issue-4625-s01-b6476b.state.json

## Original issue (complete)

---
number: 4625
title: CSV exports open in a single column in German Excel
author: vienna-accounting-hk
opened: 2026-11-10
opened_by_agent: false
human_comment_minutes_ago: 4320
---
Our Vienna office runs Excel with Austrian settings. Double-clicking a CSV
export puts each whole line into column A, as
`Date,Amount,Currency,Description,Category`, because Excel there expects
semicolons between columns. XLSX opens fine, but the tool we load the files
into only takes CSV. Could the CSV export offer a semicolon as the separator,
as a choice next to the format?

<!-- sentinel: SNTL-OAK-SWORDFISH -->

## Chronological tool calls (cN is unique; step numbers can repeat)

| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |
|---|---|---|---|---|---|
| c1 | 0 | issues_read | {"issue": "issue-4625"} | issue-4625: CSV exports open in a single column in German Excel Opened by vienna-accounting-hk on 2026-11-10 Our Vienna office runs Excel with Austrian settings. Double-clicking a CSV export puts each whole line into column A, as `Date,Amount,Currency,Description,Category`, because Excel there expects semicolons between columns.… [excerpt; use :tool] | False |
| c2 | 1 | issues_comment | {"issue": "issue-4625", "body": "label: feature\nfile: src/exportUtils.ts\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."} | {"comment": "comment-40", "issue": "issue-4625"} | False |

## Recorded end state (authority for effects)

```json
{
  "comments": [
    "label: feature\nfile: src/exportUtils.ts\nThis comment was written by RepoMind, an automated triage agent. To reach a person, mention @ledgerline/maintainers."
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

- Comment says label 'feature'; actual recorded labels are []. A comment does not apply a label.
- Comment names src/exportUtils.ts, but recorded state has no open PR. Check the complete tools and intended decision.

## Independent evidence (read directly from fixtures, not agent claims)

Maintainer history: Done in #980: the CSV export can use a semicolon separator; the option lives in toDelimited in src/exportUtils.ts.

Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.
Source excerpts are partial; :source N opens complete original source.
  [1] fixtures/issues/pool/4625.md (original issue)
  [2] fixtures/closed_issues.yaml issue #4625 (maintainer resolution)
  [3] fixtures/repo/src/exportUtils.ts

### fixtures/repo/src/exportUtils.ts (62 lines; SHA256 ae2b9a3209ff)

```text
13: export const CONTENT_TYPES: Record<ExportFormat, string> = {
14:   csv: "text/csv; charset=utf-8",
15:   xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
16: };
17: 
18: // Since 3.2.0 date comes first, which is what most accounting tools expect on import.
19: export const COLUMN_ORDER = ["date", "amount", "currency", "description", "category"] as const;
20: 
21: export type ExportColumn = (typeof COLUMN_ORDER)[number];
22: 
23: export const COLUMN_LABELS: Record<ExportColumn, string> = {
24:   date: "Date",
25:   amount: "Amount",
26:   currency: "Currency",
27:   description: "Description",
28:   category: "Category",
29: };
44:     default:
45:       return row[column];
46:   }
47: }
48: 
49: /** A header line followed by one line per row, in the given column order. */
50: export function toDelimited(rows: readonly ReportRow[], columns: readonly ExportColumn[] = COLUMN_ORDER): string {
51:   const lines = [columns.map((column) => escapeField(COLUMN_LABELS[column])).join(",")];
52:   for (const row of rows) {
53:     lines.push(columns.map((column) => escapeField(cellValue(row, column))).join(","));
54:   }
55:   return lines.join("\n") + "\n";
56: }
57: 
58: /** "March expenses" + csv -> "march-expenses-2026-04-01.csv" */
59: export function formatExportFilename(reportName: string, format: ExportFormat, at: Date = new Date()): string {
60:   const base = slugify(reportName) || "report";
```

## Agent text claims (untrusted; compare tools and state)

Step 1: label: feature
file: src/exportUtils.ts

Use :tool cN for full arguments/results; :trace for all original JSONL events;
:control for rejected/proposed calls and validation events; :source N for complete independent source.
