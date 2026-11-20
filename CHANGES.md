# CHANGES.md

Three lines per assignment: what it added, what it removed, what it constrained.
Removals are logged like additions.

## Assignment 1
- **Added:** a bounded tool loop; four ways to triage an issue (a direct call, a workflow, an agent, and a hybrid of the two); a grounded success check that reads the tracker; a results script
- **Removed:** nothing
- **Constrained:** every agent run to three bounds checked in code (steps, tokens, wall clock); success to what the tracker holds for the run's ID

## Assignment 2
- **Added:** a plan written as data before the issue is read; a validator with four checks; an executor that runs only the plan's steps; one checkpoint that may revise the plan; a second pass before the comment; detectors and a diff over traces; a progress file and a compaction
- **Removed:** the model's choice of the next tool, in the planned way
- **Constrained:** every tool call to a step of a validated plan; revisions to steps not yet done; the comment to drafts that pass the second pass

## Assignment 3
- **Added:** five rewritten tool definitions with examples, among them open_pr; a boundary check before every call; errors that name the fix; harness-derived idempotency keys, a check before every write attempt and a read-back after a timeout; the call record; a fail-closed hook
- **Removed:** free-text tool descriptions and free-form filters; protocol detail in anything the model sees
- **Constrained:** every write to be safe to retry, and to a person when its outcome cannot be read back; the comment to the last write, after the PR

## Assignment 4
- **Added:** a checkpoint after each file read and before each write, saved sync; a resume from the last checkpoint that replays a write with its saved arguments and key; a memory store of dated records with their source and origin, read before the first search; a write policy with one record per issue, superseded when it disagrees
- **Removed:** the conversation from every checkpoint; the issue's own text from what memory shows a prompt
- **Constrained:** a crashed run to resume, never restart; what is remembered to what a person stated or RepoMind derived, each with its source

## Assignment 5
- **Added:** an autonomy policy in three columns, enforced by the pre-call hook; boundaries a user states, kept as rules; a reviewer screen of facts and a dry run; a decisions log; an escalation on four named signals, with a packet, a hold and a daily cap; a live-run notification and a stop; rollback by the remote's compensations; a disclosure line on every comment
- **Removed:** autonomous merge; pushes to a protected branch
- **Constrained:** push_commit and post_comment by circumstance; every gated call to a person's answer, and no answer to a hold

## Assignment 6
- **Added:** nothing
- **Removed:** nothing
- **Constrained:** multi-agent decomposition, measured against one agent at the same budget and not merged; RepoMind stays one agent

## Assignment 7 — evaluation and reproducible experiment workflow

- **Added:** 30 independently sourced golden tasks, exact reliability/spread/interval calculations, trace/tracker result export, a stage-gated two-arm plan experiment, and a frozen, metered, resumable judge. Completed Part A report from the student's 40 unchanged reviews and nine human categories. Added synthetic tests for experiment matrices, human-label boundaries, prompt isolation and resume provenance.
- **Removed:** test dependence on the student's live review document; review tests now create their own temporary synthetic ledger. Removed the incorrect 1.0 zero-variance sweep fallback in favor of the actual 1/N sweep-mean step.
- **Constrained:** no pilot advantage inspection before threshold commitment; no fourth sweep before threshold push; no held-out labels in prompt development; explicit human criterion/label confirmation; no overwrite of human records or expensive verdicts; no fabricated results or budget overrides. Required subset/split commit `a96a722` was pushed first. Actual experiments, human Part D inputs, judge validation and final tag remain explicit dependencies until their evidence exists.
