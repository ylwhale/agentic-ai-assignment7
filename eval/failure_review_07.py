"""Prepare actual failed Part C traces and validate explicit trace-review records.

Preparation supplies facts only. Annotations must come from inspection, with
cause and authorship disclosed in the report; no end-state heuristic assigns a
last-good or first-wrong call. This does not alter historical human reviews.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path

from harness import ROOT
from harness.tasks import end_state,load_tasks
from harness.trace import read_trace
from harness.tracker import Tracker
from eval.grounded import check
from notes.review_support import json_write


def failed_rows(root=ROOT):
    result=[]
    for arm in ('A','B'):
        path=root/f'results/{arm}.jsonl'
        if path.exists():
            result.extend(dict(json.loads(line),arm=arm) for line in path.read_text().splitlines()
                          if line.strip() and json.loads(line).get('passed') is False)
    return result


def validate_annotations(annotations,failed,root=ROOT):
    wanted={r['run_id']:r for r in failed}
    ids=[r.get('run_id') for r in annotations]
    if len(ids)!=len(set(ids)) or set(ids)!=set(wanted):
        raise ValueError('First-failure annotations must cover every failed run exactly once, with no successful/unknown runs')
    for row in annotations:
        run=row['run_id']
        calls=[e for e in read_trace(root/f'runs/{run}.jsonl') if e.get('type')=='tool_call']
        names=[e['name'] for e in calls]
        if row.get('arm')!=wanted[run]['arm']:
            raise ValueError(run+': incorrect arm')
        good,bad=row.get('last_good'),row.get('first_wrong')
        if good!='start' and good not in names or bad!='stop' and bad not in names:
            raise ValueError(run+': tool reference must exist, or use start/stop')
        if row.get('last_good_call') is not None:
            good_index=int(row['last_good_call'])
            bad_index=len(calls)+1 if row.get('first_wrong_call')=='stop' else int(row['first_wrong_call'])
            if good_index!=bad_index-1 or not 0<=good_index<=len(calls) or not 1<=bad_index<=len(calls)+1:
                raise ValueError(run+': call ordinals must be adjacent and within the trace')
            expected_good='start' if good_index==0 else calls[good_index-1]['name']
            expected_bad='stop' if bad_index==len(calls)+1 else calls[bad_index-1]['name']
            good_step='start' if good_index==0 else str(calls[good_index-1]['step'])
            bad_step='stop' if bad_index==len(calls)+1 else str(calls[bad_index-1]['step'])
            if (good,bad,str(row.get('last_good_step')),str(row.get('first_wrong_step')))!=(expected_good,expected_bad,good_step,bad_step):
                raise ValueError(run+': call names/steps disagree with cited trace ordinals')
        if row.get('trace_sha256') and hashlib.sha256((root/f'runs/{run}.jsonl').read_bytes()).hexdigest()!=row['trace_sha256']:
            raise ValueError(run+': trace changed after annotation')
        if row.get('cause') and row['cause'] not in {'local','upstream','structural'}:
            raise ValueError(run+': cause must be local/upstream/structural')
    return annotations


def prepare(root=ROOT):
    tasks={t.id:t for t in load_tasks(root/'eval/golden/v1/tasks')}
    tracker=Tracker(root,flaky=False,readback_fail=False)
    failed=failed_rows(root)
    for row in failed:
        task=tasks[row['task']];run=row['run_id']
        state=end_state(tracker,run,task)
        observed=check(task,state)
        if observed['passed']:
            raise ValueError(run+': tracker no longer agrees with exported failure; re-export before review')
        path=root/f'runs/{run}.jsonl'
        packet={'status':'MACHINE PREPARED; trace inspection and first-failure annotation required',
                'run_id':run,'arm':row['arm'],'task':task.id,'issue':task.issue,
                'expected':task.expect,'independent_source':task.source,
                'original_issue':(root/f'fixtures/issues/pool/{task.issue}.md').read_text(),
                'recorded_trace':read_trace(path),'recorded_state':state,'grounded':observed,
                'review_fields':{'last_good':'','first_wrong':'','cause':'','observation':'','reviewer':''}}
        json_write(root/f'eval/failure_evidence/{run}.json',packet)
    return len(failed)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','validate'))
    parser.add_argument('--annotations',type=Path,help='explicit reviewed CSV; otherwise manual then disclosed AI-assisted records')
    args=parser.parse_args(argv)
    if args.command=='prepare':
        print(f'{prepare()} actual failed-run packets prepared; no first-failure judgments generated.')
    else:
        path=args.annotations or ROOT/'eval/failures_manual.csv'
        if not path.exists() and args.annotations is None:
            path=ROOT/'eval/failures_ai.csv'
        if not path.exists():raise SystemExit('Missing explicit trace-review annotations: eval/failures_manual.csv')
        with path.open(newline='') as stream:rows=list(csv.DictReader(stream))
        validate_annotations(rows,failed_rows())
        print(f'{len(rows)} first-failure records validated against actual failed traces.')
    return 0


if __name__=='__main__':raise SystemExit(main())
