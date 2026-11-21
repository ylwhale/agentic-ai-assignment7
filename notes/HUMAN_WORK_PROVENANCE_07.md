# Assignment 7 — Human Work Provenance

## 1. Historical Trace Reviews (Part A)

I personally reviewed 40 recorded traces and evaluated the agent's decisions, tool calls, and final outcomes against the available evidence.

The first 17 reviews were completed using an earlier documentation format that did not include the explicit `Human confirmed: yes` field. The remaining 23 reviews used a newer format with explicit human confirmation.

All 40 reviews represent my own assessments. I reviewed the recorded traces, identified the first incorrect action when applicable, and determined whether each run completed the expected workflow. I also used the original issues, relevant source code, and maintainer resolutions to support my conclusions.

Reviews 6–12 retained an outdated "draft for review" heading after my assessments were complete. I later updated those headings to "My observation" without changing the original observations.

## 2. Golden Task Labels (Part A)

I independently determined the expected outcomes for the 30 golden tasks using the issue descriptions, relevant source code, and recorded maintainer resolutions.

## 3. Judge Criterion and Reference Labels (Part D)

I personally reviewed and finalized the judge criterion in `eval/judge/criterion.md`, including the definitions of supported and unsupported evidence.

I independently evaluated all 60 outputs in `fixtures/judge/outputs/` and recorded the pass/fail decisions and supporting reasons in `eval/labels/labels.csv`.