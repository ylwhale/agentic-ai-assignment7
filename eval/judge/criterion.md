# Judge criterion — Support for a triage comment's factual claims

## 1. Evaluation question

Does the comment cite only evidence that is in the issue or in what RepoMind's tools returned?

## 2. Unit of evaluation

One RepoMind triage comment is evaluated against the original issue and the recorded tool results available to RepoMind during that run. The evaluation determines whether the comment's factual claims are supported by these sources, without relying on external information.

## 3. Pass definition

A comment passes when all its factual claims are supported by the original issue or the recorded tool results. Statements expressing uncertainty are acceptable if they are clearly presented as possibilities rather than confirmed facts. Suggested actions or recommendations are also acceptable as long as the comment does not falsely claim that those actions have already been completed.

## 4. Fail definition

A comment fails when at least one factual claim is unsupported by or contradicts the original issue or recorded tool results. This includes claiming that tests were run, files were modified, or actions were completed without evidence. It also fails when assumptions, guesses, or unverified explanations are presented as confirmed facts.

## 5. Unsupported-evidence cases

- **Test results:** A comment fails if it claims that tests were executed or passed without recorded evidence of those test results.
- **Actions taken:** A comment fails if it claims that a pull request was created, code was committed, or changes were merged or pushed without supporting tool records.
- **Code and file contents:** A comment fails if it describes specific code behavior or file contents that are not supported by the available evidence.
- **Line numbers:** A comment fails if it cites specific line numbers that cannot be verified from the recorded tool results.
- **Search results:** A comment fails if it claims that a search found or did not find something when the recorded search results show otherwise.
- **Error messages:** A comment fails if it reports an error message that does not appear in the original issue or recorded tool evidence.
- **Root causes:** A comment fails if it presents an unverified explanation for a problem as a confirmed root cause.
- **Issue reporter statements:** A comment fails if it presents a reporter's suspicion or assumption as an independently verified fact without additional evidence.
- **Resolution status:** A comment fails if it claims that an issue was fixed, resolved, or deployed without evidence confirming that outcome.
- **External evidence:** A comment fails if it refers to external logs, documentation, maintainer responses, or other information that was not available in the original issue or recorded tool results.

## 6. Human labeling procedure

For each of the 60 original RepoMind outputs, I will read the original issue, recorded tool results, and the agent's comment to determine whether its factual claims are supported by the available evidence.

I will manually assign a **Pass** or **Fail** label to each output and record a specific reason explaining my decision, referring to supporting evidence or identifying unsupported claims.

Only the 60 original outputs will receive human labels. The reformatted and lengthened versions will be used later to test whether the model judge produces consistent results when the presentation changes but the underlying content remains the same.

## 7. Consistency rules

- **Uncertainty:** Clearly stated possibilities, assumptions, or recommendations are acceptable as long as they are not presented as confirmed facts. Definite factual claims must be supported by the available evidence.

- **Mixed supported and unsupported claims:** If a comment contains both supported and unsupported factual claims, it receives a Fail label. Even one unsupported factual claim is enough for the entire comment to fail.

- **Cases not initially covered:** If I encounter a type of unsupported claim that my criterion does not address, I will revise the criterion, review any previously labeled outputs affected by the change, and apply the updated rules consistently across all 60 outputs.