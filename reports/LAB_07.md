# Assignment 7 · The evaluation harness, and a judge you have checked

Model: <vendor and model>, the same for every run and for the judge.

## Part A · A golden set from traces

**The kinds of failure** you found by reading the recorded runs (slide 12), until no new kind appeared.

| Kind of failure | Runs | One run that shows it, and its first wrong step |
|---|---|---|
| | | |

- Runs read, and when no new kind appeared:

**How you chose the tasks** (slide 12's table): every kind of task, the failures, each path, no copies.

| Stratum | Tasks | Decisions (act, refuse, stop) |
|---|---|---|
| routine | | |
| unusual | | |
| adversarial | | |
| should-not-act | | |

- The thinnest stratum, and the smallest fall it can show:

## Part B · The harness

- How a run becomes a line in `results/`, and what reads the end state:
- One table from your Part C results, as the harness reports it (runs, spread, pass@k and pass^k with *k*):

## Part C · Settle one claim

- The claim, its two arms, the measure and the sign of the gain:
- The first three sweeps: each arm's *s*, and the cost of one sweep:
- *δ*, the sweeps it needs, and the price (slide 55):
- The bar and the group rule, as committed, and the commit:

**The results**, from `results/`.

| Arm | Runs | Measure: mean (SD) | Score: mean (SD) | pass@k | pass^k | Facts right | Cost per run |
|---|---|---|---|---|---|---|---|
| A | | | | | | | |
| B | | | | | | | |

| Stratum | Gain | 95% interval |
|---|---|---|
| All tasks | | |
| routine | | |
| unusual | | |
| adversarial | | |
| should-not-act | | |

- The verdict, by your bar, and why:
- Cost beside the score (slide 54):
- Each part of your prediction that missed, and the run that shows why:

**Where the failed runs first went wrong** (slide 29), last good step down the side, first wrong step across.

```
```

- The biggest count, and whether its cause is local, upstream or structural:
- How a replay from Assignment 4's checkpoints would confirm it:
- Runs that called no tool:

## Part D · Validate a judge

- The criterion's lines, and what labelling added to them:
- The split, and when it was committed:
- The judge: its model and version, and its TPR and TNR on the test set:
- Its pass rate on the recorded runs, corrected, with its interval:
- Its flip rate, and whether a majority of three was kept:
- What moved on the reformatted and lengthened versions:
- Its rates on each system:
- What validating the judge still needs:

## AI assistance

Which tool, what it wrote, and what you checked. No assistant writes or suggests a label.
