"""Rebuild trace-backed sections of Assignment 7's JSON report.

    python -m eval.report_07                 # golden counts and any finished data
    python -m eval.report_07 --pilot --delta 0.5

--pilot intentionally prints only the first three sweeps' *spread* and cost,
not their observed mean gains. This supports the handout's precommitment rule.
The user chooses delta, bar and group_floor; this program never invents them.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from harness import ROOT
from harness.formats import STRATA
from harness.tasks import load_tasks, read_subset
from eval.judge import CoinJudge, bootstrap, correct, rates
from eval.stats import interval, over_tasks, spread, sweeps_needed, standard_error
from eval import validation_07 as validation
from notes.review_support import atomic_write

REPORT = ROOT / 'reports' / 'LAB_07.json'


def mean(values):
    return sum(values)/len(values) if values else 0.0


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sweep_values(rows, *, key='measure', tasks=None, require=None):
    cells=[(r['task'],int(r['sweep'])) for r in rows if tasks is None or r['task'] in tasks]
    if len(cells)!=len(set(cells)):
        raise ValueError('Duplicate task/sweep cells cannot be averaged')
    by = defaultdict(list)
    for row in rows:
        if tasks is None or row['task'] in tasks:
            by[int(row['sweep'])].append(row)
    if require is not None:
        by = {k:rs for k,rs in by.items() if len(rs)==require}
    return [mean([float(x[key]) if key!='score' else 100.0*bool(x['passed']) for x in by[s]])
            for s in sorted(by)]


def arm_numbers(rows,k=3):
    if not rows:
        return None
    per = defaultdict(list)
    for r in rows:
        per[r['task']].append(r)
    counts = {tid:(len(rs),sum(bool(r['passed']) for r in rs)) for tid,rs in per.items()}
    pass_k,hat_k = over_tasks(counts,k) if all(n>=k for n,_ in counts.values()) else (None,None)
    measures = sweep_values(rows)
    scores = sweep_values(rows,key='score')
    present = sum(r['facts']['present'] for r in rows)
    total = sum(r['facts']['total'] for r in rows)
    costs={s:sum(r['cost_usd'] for r in rows if r['sweep']==s) for s in {r['sweep'] for r in rows}}
    return {'runs':len(rows), 'measure':{'mean':mean(measures),'sd':spread(measures),'se':standard_error(measures) if len(measures)>1 else None},
            'score':{'mean':mean(scores),'sd':spread(scores),'se':standard_error(scores) if len(scores)>1 else None},
            'cost_per_sweep_usd':mean(list(costs.values())),
            'pass_at_k':pass_k,'pass_hat_k':hat_k,
            'facts_share':present/total if total else None,
            'cost_per_run_usd':mean([r['cost_usd'] for r in rows]),
            'no_tools':sum(bool(r['metrics'].get('no_tools')) for r in rows)}


def update_judge(info):
    split_path=ROOT/'eval/labels/split.yaml'
    if not split_path.exists():
        return
    split=yaml.safe_load(split_path.read_text())
    info['split']={k:len(split[k]) for k in ('examples','tuning','test')}
    test=split['test']
    run_files=[ROOT/f'eval/judge/verdicts/test_{idx}.jsonl' for idx in (1,2,3)]
    recorded=ROOT/'eval/judge/verdicts/recorded.jsonl'
    versions=ROOT/'eval/judge/verdicts/versions.jsonl'
    if not all(p.exists() for p in [*run_files,recorded,versions]):
        return
    from eval.judge import check_frozen
    check_frozen(ROOT)
    # Held-out labels enter evaluation only after the judge has been frozen.
    labels={i:r['label'] for i,r in validation.labels(ROOT).items()}
    three=[]
    for path in run_files:
        rows=read_jsonl(path)
        if len(rows)!=len(test) or {r['id'] for r in rows}!=set(test):
            raise ValueError('Each test verdict file must contain exactly the held-out IDs once')
        three.append({r['id']:r for r in rows})
    first={i:three[0][i]['answer'] for i in test}
    on_test={i:labels[i] for i in test}
    tpr,tnr=rates(first,on_test)
    saved=read_jsonl(recorded)
    if not saved:
        return
    p=mean([1.0 if r.get('answer')=='pass' else 0.0 for r in saved])
    coin=abs(tpr+tnr-1)<=0.1
    try:
        corrected=correct(p,tpr,tnr)
        ci=list(bootstrap(first,on_test,p))
    except CoinJudge:
        corrected,ci=None,None
    info.update({'model':three[0][test[0]].get('model'),'tpr':tpr,'tnr':tnr,
                 'p':p,'corrected':corrected,'interval':ci,'coin':coin})
    flips=[i for i in test if len({r[i]['answer'] for r in three})>1]
    info['flip_rate']=len(flips)/len(test)
    (ROOT/'eval/judge/for_a_person.txt').write_text(''.join(x+'\n' for x in flips))
    majority={i:'pass' if sum(three[j][i]['answer']=='pass' for j in range(3))>=2 else 'fail' for i in test}
    mtpr,mtnr=rates(majority,on_test)
    base_good=sum(first[i]==labels[i] for i in test)
    maj_good=sum(majority[i]==labels[i] for i in test)
    info['accuracy']=base_good/len(test)
    info['majority']={'tpr':mtpr,'tnr':mtnr,'kept':maj_good>base_good,'accuracy':maj_good/len(test)}
    versions_json=read_jsonl(versions)
    expected={(i,v) for i in test for v in ('list','long')}
    if len(versions_json)!=len(expected) or {(r['id'],r.get('version')) for r in versions_json}!=expected:
        raise ValueError('Version verdicts must contain each test ID/list-long pair once')
    moved={r['id'] for r in versions_json if r.get('id') in first and r.get('answer')!=first[r['id']]}
    info['moved_share']=len(moved)/len(test)
    output_system={p.stem:json.loads(p.read_text()).get('system') for p in
                   (ROOT/'fixtures/judge/outputs').glob('*.json')}
    info['by_system']={s:dict(zip(('tpr','tnr'),rates(first,{i:labels[i] for i in test if output_system[i]==s})))
                       for s in sorted(set(output_system.values()))}


def build():
    existing=json.loads(REPORT.read_text())
    tasks=load_tasks('eval/golden/v1/tasks')
    strata=Counter(task.stratum for task in tasks)
    decisions=Counter(task.decision for task in tasks)
    thin_count=min(strata.values())
    thin=next(s for s in STRATA if strata[s]==thin_count)
    existing['golden']={'version':'v1','tasks':len(tasks),'strata':{s:strata[s] for s in STRATA},
                        'decisions':{d:decisions[d] for d in ('act','refuse','stop')},'thinnest':thin}
    update_judge(existing['judge'])
    threshold_path=ROOT/'eval/thresholds/claim.yaml'
    if not threshold_path.exists():
        atomic_write(REPORT,json.dumps(existing,indent=2,ensure_ascii=False)+'\n')
        render_markdown(existing)
        return 'Golden counts updated. Claim remains unset: run three real-model pilot sweeps first.'
    validation.committed(ROOT,'eval/thresholds/claim.yaml')
    spec=yaml.safe_load(threshold_path.read_text())
    subset=set(read_subset('eval/subsets/claim.txt'))
    k=int(spec.get('k',3))
    rows={arm:[r for r in read_jsonl(ROOT/f'results/{arm}.jsonl') if r.get('task') in subset]
          for arm in ('A','B')}
    for arm in ('A','B'):
        values=arm_numbers(rows[arm],k)
        if values is None:
            continue
        stratum={}
        for s in STRATA:
            ids={t.id for t in tasks if t.stratum==s}
            these=[r for r in rows[arm] if r['task'] in ids]
            n=arm_numbers(these,k)
            if n:
                stratum[s]={'runs':n['runs'],'measure':n['measure']['mean'],
                            'score':n['score']['mean'],'pass_at_k':n['pass_at_k'],'pass_hat_k':n['pass_hat_k'],
                            'measure_sd':n['measure']['sd'],'score_sd':n['score']['sd']}
        values.update({'way':spec[f'arm_{arm.lower()}']['way'],
                       'switches':spec[f'arm_{arm.lower()}'].get('switches') or {},
                       'by_stratum':stratum})
        existing['arms'][arm]=values
    existing['claim'].update({key:spec[key] for key in ('claim','measure','gain','sweeps','s_a','s_b','delta','n_needed','price_usd','k') if key in spec})
    complete=all(len(rows[a])==len(subset)*int(spec.get('sweeps',5)) for a in ('A','B'))
    if not complete:
        atomic_write(REPORT,json.dumps(existing,indent=2,ensure_ascii=False)+'\n')
        render_markdown(existing)
        return 'Claim summary updated, but the real 5-sweep arm data is incomplete.'
    from eval.experiment_07 import matrix
    for arm in ('A','B'):matrix(rows[arm],subset,range(1,int(spec['sweeps'])+1))
    vals={a:sweep_values(rows[a]) for a in ('A','B')}
    forward=str(spec['gain']).replace(' ','')=='B-A'
    def signed(a,b): return interval(b,a) if forward else interval(a,b)
    diff,lo,hi=signed(vals['A'],vals['B'])
    by_stratum={}
    for s in STRATA:
        ids={t.id for t in tasks if t.stratum==s}
        ar=sweep_values(rows['A'],tasks=ids)
        br=sweep_values(rows['B'],tasks=ids)
        v=signed(ar,br)
        by_stratum[s]={'difference':v[0],'interval':[v[1],v[2]]}
    bar,floor=float(spec['bar']),float(spec['group_floor'])
    verdict='holds' if lo>bar and all(v['difference']>=floor for v in by_stratum.values()) else 'fails' if hi<bar else 'cannot_settle'
    existing['claim'].update({'difference':diff,'interval':[lo,hi],'by_stratum':by_stratum,'verdict':verdict})
    # Read explicit trace-inspection annotations. AI-assisted records retain
    # authorship and are never represented as the student's human reviews.
    manual=ROOT/'eval/failures_manual.csv'
    if not manual.exists():
        manual=ROOT/'eval/failures_ai.csv'
    if manual.exists():
        with manual.open(newline='') as fh:
            firsts=[r for r in csv.DictReader(fh) if r.get('run_id')]
        from eval.failure_review_07 import validate_annotations
        validate_annotations(firsts,[dict(r,arm=a) for a in ('A','B') for r in rows[a] if not r['passed']],ROOT)
        existing['failures']=firsts
        grid={}
        for r in firsts:
            arm,good,wrong=r['arm'],r['last_good'],r['first_wrong']
            grid.setdefault(arm,{}).setdefault(good,{}).setdefault(wrong,0)
            grid[arm][good][wrong]+=1
        existing['grid']=grid
        existing['failure_analysis']={'source':str(manual.relative_to(ROOT)),
            'reviewers':sorted({r.get('reviewer','unspecified') for r in firsts}),
            'cause_counts':dict(Counter(r.get('cause','unspecified') for r in firsts)),
            'failure_type_counts':dict(Counter(r.get('failure_type','unspecified') for r in firsts)),
            'human_historical_reviews_modified':False}
    atomic_write(REPORT,json.dumps(existing,indent=2,ensure_ascii=False)+'\n')
    render_markdown(existing)
    return f'Calculated real-sweep comparison: {diff:.4f} [{lo:.4f}, {hi:.4f}]; verdict={verdict}. First-failure annotations require explicit trace inspection and disclosed authorship.'


def pilot(delta):
    subset=set(read_subset('eval/subsets/claim.txt'))
    data={a:[r for r in read_jsonl(ROOT/f'results/{a}.jsonl')
              if r.get('task') in subset and int(r.get('sweep') or 0) in (1,2,3)] for a in ('A','B')}
    from eval.experiment_07 import pilot_numbers
    numbers=pilot_numbers(data,subset,delta)
    print(json.dumps(numbers,indent=2))
    print('Spread and cost only. Commit and push claim.yaml before sweep 4; zero SD uses one step (1/N) of a sweep mean for planning.')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot',action='store_true')
    p.add_argument('--delta',type=float,default=None)
    args=p.parse_args(argv)
    if args.pilot:
        if args.delta is None or args.delta<=0:
            p.error('--pilot needs a positive user-chosen --delta')
        pilot(args.delta)
    else:
        print(build())
    return 0



def render_markdown(report):
    """Refresh computed report sections; Part A and the human source files stay intact."""
    path=ROOT/'reports/LAB_07.md'
    text=path.read_text()
    prefix=text[:text.index('## Part B')]
    lines=['## Part B · The harness','',
        '`eval/results_07.py` reads finished real traces, matches golden task IDs and the frozen subset, and queries the run-scoped tracker end state. It writes one row per unique task/sweep cell with the grounded pass and fact counts, trace-derived tokens/cost/duration, and trajectory metrics. Scripted backends are exported separately and excluded from measured results. Quota/rate-limited attempts stay recorded but do not count as finished cells.','',
        'Each sweep contributes one mean primary measure and one score (100 × passes/tasks). Spread is sample SD across sweep values, with n−1 in the denominator; SE is SD/√n. The signed gain uses the two arms’ sweep means and a 95% normal interval with margin 1.96√(s_A²/n_A+s_B²/n_B). Per-stratum calculations use the same sweep grouping. With few sweeps, normal intervals and estimated spreads are imprecise.','',
        'Reliability uses the exact finite-sample estimators, averaged equally over tasks: pass@k = 1−C(n−c,k)/C(n,k), and pass^k = C(c,k)/C(n,k). pass^k is not pass@1 raised to k.','',
        'Trajectory metrics are actual calls minus reference calls; precision/recall over distinct tool names; repeated (tool, canonical arguments) pairs after the first; orphan reads whose identifiers never occur in later arguments or the final comment; and trace-reported cost/latency. A zero-call run has undefined precision, an explicit no-tools flag, and the appropriate negative reference-call difference.','',
        '## Part C · Settle one claim','',
        'Design: “The plan reduced repeated steps.” Arm A is `planned`, arm B is `agent`; the measure is repeated tool calls and the gain is B−A, so positive values favor A. The unchanged eight-task subset is g01/g03, g10/g13, g20/g21, and g24/g25, two per stratum. The subset and judge split were committed and pushed in `a96a722` before any Part C run.','',
        'The pre-pilot design in `eval/experiment_plan.yaml` predicts A by 0.25 repeats per task, with the largest gap in unusual tasks. Delta 0.25 equals two avoided repeated calls in an eight-task sweep. The bar is 0 and the stratum floor is 0. These are design choices, not observed effects.','']
    claim=report['claim'];arms=report['arms']
    if claim.get('difference') is None:
        lines.extend(['**Experiment incomplete.** No final advantage or claim verdict is reported. The pilot-derived threshold remains absent until both arms have three complete real sweeps. Only pilot SD and cost may be inspected before the threshold commit and push.',''])
    else:
        lines.extend([f"Final gain: {claim['difference']:.4f}; 95% interval {claim['interval']}; verdict **{claim['verdict']}**.",''])
    lines.extend(['| Arm | Real runs | Measure mean (SD) | Score mean (SD) | pass@k | pass^k | Facts share | USD/run |',
                  '|---|---:|---|---|---|---|---|---|'])
    def value(x):return 'pending' if x is None else f'{x:.6g}' if isinstance(x,(int,float)) else str(x)
    for arm in ('A','B'):
        a=arms[arm]
        lines.append(f"| {arm} | {a['runs']} | {value(a['measure']['mean'])} ({value(a['measure']['sd'])}) | {value(a['score']['mean'])} ({value(a['score']['sd'])}) | {value(a['pass_at_k'])} | {value(a['pass_hat_k'])} | {value(a['facts_share'])} | {value(a['cost_per_run_usd'])} |")
    lines.extend(['',f"Reliability k: {value(claim.get('k'))}. Final design calls for five sweeps per arm (80 finished runs); incomplete attempts and their costs remain preserved.",''])
    pilot_path=ROOT/'eval/pilot_spread.json'
    if pilot_path.exists():
        pilot=json.loads(pilot_path.read_text())
        lines.extend([f"Pilot SDs: A={pilot['s_a']}, B={pilot['s_b']}; effective planning SDs {pilot['effective_s_a']}, {pilot['effective_s_b']}. n_needed={pilot['n_needed']}; estimated cost for that n=${pilot['price_usd']:.6f}; mean pilot cost/sweep=${pilot['pilot_cost_per_sweep_usd']:.6f}.",''])
    lines.extend(['Planning uses n≥(s_A²+s_B²)(2.80/δ)², rounded up. Zero observed SD is replaced only for planning by one step of the sweep mean (1/8 repeats), with raw SD also retained. Three pilot sweeps provide a weak spread estimate. If five sweeps do not clear the precommitted bar and stratum rule, the result remains cannot_settle; no extra budget or favorable result is assumed.','',
                  '| Stratum | Gain | 95% interval |','|---|---|---|'])
    for st in STRATA:
        part=claim.get('by_stratum',{}).get(st,{})
        lines.append(f"| {st} | {value(part.get('difference'))} | {value(part.get('interval'))} |")
    lines.extend(['','First-failure grids (last correct tool → first wrong tool, or start/stop):','',
                  '```json',json.dumps(report.get('grid',{}),indent=2),'```','',
                  f"No-tool runs: A={arms['A'].get('no_tools',0)}, B={arms['B'].get('no_tools',0)}. These counts are final only when the experiment matrix is complete.",'',
                  (ROOT/'reports/PART_C_ANALYSIS_07.md').read_text() if (ROOT/'reports/PART_C_ANALYSIS_07.md').exists() else 'First-failure trace inspection and causal/checkpoint analysis remain pending. No first failure is inferred solely from a missing final fact.','',
                  '## Part D · Validate a judge',''])
    j=report['judge']
    try:count=len(validation.labels(ROOT,complete=False))
    except validation.InputError:count=0
    lines.extend([f"Human labels currently complete: {count}/60. The criterion is `eval/judge/criterion.md`; its authorship and revisions must be confirmed by the student, never supplied by the assistant. The original inherited criterion is not treated as verified human authorship.",'',
        f"The label-independent split has {j['split']['examples']} examples, {j['split']['tuning']} tuning items, and {j['split']['test']} held-out items. Split commit `a96a722` precedes the new judge implementation. Example labels alone enter the prompt; tuning has separate verdict files; held-out labels enter metric calculation only after an immutable judge configuration is frozen. No human label or reason is generated or changed by the judge.",''])
    if j.get('model') is None:
        lines.extend(['**Judge validation incomplete.** No real judge rates, corrected rate, reliability, or perturbation result is claimed. The absent verdicts are not substituted with scripted calls.',''])
    else:
        lines.extend([f"Frozen judge model: {j['model']}; TPR={j['tpr']}, TNR={j['tnr']}, accuracy={j.get('accuracy')}. Recorded-run pass rate={j['p']}; corrected={j['corrected']}; bootstrap 95% interval={j['interval']}; coin-like={j['coin']}.",'',
                      f"Three-pass flip rate={j['flip_rate']}; majority result={j['majority']}. IDs requiring a person are in `eval/judge/for_a_person.txt`. Share moved by either list/long perturbation={j['moved_share']}.",'',
                      'Per source system:','', '```json',json.dumps(j['by_system'],indent=2),'```',''])
    lines.extend(['Correction is clipped (p+TNR−1)/(TPR+TNR−1), refused when |TPR+TNR−1|≤0.1. At least 2,000 seeded bootstrap resamples propagate calibration uncertainty. A small held-out sample, absent classes within a source-system slice, and calibration transfer to historical comments limit interpretation. Bootstrap intervals condition on the observed recorded pass rate; they do not account for task-population drift.','',
        '## AI assistance','',
        'Codex audited and extended the Python evaluation/review tools, isolated synthetic tests from live human records, added three independently sourced golden tasks, and summarized the student’s existing human taxonomy. Codex executed the real Part C experiment and inspected its failed traces; those annotations disclose Codex authorship in eval/failures_ai.csv and are not student-authored human reviews. Codex did not author or suggest Part D human labels/reasons, did not write the student’s criterion, and did not change the 40 human observations or taxonomy. Synthetic test labels/runs remain confined to temporary roots. The checkpoint diagnostic is read-only, not a new measured arm or evidence of downstream task success. Human verification of the criterion, all labels, and final report interpretation remains required.',''])
    atomic_write(path,prefix+'\n'.join(lines))

if __name__=='__main__':
    raise SystemExit(main())
