#!/usr/bin/env python3
"""Non-AI, interactive labelling of the 60 judge outputs.

    python3 notes/human_judge_cli.py --status
    python3 notes/human_judge_cli.py
    python3 notes/human_judge_cli.py --id j17

The script never suggests a pass/fail label or a reason. It records only the
human's own explicit input in eval/labels/labels.csv.
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
import io
import datetime as dt
import fcntl
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
OUTPUTS=ROOT/'fixtures'/'judge'/'outputs'
LABELS=ROOT/'eval'/'labels'/'labels.csv'
sys.path.insert(0,str(ROOT))
from eval import validation_07 as validation
from notes.review_support import atomic_write, json_write


def read_labels():
    if not LABELS.exists():
        return {}
    return {i:dict(id=i,**r) for i,r in validation.labels(ROOT,complete=False).items()}


def save_label(identifier,answer,reason,*,confirmed=False):
    if confirmed is not True:
        raise ValueError('Explicit human confirmation required')
    if identifier not in validation.output_ids(ROOT) or answer not in {'pass','fail'} or not reason.strip():
        raise ValueError('Valid ID, human pass/fail and nonempty reason required')
    LABELS.parent.mkdir(parents=True,exist_ok=True)
    with (LABELS.parent/'.labels.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        done=read_labels()
        if identifier in done:
            raise ValueError('Label already saved; preserve it and resolve edits explicitly')
        if LABELS.exists():
            stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            atomic_write(LABELS.parent/'backups'/f'{stamp}-labels.csv',LABELS.read_bytes())
        done[identifier]={'id':identifier,'label':answer,'reason':reason}
        stream=io.StringIO(newline='')
        writer=csv.DictWriter(stream,fieldnames=['id','label','reason'])
        writer.writeheader();writer.writerows(done[i] for i in sorted(done))
        atomic_write(LABELS,stream.getvalue())
    return len(done)


def confirm_criterion():
    path=ROOT/'eval/judge/criterion.md'
    if not path.exists() or not path.read_text().strip():
        raise ValueError('Write eval/judge/criterion.md yourself first')
    print(path.read_text())
    print('Confirm only if YOU authored/revised and independently checked this criterion, including unsupported-evidence cases.')
    if input('Type HUMAN to attest authorship and freeze this criterion revision: ').strip()!='HUMAN':
        print('Not confirmed.');return
    json_write(ROOT/'eval/judge/human_criterion.json',{'human_confirmed':True,'sha256':validation.sha(path),
               'at':dt.datetime.now(dt.timezone.utc).isoformat()})
    print('Human criterion confirmation recorded; later edits require fresh confirmation.')


def ask(question, options=None):
    while True:
        answer=input(question+' ').strip()
        if not answer:
            print('Please answer, or Ctrl-C to cancel.')
        elif options and answer not in options:
            print('Choose from '+', '.join(sorted(options)))
        else:
            return answer


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--status',action='store_true')
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--confirm-criterion',action='store_true')
    parser.add_argument('--batch',type=int,default=1,help='number of individually confirmed labels per session')
    parser.add_argument('--id',help='specific output to label')
    args=parser.parse_args(argv)
    if args.batch<1:
        parser.error('--batch must be positive')
    if args.confirm_criterion:
        confirm_criterion();return 0
    if args.validate:
        checked=validation.labels(ROOT)
        validation.split(ROOT)
        validation.criterion(ROOT)
        print(f'{len(checked)} human labels valid; split valid; criterion confirmation current.');return 0
    ids=sorted(p.stem for p in OUTPUTS.glob('*.json'))
    done=read_labels()
    if args.status:
        print(f'{len(done)}/{len(ids)} human labels recorded. Remaining: '+', '.join(i for i in ids if i not in done))
        return 0
    if args.id and args.id not in ids:
        raise SystemExit(f'Invalid output ID {args.id}')
    if args.id and args.id in done:
        raise SystemExit('This output already has a saved human label; it will not be overwritten.')
    validation.criterion(ROOT)
    todo=[args.id] if args.id else [i for i in ids if i not in done]
    if not todo:
        print('All 60 outputs already labelled.')
        return 0
    saved_this_session=0
    for identifier in todo:
        payload=json.loads((OUTPUTS/f'{identifier}.json').read_text())
        print('\n'+'='*80+'\nOUTPUT '+identifier+' - read the issue, EVERY tool result, then comment\n'+'='*80)
        print(json.dumps({k:payload[k] for k in ('id','system','issue','evidence','comment')},ensure_ascii=False,indent=2))
        print('\nCriterion: eval/judge/criterion.md. Formulate a label and reason yourself.')
        try:
            answer=ask('YOUR label (pass/fail/skip):',{'pass','fail','skip'})
            if answer=='skip':
                print('Skipped without assigning a label.')
                continue
            reason=ask('YOUR concrete reason (required):')
            while len(reason)<15:
                print('Give a concrete evidence-based reason, at least 15 characters.')
                reason=ask('YOUR reason:')
            if ask('Save YOUR label? (yes/no):',{'yes','no'})!='yes':
                continue
            count=save_label(identifier,answer,reason,confirmed=True)
            done=read_labels()
            print(f'Saved {identifier}; {count}/60 manually labelled.')
            saved_this_session+=1
        except (KeyboardInterrupt,EOFError):
            print('\nStopped; previous human labels are safe.')
            break
        if saved_this_session>=args.batch:
            break
    return 0

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (validation.InputError,ValueError) as exc:
        raise SystemExit(str(exc))
