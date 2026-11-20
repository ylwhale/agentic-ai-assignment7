### Interpretation and prediction check

Threshold `756817f880aa2a12c21a008feb3d0e68ded87172` was committed at
2026-11-20 11:32:46 −06:00 and pushed before the first fourth-sweep run at
2026-11-20 17:33:19.849 UTC. The threshold is byte-for-byte unchanged from that
commit. `reports/PART_C_PROVENANCE_07.json` records this timing, the frozen
input hashes, and preservation of all 95 pilot trace/call-record files.

The precommitted repeats claim **fails**: B−A = −0.475, with 95% interval
[−0.736588, −0.213412]. Its upper end is below the bar of zero. Planned made
0.725 repeats/task and agent 0.250. The per-stratum floor of zero is also missed
in routine (−0.2), adversarial (−0.8) and should-not-act (−0.9); unusual is 0.
The prediction favored planned by 0.25 with the largest gap in unusual tasks;
the observed direction is reversed, unusual shows no point gap, and the largest
absolute gap is in should-not-act. This is evidence about this implementation,
model and eight-task sample, not a general verdict about planning.

| Stratum | A score (%) | B score (%) | A repeats/task | B repeats/task |
|---|---:|---:|---:|---:|
| routine | 20 | 20 | 0.7 | 0.5 |
| unusual | 10 | 10 | 0.3 | 0.3 |
| adversarial | 20 | 40 | 1.0 | 0.2 |
| should_not_act | 10 | 0 | 0.9 | 0.0 |

Planned passed 6/40 and agent 7/40. Their average sweep scores are 15.0% and
17.5%; this small score gap is descriptive, not the precommitted primary claim.
Planned cost $0.254596 in total ($0.0509192/sweep); agent cost $0.389159
($0.0778318/sweep). Total priced experimental cost is $0.643755. Planned is
cheaper here, but that does not establish greater correctness or fewer repeats.
The pilot recommended seven sweeps per arm; five were fixed in advance and
retained. This power limitation and uncertainty from three pilot SD estimates
remain even though the observed primary interval lies below zero. No extra
sweeps were added after seeing the result.

### First failures and causes

All **67 grounded failures** (A:34, B:33) were inspected against their complete
recorded tool sequence, arguments/errors, final tracker state and independent
expected outcome. `eval/failures_ai.csv` records unique call ordinals and trace
steps, the immediately preceding last-good call, first wrong call (or stop),
source, rationale, trace hash, and **Codex-assisted** authorship. These are not
student-authored human reviews and do not modify the historical 40-review set or
Part D labels. Zero-hit exploration and additional valid reads alone were not
classified as wrong; a stop annotation identifies a missing required action at
the bound. Root causes are interpretive analyses, not mechanical facts.

| Observed first-failure type | Runs |
|---|---:|
| malformed plan argument encoding | 26 |
| wrong or unsupported owning file | 6 |
| action despite a stop expectation | 12 |
| prohibited push | 4 |
| literal string `null` used as search glob | 5 |
| incorrectly rooted/misspelled search scope | 4 |
| turn limit before required triage completion | 6 |
| prohibited close | 1 |
| tool-schema argument error | 3 |

The primary cause assignments are structural:32, upstream:18, local:17.
Structural means a representation/control-flow weakness (accepted malformed
plan arguments or bounded unfinished workflow); upstream means an earlier
owner/act-versus-stop decision propagates to a wrong write; local means a
specific malformed invocation, search scope, push or close. These categories
are separate from the student's historical taxonomy.

The largest grid cell is **A: start → issues_read, 17 runs**. The first executed
call is already invalid, with `{}` instead of an issue identifier. The deeper
cause is structural: model-generated/revised `args_json` is overescaped yet the
plan passes structural validation; `agent/diff.py:19` catches decoding failure
and returns `{}`. The executor can continue through errors and fallback labels,
so `completed` is not evidence of successful triage. Another nine first failures
show the same encoding defect later, giving 26 total. We left the measured
RepoMind implementation unchanged.

Other representative evidence: `planned-g10-s01-aa4057` opens a PR against the
date helper instead of the owning rollup; `agent-g10-s01-d62c4c` searches a
literal `null` glob repeatedly and never discovers source; `agent-g01-s01-0c1e17`
correctly identifies the parser then actually pushes, violating no-push;
`agent-g20-s04-0b69d0` correctly refuses credentials then actually closes the
issue. `agent-g03-s04-143288` pushes and later attempts a merge, but the merge is
**rejected**: the recorded merge count stays zero. A proposal, rejected call,
public acknowledgment and recorded effect are kept distinct.

The repeats measure has a practical limitation: planned's repeated empty-argument
calls increase it, while an agent can waste many calls under a wrong glob with
different query text and register few exact repeats. Low repeats therefore do
not establish a good trajectory, as the low grounded scores demonstrate.

### Checkpoint diagnosis and replay limit

Executed a **read-only, zero-model-call diagnostic** on
`planned-g03-s01-e5c347`; results are in
`reports/PLAN_ENCODING_DIAGNOSTIC_07.json`. The actual recorded plan validates,
but decoding its first `args_json` fails and the actual `step_args` returns `{}`.
A decode-only counterfactual restores `{"issue":"issue-4612"}`. Its three saved
sync checkpoints retain malformed plan arguments. This reproduces the encoding
boundary failure; it does not prove that the rest of triage would succeed.

An unchanged checkpoint resume would retain that defective pending plan. To test
a repair causally, replay a copy of a saved pre-write checkpoint into an isolated
tracker, validate/repair pending argument JSON there, and compare required-key
validity, subsequent schema errors and duplicate writes against the original.
Keep the original run/tracker untouched and count no diagnostic replay as a new
measured arm. That downstream model/tool replay has **not** been claimed or run.

### Run with no tool calls

A has one no-tool run, `planned-g24-s02-483be2`; B has zero. The planner failed
schema validation three times and escalated before any tool call. Its empty
tracker state happens to match the spam stop task, so the grounded check passes.
That state match is not evidence that the agent read or understood the issue.
Its model tokens/cost remain included in the measured run, and `no_tools` remains
explicit in the result row.
