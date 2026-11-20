"""Read-only checkpoint/decoder diagnostic; not a new experimental arm or replay run.

Reproduce the observed plan-argument failure and test a decode-only counterfactual.
No tool, model, tracker write, or measured trajectory is replayed or replaced.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sqlite3

from harness import ROOT
from agent.diff import step_args
from agent.validator import validate
from notes.review_support import json_write


def diagnose(run_id,root=ROOT):
    path=root/f'runs/{run_id}.jsonl'
    events=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    candidate=None
    for event in events:
        if event.get('type')!='plan':continue
        for step in event['plan'].get('steps',[]):
            raw=step.get('args_json')
            if not isinstance(raw,str):continue
            try:json.loads(raw)
            except ValueError:
                candidate=(event,step,raw);break
        if candidate:break
    if not candidate:raise ValueError('No malformed recorded args_json found')
    event,step,raw=candidate
    original=step_args(step)
    repaired=raw;decoded=None;passes=0
    for passes in range(1,5):
        repaired=repaired.replace('\\"','"')
        try:
            decoded=json.loads(repaired)
            break
        except ValueError:continue
    if not isinstance(decoded,dict):raise ValueError('Decode-only counterfactual did not recover an object')
    checkpoints=[]
    db_path=root/'state/checkpoints.db'
    if db_path.exists():
        with sqlite3.connect(db_path.as_uri()+'?mode=ro',uri=True) as db:
            for seq,position,mode,body in db.execute('SELECT seq,step,mode,body FROM checkpoints WHERE run_id=? ORDER BY seq',(run_id,)):
                saved=json.loads(body);bad=[]
                for item in saved.get('plan',{}).get('steps',[]):
                    try:json.loads(item.get('args_json') or '{}')
                    except (ValueError,TypeError):bad.append(item.get('id'))
                checkpoints.append({'seq':seq,'step':position,'mode':mode,'malformed_plan_steps':bad})
    return {'run_id':run_id,'diagnostic_only':True,'model_calls':0,'tool_calls':0,
            'recorded_plan_version':event.get('version'),'recorded_plan_validation':validate(event['plan']),
            'recorded_plan_step':step.get('id'),'recorded_tool':step.get('tool'),
            'original_args_json':raw,'actual_step_args_output':original,
            'counterfactual_decode_passes':passes,'counterfactual_arguments':decoded,
            'saved_checkpoints':checkpoints,
            'conclusion':'The recorded plan passes structural validation but its args_json cannot be parsed and step_args returns {}. Decode-only repair restores argument keys; this confirms loss at the encoding boundary, not downstream task success.',
            'replay_limit':'Resuming an unchanged saved plan would retain malformed arguments. A future isolated replay should repair/validate the saved pending plan before any simulated tool executes and compare required-key validity with the original; do not alter these measured traces or their tracker rows.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    args=parser.parse_args(argv)
    result=diagnose(args.run_id)
    path=ROOT/'reports/PLAN_ENCODING_DIAGNOSTIC_07.json'
    json_write(path,result)
    print(json.dumps(result,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
