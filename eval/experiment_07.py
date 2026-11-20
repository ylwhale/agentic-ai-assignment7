"""Stage-gated real experiment driver. No simulated results or budget overrides.

python -m eval.experiment_07 preflight
python -m eval.experiment_07 pilot       # sweeps 1–3, only SD/cost displayed
python -m eval.experiment_07 threshold   # writes a pilot-derived threshold; commit/push it
python -m eval.experiment_07 finish      # verifies threshold push before sweeps 4–5
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import yaml
from harness import ROOT
from harness.backends import REAL_BACKENDS
from harness.runner import Ledger, is_trace, run_header
from harness.settings import load_settings
from harness.tasks import load_tasks, read_subset
from eval import validation_07 as validation
from eval.results_07 import build_rows
from eval.stats import spread,sweeps_needed
from notes.review_support import atomic_write,json_write


def load_local_environment(root=ROOT):
    """Read only the explicitly supported local .env; never execute its contents."""
    path=root/'.env'
    if path.exists():
        for line in path.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith('#'):continue
            if line.startswith('export '):line=line[7:]
            name,sep,value=line.partition('=')
            if sep and name.strip().isidentifier():
                tokens=shlex.split(value,comments=True)
                if len(tokens)==1:os.environ.setdefault(name.strip(),tokens[0])
    os.environ['REVIEWER']='scripted:approve-all'
    os.environ['REPOMIND_STORE']='empty'


def remote_contains(root,commit):
    branch=validation.git(root,'branch','--show-current')
    result=subprocess.run(['git','ls-remote','origin',f'refs/heads/{branch}'],cwd=root,capture_output=True,text=True)
    if result.returncode or not result.stdout.strip():
        raise validation.InputError('Cannot verify the prerequisite push to origin; fix Git authentication/connectivity first')
    head=result.stdout.split()[0]
    validation.git(root,'merge-base','--is-ancestor',commit,head)
    return head


def matrix(rows,ids,sweeps):
    expected={(task,sweep) for task in ids for sweep in sweeps}
    seen=[(r['task'],int(r['sweep'])) for r in rows]
    if len(seen)!=len(set(seen)):
        raise validation.InputError('Duplicate task/sweep cells; no aggregate computed')
    missing=expected-set(seen);extra=set(seen)-expected
    if missing or extra:
        raise validation.InputError(f'Incomplete experiment matrix: {len(missing)} missing, {len(extra)} extra cells')


def pilot_numbers(rows,ids,delta):
    """Return spread and cost only; never reveal scores or the signed mean gap."""
    effective={};raw={};costs=[]
    for arm in ('A','B'):
        matrix(rows[arm],ids,range(1,4))
        values=[sum(r['measure'] for r in rows[arm] if r['sweep']==s)/len(ids) for s in range(1,4)]
        raw[arm]=spread(values)
        effective[arm]=raw[arm] or 1/len(ids)
        costs.extend(sum(r['cost_usd'] for r in rows[arm] if r['sweep']==s) for s in range(1,4))
    n=sweeps_needed(effective['A'],effective['B'],delta)
    cost=sum(costs)/len(costs)
    return {'s_a':raw['A'],'s_b':raw['B'],'effective_s_a':effective['A'],'effective_s_b':effective['B'],
            'delta':delta,'n_needed':n,'pilot_cost_per_sweep_usd':cost,'price_usd':n*2*cost,
            'five_sweep_total_estimate_usd':5*2*cost,'zero_variance_quantum':1/len(ids),
            'limitation':'SD from only three sweeps is imprecise. Zero observed SD uses one task-count step (1/N) of the sweep mean for planning. Five sweeps may be underpowered.'}


def design(root=ROOT):
    return yaml.safe_load((root/'eval/experiment_plan.yaml').read_text())


def export(root=ROOT):
    plan=design(root);out={}
    for arm in ('A','B'):
        way=plan[f'arm_{arm.lower()}']['way']
        rows=build_rows(arm,way,plan['claim'],root=root)
        atomic_write(root/f'results/{arm}.jsonl',''.join(json.dumps(r)+'\n' for r in rows))
        out[arm]=rows
    return out


def preflight(root=ROOT,*,network=True):
    load_local_environment(root)
    tasks={t.id:t for t in load_tasks(root/'eval/golden/v1/tasks')}
    ids=read_subset(root/'eval/subsets/claim.txt')
    if not 8<=len(ids)<=10 or any(i not in tasks for i in ids):
        raise validation.InputError('Subset must contain 8–10 distinct golden task IDs')
    for stratum in ('routine','unusual','adversarial','should_not_act'):
        if sum(tasks[i].stratum==stratum for i in ids)<2:
            raise validation.InputError('Subset needs at least two tasks per stratum')
    subset_commit=validation.committed(root,'eval/subsets/claim.txt')
    validation.committed(root,'eval/experiment_plan.yaml')
    for relative in ('settings.yaml','pricing.yaml','eval/results_07.py','eval/stats.py','eval/metrics.py',
                     'eval/grounded.py','eval/experiment_07.py','eval/golden/v1/manifest.yaml'):
        validation.committed(root,relative)
    for task in tasks.values():
        validation.committed(root,str(task.path.relative_to(root)))
    if network:remote_contains(root,subset_commit)
    settings=load_settings(root/'settings.yaml')
    if settings.provider not in REAL_BACKENDS or not os.environ.get(settings.api_key_env or 'OPENAI_API_KEY'):
        raise validation.InputError('Configured real-model API credential is not accessible; run make ping after configuring it')
    pricing=yaml.safe_load((root/'pricing.yaml').read_text())
    if settings.model not in pricing['models']:
        raise validation.InputError('The configured model has no exact pricing row')
    # Preserve the course ceilings, even if a local edit accidentally raised one.
    first=validation.git(root,'rev-list','--max-parents=0','HEAD').splitlines()[0]
    original=yaml.safe_load(validation.git(root,'show',f'{first}:settings.yaml'))
    for name in ('session_token_ceiling','lab_token_ceiling'):
        if getattr(settings,name)!=int(original[name]):
            raise validation.InputError('Configured token ceiling differs from the course starter: '+name)
    spent=Ledger(root/'runs/_ledger.jsonl').spent_tokens()
    if spent>=settings.lab_token_ceiling:raise validation.InputError('Lab token ceiling reached')
    return {'tasks':len(ids),'model':settings.model,'spent_tokens':spent,
            'remaining_tokens':settings.lab_token_ceiling-spent,'subset_commit':subset_commit}


def run_stage(stage,root=ROOT):
    preflight(root)
    plan=design(root)
    if stage=='finish':
        commit=validation.committed(root,'eval/thresholds/claim.yaml')
        remote_contains(root,commit)
        spec=yaml.safe_load((root/'eval/thresholds/claim.yaml').read_text())
        for key in ('claim','arm_a','arm_b','measure','gain','sweeps','delta','bar','group_floor','prediction'):
            if spec[key]!=plan[key]:raise validation.InputError('Threshold differs from the pre-pilot design: '+key)
    # The ordinary harness ping validates real connectivity, served model, tool
    # round trip and pricing. It prints no key. A failed ping starts no run.
    subprocess.run([sys.executable,'-m','harness.ping'],cwd=root,check=True)
    sweeps=range(1,4) if stage=='pilot' else range(4,6)
    for sweep in sweeps:
        for arm in ('A','B'):
            subprocess.run([sys.executable,'run.py','--tasks','eval/golden/v1/tasks','--subset','eval/subsets/claim.txt',
                            '--way',plan[f'arm_{arm.lower()}']['way'],'--runs','1','--start-sweep',str(sweep),'--jobs','1'],cwd=root,check=True)
    rows=export(root)
    ids=read_subset(root/'eval/subsets/claim.txt')
    if stage=='pilot':
        selected={a:[r for r in rows[a] if int(r['sweep'])<=3] for a in rows}
        numbers=pilot_numbers(selected,ids,plan['delta'])
        json_write(root/'eval/pilot_spread.json',numbers)
        print(json.dumps(numbers,indent=2))
    else:
        for arm in ('A','B'):matrix(rows[arm],ids,range(1,6))
        from eval.report_07 import build
        print(build())


def threshold(root=ROOT):
    threshold_path=root/'eval/thresholds/claim.yaml'
    if threshold_path.exists():raise validation.InputError('Threshold already exists; it will not be overwritten')
    plan=design(root)
    for trace_path in (root/'runs').glob('*.jsonl'):
        header=run_header(trace_path) if is_trace(trace_path) else None
        if header and header.get('backend') in REAL_BACKENDS and int(header.get('sweep') or 0)>=4 and header.get('task') in read_subset(root/'eval/subsets/claim.txt') and header.get('way') in {plan['arm_a']['way'],plan['arm_b']['way']}:
            raise validation.InputError('A fourth-sweep run already started, including unfinished attempts; retrospective threshold refused')
    rows=export(root)
    if any(int(r['sweep'])>=4 for a in rows for r in rows[a]):
        raise validation.InputError('Fourth-sweep runs already exist; no retrospective threshold is allowed')
    numbers=pilot_numbers(rows,read_subset(root/'eval/subsets/claim.txt'),plan['delta'])
    json_write(root/'eval/pilot_spread.json',numbers)
    spec={**plan,**{k:numbers[k] for k in ('s_a','s_b','n_needed','price_usd')},
          'effective_s_a':numbers['effective_s_a'],'effective_s_b':numbers['effective_s_b'],
          'zero_variance_quantum':numbers['zero_variance_quantum'],
          'pilot_cost_per_sweep_usd':numbers['pilot_cost_per_sweep_usd'],
          'planning_limitation':numbers['limitation']}
    atomic_write(threshold_path,yaml.safe_dump(spec,sort_keys=False))
    print('Pilot-derived threshold written. Commit and push claim.yaml before running finish; no advantage was displayed.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('preflight','pilot','threshold','finish'))
    args=parser.parse_args(argv)
    try:
        if args.stage=='preflight':print(json.dumps(preflight(),indent=2))
        elif args.stage=='threshold':threshold()
        else:run_stage(args.stage)
    except (validation.InputError,OSError,subprocess.CalledProcessError) as exc:
        parser.exit(2,str(exc)+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
