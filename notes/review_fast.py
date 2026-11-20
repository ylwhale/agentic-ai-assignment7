#!/usr/bin/env python3
"""Fast, human-confirmed Assignment 7 Part A reviews; no model/API calls.

Run with no arguments to review/resume; :q pauses at any field. Prepared evidence
and drafts never count. Type SAVE at the confirmation screen for each review.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pydoc
import re
import sys

try:
    from . import batch_review as batch
    from .review_support import (ROOT, Store, atomic_write, audit, digest, field, json_write,
        observation_warnings, read_json, render_packet, resolve_call, source_options,
        taxonomy_report, validate_record)
except ImportError:
    import batch_review as batch
    from review_support import (ROOT, Store, atomic_write, audit, digest, field, json_write,
        observation_warnings, read_json, render_packet, resolve_call, source_options,
        taxonomy_report, validate_record)


class Pause(Exception):
    pass


def show_status(store, packets=None):
    packets = packets or store.packets()
    done = set(store.blocks())
    print(f'{len(done)}/40 saved reviews; {max(0,40-len(done))} still required; {len(packets)-len(done)} pending of {len(packets)} traces.')
    pending = store.pending(packets)
    if pending:
        print('Next:', pending[0])
    return pending


def source_text(store, packet, number):
    options = source_options(packet)
    if not 1 <= number <= len(options):
        raise ValueError('Choose a displayed independent source number')
    ref = options[number-1]
    if ref.startswith('fixtures/closed_issues.yaml'):
        return str(packet['maintainer'])
    path = ref.split(' ',1)[0]
    return '\n'.join(f'{n}: {line}' for n,line in enumerate((store.root/path).read_text().splitlines(),1))


def command(answer, store, packet, output):
    bits = answer.split(maxsplit=1)
    cmd, arg = bits[0], bits[1] if len(bits)>1 else ''
    if cmd in {':q',':pause'}:
        raise Pause
    if cmd == ':trace':
        output((store.root/packet['trace_file']).read_text())
    elif cmd == ':packet':
        output(render_packet(packet, source_limit=1000))
    elif cmd == ':control':
        output(json.dumps(packet['control_events'], ensure_ascii=False, indent=2))
    elif cmd == ':tool':
        if not re.fullmatch(r'c?\d+', arg):
            raise ValueError('Use :tool cN from the displayed table')
        call = int(arg.lstrip('c'))
        matches = [c for c in packet['calls'] if c['call']==call]
        if not matches:
            raise ValueError('Unknown call')
        output(json.dumps(matches[0], ensure_ascii=False, indent=2))
    elif cmd == ':source':
        output(source_text(store,packet,int(arg)))
    elif cmd == ':help':
        output(':q pause | :trace full raw trace | :packet all source excerpts | :tool cN full tool result | :source N full independent source | :control rejected/proposed calls. Viewing never marks evidence checked.')
    else:
        raise ValueError('Unknown command; use :help')


def review_one(store, packet, *, input_fn=input, output=print, display=print):
    run = packet['run_id']
    if run in store.blocks():
        raise ValueError('Already reviewed: ' + run)
    draft = read_json(store.draft_path(run), {})
    values = dict(draft.get('fields', {}))
    if draft.get('fixture_hashes') and draft['fixture_hashes'] != packet['fixture_hashes']:
        output('Evidence changed since the draft; inspect it again before confirming.')
    # Can resume unverified CSV work; never carry verified through to confirmation.
    _, queue = store.read_queue()
    prior = next((r for r in queue if r['run_id']==run), {})
    for key in batch.HUMAN_FIELDS[:-1]:
        if key not in values and prior.get(key):
            values[key] = prior[key]
    display(render_packet(packet))
    output('\nEnter YOUR judgments. :help lists inspection commands; :q pauses. Enter retains a displayed draft value.')
    prompts = [
        ('expected_decision','Expected decision [a act / r refuse / s stop]'),
        ('actual_decision','Actual decision/workflow observed (your words)'),
        ('last_correct_call','Last correct call [cN / unique step / tool at step N / start]'),
        ('first_incorrect_call','First incorrect call [cN / none / stopped too early]'),
        ('observation','Your own observation with decisive evidence (40+ characters)'),
        ('assessment','Assessment [s successful / f failed / u uncertain]'),
        ('source_checked','Independent evidence YOU checked [source numbers separated by commas, or paths separated by semicolons]'),
    ]
    def prompt(label):
        while True:
            answer = input_fn(label + '> ').strip()
            if answer.startswith(':'):
                try:
                    command(answer,store,packet,display)
                except (ValueError,IndexError) as exc:
                    output(str(exc))
                continue
            return answer
    try:
        while True:
            for key, label in prompts:
                while True:
                    default = values.get(key,'')
                    answer = prompt(label + (f' [{default}]' if default else '')) or default
                    try:
                        if not answer:
                            raise ValueError('A human-entered value is required')
                        if key == 'expected_decision':
                            answer = {'a':'act','r':'refuse','s':'stop'}.get(answer.lower(),answer.lower())
                            if answer not in batch.CHOICES:
                                raise ValueError('Choose act/refuse/stop')
                        if key == 'assessment':
                            answer = {'s':'successful','f':'failed','u':'uncertain'}.get(answer.lower(),answer.lower())
                            if answer not in batch.ASSESSMENTS:
                                raise ValueError('Choose successful/failed/uncertain')
                        if key in {'last_correct_call','first_incorrect_call'}:
                            answer = resolve_call(answer,packet,first=key=='first_incorrect_call')
                        if key == 'source_checked' and re.fullmatch(r'\d+(?:\s*,\s*\d+)*',answer):
                            refs = source_options(packet)
                            indexes = [int(n) for n in answer.split(',')]
                            if any(not 1<=n<=len(refs) for n in indexes):
                                raise ValueError('Choose displayed source numbers')
                            answer = '; '.join(refs[n-1] for n in dict.fromkeys(indexes))
                        if key=='observation' and len(answer)<40:
                            raise ValueError('Write your own substantive observation (40+ characters)')
                        values[key] = answer
                        store.save_draft(run,values,packet)
                        break
                    except ValueError as exc:
                        output(str(exc))
            row = dict(values, run_id=run)
            errors = validate_record(row,packet,store.root)
            if errors:
                output('Cannot save:\n' + '\n'.join(errors) + '\nRevisit fields (Enter retains each value).')
                continue
            output('\nCONFIRM YOUR REVIEW — ' + run)
            for key,_ in prompts:
                output(f'{key}: {values[key]}')
            warnings = observation_warnings(row,packet)
            for warning in warnings:
                output('WARNING: ' + warning)
            answer = prompt('Type SAVE to confirm this is your own independent review; edit revisits fields; :q pauses')
            if answer == 'SAVE':
                count = store.save(row,packet,confirmed=True)
                output(f'Saved {run}. Total {count}/40; {max(0,40-count)} still required.')
                return True
            if answer.lower() == 'edit':
                continue
            output('Not confirmed. Draft retained; no completed review saved.')
            return False
    except (Pause,KeyboardInterrupt,EOFError):
        output('\nPaused. Any unconfirmed inputs are retained; no completed review added.')
        return False


def tag_review(store, run, input_fn=input):
    blocks = store.blocks()
    if run not in blocks:
        raise ValueError('Only saved human reviews can be tagged')
    observation = field(blocks[run],'My observation','My observation (draft for review)')
    if not observation:
        raise ValueError('No recorded human observation')
    print(observation)
    print('Enter your failure categories from this observation, separated by semicolons; none for no failure. No suggestions supplied.')
    answer = input_fn('Categories> ').strip()
    if not answer:
        return
    categories = [] if answer.lower()=='none' else list(dict.fromkeys(x.strip() for x in answer.split(';') if x.strip()))
    print('Categories:',categories)
    if input_fn('Type SAVE to confirm these tags> ').strip() != 'SAVE':
        return
    with store.lock():
        # Re-read under lock to bind tags to the observation actually inspected.
        current = field(store.blocks()[run],'My observation','My observation (draft for review)')
        if current != observation:
            raise ValueError('Observation changed; reopen before tagging')
        tags = read_json(store.out/'taxonomy.json',{})
        if (store.out/'taxonomy.json').exists():
            store.backup(store.out/'taxonomy.json')
        tags[run] = {'categories':categories,'observation_sha256':digest(observation),'human_confirmed':True}
        json_write(store.out/'taxonomy.json',tags)
    print(taxonomy_report(store))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--status',action='store_true')
    group.add_argument('--prepare',action='store_true',help='Refresh all pending evidence packets and compatible CSV')
    group.add_argument('--preview',action='store_true',help='Print next/run evidence without prompting or saving')
    group.add_argument('--validate',action='store_true',help='Audit saved reviews, references, preservation and progress')
    group.add_argument('--history',action='store_true',help='List preservation backup and confirmed save history')
    group.add_argument('--taxonomy',action='store_true',help='Summarize only human-entered taxonomy tags')
    group.add_argument('--tag',metavar='RUN_ID',help='Tag a saved observation with your own failure categories')
    parser.add_argument('--run',help='Exact pending run ID')
    parser.add_argument('--batch',type=int,default=0,help='Stop after N explicitly confirmed saves (default: continue)')
    args = parser.parse_args(argv)
    if args.batch<0:
        parser.error('--batch must be nonnegative')
    store = Store()
    try:
        if args.validate:
            result = audit(store)
            atomic_write(store.out/'audit.json',json.dumps(result,indent=2)+'\n')
            print(json.dumps(result,indent=2))
            return int(bool(result['errors']))
        if args.history:
            print(json.dumps(read_json(store.out/'preservation.json',{}),indent=2))
            for path in sorted((store.out/'history').glob('*.json')):
                event = read_json(path)
                print(event['at'],event['run_id'],event.get('status','unknown'),path)
            return 0
        if args.taxonomy:
            tags = read_json(store.out/'taxonomy.json',{})
            print(f'Taxonomy: {len(tags)}/{len(store.blocks())} observations tagged. Use --tag RUN_ID after recording observations; --taxonomy shows new-category history and saturation evidence.')
            return 0
        if args.tag:
            tag_review(store,args.tag)
            return 0
        packets = store.prepare(batch.FIELDS) if args.prepare else store.packets()
        if args.prepare or args.status:
            show_status(store,packets)
            return 0
        pending = store.pending(packets)
        if args.run:
            if args.run not in packets:
                raise ValueError('Unknown run: '+args.run)
            if args.run not in pending:
                raise ValueError('Already reviewed: '+args.run)
            pending = [args.run] + [r for r in pending if r != args.run]
        if not pending:
            print('All traces already reviewed.')
            return 0
        if args.preview:
            print(render_packet(packets[pending[0]]))
            print('DEMONSTRATION ONLY: no decisions generated, no review saved.')
            show_status(store,packets)
            return 0
        # Refresh packets/CSV before the first interactive session; no human fields generated.
        store.prepare(batch.FIELDS)
        saved = 0
        while pending:
            show_status(store,packets)
            display = pydoc.pager if sys.stdout.isatty() else print
            if not review_one(store,packets[pending[0]],display=display):
                break
            saved += 1
            print(taxonomy_report(store))
            if args.batch and saved>=args.batch:
                break
            pending = store.pending(packets)
        return 0
    except (ValueError,OSError) as exc:
        print('Review error: '+str(exc),file=sys.stderr)
        return 2
    except (KeyboardInterrupt,EOFError):
        print('\nPaused; no unconfirmed review saved.')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
