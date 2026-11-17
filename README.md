# RepoMind

The course's running system, built one layer at a time. RepoMind triages issues
for **Ledgerline**, a small reporting and export service: it reads an issue,
searches Ledgerline's private codebase, applies a label, opens a draft pull request
for the file it names, and posts a triage comment where the issue's author can read
it.

That combination is deliberate. RepoMind reads text anyone can write, reaches
code nobody outside the team should see, and writes somewhere public. Lecture 1
calls it the lethal trifecta. You build it this way on purpose, and Lecture 8 is
when you close it.

## Start here

You have two things: this repository, and the assignment handout from your
instructor. The handout says what to build and how it is graded; this file says
how the repository works. For Assignment 7, read the handout's "Getting started"
first.

This repository holds Assignment 6's working state in place of your own code:
Assignment 5's working solution, the planned way with its autonomy policy, the
reviewer, the stop and rollback, and the disclosure line; and the agent way,
Assignment 6's single agent. Assignment 6 merged nothing, so RepoMind is still one
agent, and **RepoMind as it is, is the planned way** (`ways/planned.py`). Assignment
7 gives it an evaluation: a golden set from its own history, a harness that reports
runs, spread and both pass metrics, five trajectory metrics, and a judge you
validate against labels you write by hand. The stubs are in `eval/`. A fresh copy runs, and
`make check-07` awards it nothing. That is expected.

### What you need

- Python 3.10 or later, `git` and `make`. Python's built-in `sqlite3` is all the
  database this assignment needs.
- The model and API key you used before, or any model with tool calling. Never
  commit the key and never share it.

### Set up, and use your model

```bash
make setup                     # creates .venv and installs the three dependencies
source .venv/bin/activate      # in every new terminal
make test                      # the harness's own tests; they spend no tokens
```

From your earlier repository, copy the `provider`, `model`, `base_url` and
`api_key_env` lines of `settings.yaml` into this one, and your model's line in
`pricing.yaml`, if this sheet does not have it. Change nothing else in
`settings.yaml`. Two backends cover almost every vendor:

| Your model | In `settings.yaml` |
|---|---|
| Claude, through Anthropic's API | `provider: anthropic`, `model`; the key in `ANTHROPIC_API_KEY` |
| Anything with an OpenAI-compatible API: OpenAI, Google Gemini, Mistral, DeepSeek, Groq, OpenRouter, a local Ollama or vLLM server, and many more | `provider: openai-compatible`, `model`, `base_url` (none for OpenAI itself), and `api_key_env`, the variable that holds your key (default `OPENAI_API_KEY`) |

Then check it:

```bash
export OPENAI_API_KEY=...      # or the variable your api_key_env names
make ping                      # your key, your model, tool calling, its price line, and your tool definitions
export REVIEWER=scripted:approve-all   # every run in this assignment
```

`make test` and `make ping` must both pass before you write any code.

### Where to start: Assignment 7

| Order | What you write | How you test it | Costs |
|---|---|---|---|
| Part A | `eval/golden/v1/` (the manifest and one task file per task) and `eval/grounded.py` | Your check on the recorded runs' end states, `fixtures/traces7/*.state.json`; `run.py --tasks eval/golden/v1/tasks --backend harness.scripted:ScriptedTriage` loads every task, free | Nothing |
| Part B | `eval/results_07.py`, `eval/stats.py`, `eval/metrics.py`, `tests/test_eval.py` | `make test`; scripted runs through `python -m eval.results_07 ... --scripted`, which writes `results/scripted_<arm>.jsonl`, free | Nothing |
| Part C | `eval/subsets/claim.txt`, then `eval/thresholds/claim.yaml`, and any `ways/arm_<name>.py` | Three sweeps of each arm, then two more | Five sweeps of 8 to 10 tasks, two arms |
| Part D, tasks 1 to 3 | `eval/judge/criterion.md`, your labels in `eval/labels/labels.csv`, the split | Nothing to run | Nothing |
| Part D, tasks 4 to 8 | `eval/judge.py`, `prompts/judge.md` | `harness.scripted:PassEverything`, a coin judge, free | The judge's calls |

`make check-07` works at any point and shows what is still missing; it is the same
checker staff run.

## What is here, and what is yours

| Path | What it is | Yours to edit? |
|---|---|---|
| `ways/planned.py`, `agent/`, `state/`, `policy/`, `bin/`, `tools/`, `prompts/` | **RepoMind as it is**: Assignment 5's working solution, the planned way. Every call goes through the registry and `policy/hook.py` | Only to add Part C's arm, as `ways/arm_<name>.py`, and `prompts/judge.md` |
| `ways/agent.py`, `ways/direct.py` and the earlier ways | The agent way (Assignment 6's single agent) and Assignment 1's direct call, two of Part C's arms | No |
| `fixtures/traces7/` | 60 recorded runs from RepoMind's history on the pool's issues: each trace, whose `tool_call` lines carry the whole result, and its end state; and slide 27's trace with its task | **Never** |
| `fixtures/issues/pool/`, `fixtures/closed_issues.yaml` | Every issue behind the recorded runs, runnable as a golden task, and what the maintainers did with each issue they closed | **Never** |
| `fixtures/judge/outputs/` | The 60 comments to label for Part D, each with its issue, what RepoMind's tools returned, the model that wrote it, and two other versions of the comment | **Never** |
| `eval/grounded.py`, `eval/stats.py`, `eval/metrics.py`, `eval/results_07.py`, `eval/judge.py` | Assignment 7's stubs: the interfaces the checker calls, and what each must do | **Yes** |
| `eval/check_task.py` and the rest of `eval/` | Earlier assignments' checks and reports | No |
| `run.py`, `harness/` | New for Assignment 7: `--subset`, golden tasks (`harness/tasks.py`), the end state with what a run closed, merged and pushed, `TOOL_EXAMPLES`, and judge sessions (`harness/meter.py`) | No |
| `checks/` | `check_07.py`, the Assignment 7 checker, and `FORMATS.md`, which defines every format it reads (section 15 is new) | No |
| `tests/` | The harness's own tests | Add `tests/test_eval.py`; change nothing else |
| `settings.yaml`, `pricing.yaml` | Your model, the ceilings, the dated price sheet | Once, in setup: your model and its price line; never the ceilings |
| `reports/`, `CHANGES.md`, `ARCHITECTURE.md` | Your write-ups; `reports/` starts with the templates for `LAB_07.md` and `LAB_07.json` | **Yes** |
| `runs/`, `tracker/`, `results/`, `logs/` | Made as you run: traces, call records, the ledger, the tracker's database, the logs, judge sessions in `runs/judge/`, and your `results/A.jsonl` and `results/B.jsonl` | Written by the harness and your code; **commit them** |

## Running

```bash
python run.py --tasks eval/golden/v1/tasks --subset eval/subsets/claim.txt --way planned --runs 3       # an arm, three sweeps
python run.py --tasks eval/golden/v1/tasks --subset eval/subsets/claim.txt --way planned --runs 2 \
    --start-sweep 4                                                                                     # sweeps 4 and 5
TOOL_EXAMPLES=off python run.py --tasks eval/golden/v1/tasks --subset eval/subsets/claim.txt \
    --way planned --runs 3                                                                              # claim 3's arm B
python run.py --tasks eval/golden/v1/tasks --way planned --backend harness.scripted:ScriptedTriage     # every task, free
python -m eval.results_07 --arm A --way planned --claim plan                                           # results/A.jsonl
make check-07                                                                                          # the Assignment 7 checker
```

`--tasks` takes your golden set's folder, and `--subset` the file of task IDs Part C
runs. On your model, a run of a task that a way has already finished at that sweep,
with the same switches, is skipped, so the same command again redoes only the runs a
rate limit or the daily quota stopped. To measure a way again after a change,
`python run.py --tasks eval/golden/v1/tasks --way <way> --discard` first. Scripted
runs always run anew, cost nothing, and score nothing.

**Memory.** Every run starts from an empty memory store: `run.py` sets
`REPOMIND_STORE=empty` unless you set it, so no run reads what an earlier one
remembered. `REPOMIND_STORE=shared` gives every run `state/store.db`, as Assignments
4 to 6 did.

**Switches** (`harness/switches.py`) are read from the environment and recorded in
every `run_start` line: Assignment 3's four, and `TOOL_EXAMPLES=off`, which sends
every tool definition without the examples at the end of its description. A
resumed run keeps the switches it started with.

**Killed and resumed runs**, for claim 4: `--die-after-step N` kills a run just
after its plan's step N returns, and `python run.py --resume <run_id>` runs it again
under the same `run_id`, as in Assignment 4. A resumed run is one run in your
results, its calls every `tool_call` line before and after its `resume` line.

**The judge** runs in a session of its own, outside any run, so its calls are
metered and priced like every run's and count against `lab_token_ceiling`:
`harness.meter.judge_session` (below). `harness.scripted:PassEverything` is a judge
that passes everything: a coin, for testing your plumbing and your coin guard for
nothing.

## How your code calls the harness

```python
# A golden task, its end state, and your grounded check (checks/FORMATS.md, sections 15.1 to 15.3)
from harness.tasks import load_task, load_tasks, end_state, load_state, read_subset, secret_values
task = load_task("eval/golden/v1/tasks/g07.yaml")
task.stratum, task.decision, task.expect, task.reference, task.source, task.runs
state = end_state(Tracker(flaky=False, readback_fail=False), run_id, task)   # a live run's
state = load_state("fixtures/traces7/<run_id>.state.json")                   # a recorded run's
from eval.grounded import check
check(task, state)["passed"], check(task, state)["facts"]

# A run's trace and its call record
from harness.trace import read_trace
lines = read_trace(Path("runs") / f"{run_id}.jsonl")          # one dict per line
from eval.results_07 import finished_runs, call_record

# A comment's two lines
from harness.formats import parse_triage_comment, format_triage_comment
label, file = parse_triage_comment(body)

# The judge: a metered session, outside any run (section 15.10)
from harness.meter import judge_session
with judge_session("test-1") as session:           # backend="harness.scripted:PassEverything" for free
    response = session.client.create(system=prompt, messages=[{"role": "user", "content": text}])
    session.trace.model_call(0, response, purpose="judge")
    response.text, session.id, session.model
```

## The rules the harness enforces

- **Success is read from the environment, never from the agent.** The grounded
  check reads the tracker; a spend comes from the `run_end` lines.
- **Every read of the tracker is scoped to one run**, and every write is stamped
  with it.
- **Every run has a hard ceiling**: its task's budget, under the harness's own
  (`session_token_ceiling`); and **every assignment has one** (`lab_token_ceiling`).
  The runner stops starting runs at the second. Ask before you pass `--over-budget`.
- **Every run records what it held constant**: the model, the tools, the budget, the
  evaluator and the task set.
- **Prompts live in `prompts/`**, and a layer held only by a prompt is empty.
- **Disclose AI assistance** in each report: which tool, what it wrote, what you
  checked.

## Submitting an assignment

Your copy of this repository is private. When you create it, add the course
staff's GitHub account as a collaborator (**Settings**, then **Collaborators**)
and post its URL on the assignment in Canvas: that is how staff find and read
your work.

Run `make check-07`, commit everything, including `runs/`, `tracker/` and
`results/`, tag the commit and push both. A tag you have not pushed has not been
submitted.

```bash
make check-07
git add -A
git commit -m "Assignment 7"
git tag lab-07
git push
git push origin lab-07
```
