"""Validate Assignment 7 human inputs and provenance without assigning judgments."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import yaml
from harness import ROOT


class InputError(ValueError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output_ids(root=ROOT):
    return sorted(p.stem for p in (root/'fixtures/judge/outputs').glob('*.json'))


def labels(root=ROOT, *, complete=True, allowed=None):
    """Validation reads IDs/shape; callers may receive only examples/tuning labels.

    Nothing here chooses or repairs a label. Duplicate rows are errors, even if
    they contain the same judgment. Empty templates are not completed labels.
    """
    path=root/'eval/labels/labels.csv'
    if not path.exists():
        raise InputError('Human labels missing: eval/labels/labels.csv')
    expected=set(output_ids(root)); result={}
    with path.open(newline='',encoding='utf-8-sig') as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames != ['id','label','reason']:
            raise InputError('labels.csv header must be exactly id,label,reason')
        seen=set()
        for number,row in enumerate(reader,2):
            if None in row or any(value is None for value in row.values()):
                raise InputError(f'labels.csv row {number}: malformed CSV')
            identifier=row['id'].strip()
            if not identifier and not any(row.values()):
                continue
            if identifier in seen:
                raise InputError(f'labels.csv row {number}: duplicate ID {identifier}')
            seen.add(identifier)
            if identifier not in expected:
                raise InputError(f'labels.csv row {number}: unknown ID {identifier}')
            if not row['label'].strip() and not row['reason'].strip():
                continue
            if row['label'].strip() not in {'pass','fail'} or not row['reason'].strip():
                raise InputError(f'labels.csv row {number}: human pass/fail and nonempty reason required')
            result[identifier]={'label':row['label'].strip(),'reason':row['reason'].strip()}
    missing=expected-result.keys()
    if complete and missing:
        raise InputError(f'{len(result)}/{len(expected)} human labels complete; missing: '+', '.join(sorted(missing)))
    return {i:r for i,r in result.items() if allowed is None or i in allowed}


def split(root=ROOT):
    path=root/'eval/labels/split.yaml'
    data=yaml.safe_load(path.read_text())
    expected=output_ids(root)
    if not isinstance(data,dict) or any(not isinstance(data.get(k),list) for k in ('examples','tuning','test')):
        raise InputError('split.yaml requires examples, tuning and test ID lists')
    flat=[i for k in ('examples','tuning','test') for i in data[k]]
    if sorted(flat)!=expected:
        raise InputError('Split must be disjoint and cover every output exactly once')
    n=len(expected)
    for key,low,high in [('examples',.10,.20),('tuning',.40,.45),('test',.40,.45)]:
        if not round(low*n)<=len(data[key])<=round(high*n):
            raise InputError(f'{key} split violates the required proportion')
    return data


def git(root,*args):
    result=subprocess.run(['git',*args],cwd=root,capture_output=True,text=True)
    if result.returncode:
        raise InputError('Git provenance check failed: '+ ' '.join(args))
    return result.stdout.strip()


def committed(root,relative):
    path=root/relative
    recorded=subprocess.run(['git','show',f'HEAD:{relative}'],cwd=root,capture_output=True)
    if recorded.returncode or recorded.stdout!=path.read_bytes():
        raise InputError(f'{relative} must be committed without subsequent edits')
    return git(root,'log','-1','--format=%H','--',relative)


def require_push(root,commit):
    # A fetched/pushed tracking ref is necessary but not by itself a remote
    # verification. The driver verifies ls-remote before starting paid stages.
    branch=git(root,'rev-parse','--abbrev-ref','--symbolic-full-name','@{upstream}')
    git(root,'merge-base','--is-ancestor',commit,branch)


def criterion(root=ROOT):
    path=root/'eval/judge/criterion.md'
    receipt=root/'eval/judge/human_criterion.json'
    if not path.exists() or not path.read_text().strip():
        raise InputError('Write your own eval/judge/criterion.md first')
    data=json.loads(receipt.read_text()) if receipt.exists() else {}
    if data.get('human_confirmed') is not True or data.get('sha256')!=sha(path):
        raise InputError('Criterion needs human authorship confirmation: python notes/human_judge_cli.py --confirm-criterion')
    return path.read_text()
