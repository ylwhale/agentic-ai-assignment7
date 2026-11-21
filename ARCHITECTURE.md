# ARCHITECTURE.md · RepoMind on the seven layers

For each layer: what does this job, and where is it enforced. Cite code as a file
path and line number joined by a colon, inside backticks; a checker opens every
reference (`checks/FORMATS.md`, section 8). A layer held only by a sentence in a
prompt (any file under `prompts/`) is **EMPTY**, and so is a layer nothing does
yet. Status is one of: present, partial (say what is missing), or **EMPTY**. Each
assignment brings this file up to date.

What each layer is for (Lecture 1, slides 42 to 44):

- **Model**: reasoning, choosing tools, generating text.
- **Harness**: runs the loop, builds each prompt, trims old history.
- **Tools**: where the system acts on the world.
- **Memory & State**: what survives a step, a session, a restart.
- **Control & Policy**: what the system may do, and when it must ask.
- **Observability**: a step-by-step record of what it did.
- **Evaluation**: measuring quality, before and after release.

The table below is RepoMind as Assignment 5 leaves it: its working solution.

| Layer | What does this job | Where it is enforced | Status |
|---|---|---|---|
| Model | The configured model, called only through the metered client | `harness/client.py:150` | present |
| Harness | The loop, with three bounds checked in code; a plan validated before it runs, and an executor that runs only the plan's steps; the client drains the user's messages before every call | `agent/loop.py:38`, `ways/planned.py:327`, `ways/planned.py:488`, `ways/planned.py:180` | present |
| Tools | Ten namespaced tools behind one registry: every call checked at the boundary before it runs; every write keyed by the harness, checked before each attempt and read back after a timeout; every attempt in the call record | `tools/__init__.py:170`, `tools/__init__.py:260`, `tools/__init__.py:269`, `tools/__init__.py:286`, `tools/__init__.py:325` | present |
| Memory & State | A checkpoint after each file read and before each write, sync, and a resume from the last one; a store of dated records with their origin, read before the first search and written once at the end of a run | `ways/planned.py:387`, `ways/planned.py:400`, `ways/planned.py:263`, `ways/planned.py:283`, `state/checkpointer.py:55`, `state/store.py:96` | present |
| Control & Policy | The autonomy policy in three columns, enforced by a pre-call hook outside the model: a stop first, prohibited before everything, a user's boundary kept as a rule, the disclosure line, and the reviewer asked for a gated call, with no answer never a yes; an escalation on a named signal that holds; a stop with a live notification; rollback by the remote's compensations | `tools/__init__.py:147`, `policy/hook.py:52`, `policy/hook.py:130`, `policy/hook.py:142`, `policy/hook.py:145`, `policy/hook.py:154`, `policy/hook.py:174`, `policy/boundary.py:33`, `ways/planned.py:209`, `ways/planned.py:460`, `ways/planned.py:546`, `policy/escalation.py:49`, `bin/rollback:24` | partial: the approvals still decay, as Lecture 5's Section B predicts, and nothing measures harm prevented |
| Observability | One trace line per model call and per tool call, and the plan as data before it runs; every refusal in the hook log, every decision in the decisions log, every write in the remote's log | `agent/loop.py:50`, `ways/planned.py:219`, `policy/hook.py:183` | partial: traces and logs, no alerts |
| Evaluation | The grounded check reads the tracker, never the agent | `eval/check_triage.py:7` | partial: offline only |

**Empty layers: 0 of 7**, and three are partial.

## Assignment 7 evaluation extension

The course harness, RepoMind ways, tools, prompts/agent.md, checks and fixtures
remain unchanged. Thirty distinct source-grounded golden tasks live under
`eval/golden/v1/tasks/`; the manifest names every task. The 40 original human
reviews and taxonomy remain unchanged.

| Responsibility | Implementation | Evidence and boundary |
|---|---|---|
| End-state grounding | `eval/grounded.py:14` | Tracker state only; comment/label/PR facts and prohibited actions, never model claims. |
| Trajectory metrics | `eval/metrics.py:39` | Canonical repeated calls, distinct-tool precision/recall, orphan reads, reference-call difference, trace cost/duration. |
| Exact reliability statistics | `eval/stats.py:31` | Combinatorial pass@k and pass^k; sample SD, SE, confidence interval and sweep planning. |
| Result export | `eval/results_07.py:83` | Unique real task/sweep rows; tracker root is explicit; scripted evidence goes to separate files. |
| Experimental stage gates | `eval/experiment_07.py:131` | Committed/pushed subset; actual pilots show only SD/cost; threshold push before fourth sweep; no budget override. |
| Pilot planning | `eval/experiment_07.py:65` | Raw SD preserved; zero variance uses one sweep-mean step, 1/N; no pilot advantage output. |
| Human-input validation | `eval/validation_07.py:25` | Exact IDs and reasons, duplicate rejection; no inferred labels; subset-filtered access. |
| Human label collection | `notes/human_judge_cli.py:35` | Explicit user input and confirmation, lock, backup, atomic replacement, no overwrite. |
| Frozen metered judge | `eval/judge.py:198` | Examples-only prompt labels; independent criterion; frozen config for held-out calls; resumable session-backed verdicts. |
| Judge freeze | `eval/judge.py:173` | Hash checks of code/prompt, criterion/receipt, split/labels, model settings and input outputs. |
| Failed-run evidence | `eval/failure_review_07.py:64` | Full actual trace/end-state packets; no inferred first-failure judgment. |
| Computed report | `eval/report_07.py:135` | Exact arm/per-stratum calculations from complete matrices; null/pending when evidence is absent. |
| Report rendering | `eval/report_07.py:247` | Part A retained; no invented experiments or human criterion/labels. |
| Plan-encoding diagnosis | `eval/diagnose_plan_07.py:18` | Read-only saved-plan/decoder proof; zero API/tool calls and no measured-run changes. |

The label-independent subset/split commit `a96a722` was pushed before the new
judge implementation. `eval/experiment_plan.yaml` fixes the design before paid
pilots. The actual `eval/thresholds/claim.yaml` is created only after three real
sweeps and committed/pushed before sweep four. `eval/judge/frozen.json` is created
only after human inputs and development, then committed before held-out testing.

All paid calls use `harness.client.ModelClient`; Part D additionally uses
`harness.meter.judge_session` and its real ledger/session traces. The correction
refuses |TPR+TNR−1|≤0.1 and uses at least 2,000 bootstrap samples. The configured
course ceilings remain 1.5 million tokens/session and 20 million/assignment.

See `reports/LAB_07.md` for the completed evaluation, experimental
results, judge validation, provenance, and limitations. The written
report remains subject to separate staff review.

Part C has now completed all 80 real runs. Threshold `756817f` was pushed before
sweep four. The failed repeats claim, actual costs and 67 disclosed Codex-assisted
first-failure records are in `reports/PART_C_ANALYSIS_07.md`,
`reports/PART_C_PROVENANCE_07.json` and `eval/failures_ai.csv`. The report builder
validates call ordinals/steps/hashes and computes grids from those records; it does
not present them as student-authored human labels. The Part D human criterion
and labels remain separate and are not changed by this pipeline.
