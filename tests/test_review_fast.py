"""Offline tests; synthetic reviewer answers are confined to temporary copies."""
from __future__ import annotations
import contextlib
import csv
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from notes import batch_review, review_fast
from notes.review_support import (ROOT, Store, atomic_write, audit, digest, extract, field,
    json_write, observation_warnings, read_json, render_packet, resolve_call, review_blocks,
    select_order, source_options, taxonomy_report, validate_record)

RUN = 'workflow-issue-4605-s01-83f50a'


class ReviewFastTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT/'fixtures/traces7', self.root/'fixtures/traces7')
        shutil.copytree(ROOT/'fixtures/repo', self.root/'fixtures/repo')
        shutil.copytree(ROOT/'fixtures/issues/pool', self.root/'fixtures/issues/pool')
        shutil.copy2(ROOT/'fixtures/closed_issues.yaml',self.root/'fixtures/closed_issues.yaml')
        (self.root/'notes').mkdir()
        # Real immutable trace fixtures exercise extraction, but a user's growing
        # review document is not a test fixture. Build a fixed synthetic ledger
        # in the temporary root; RUN must remain pending for save/resume tests.
        fixture_ids = sorted(p.stem for p in (self.root/'fixtures/traces7').glob('agent-*.jsonl'))[:17]
        document = ['# Synthetic test reviews', '',
                    '**Runs reviewed so far:** 17',
                    '**Runs remaining to meet the minimum:** 23',
                    '**Issues examined:** #4612', '']
        for number, run in enumerate(fixture_ids,1):
            packet = extract(self.root,run)
            document.extend([f"## Run {number} — Issue #{packet['issue']}", '',
                f'**Run ID:** `{run}`', '',
                "**Issue title:** API reference doesn't give the limits (synthetic test title)", '',
                '**Expected decision:** act', '', '**Decision made:** synthetic test input', '',
                '**Last correct call:** before any call', '', '**First incorrect call:** none', '',
                '**My observation:** Synthetic prior observation for preservation tests; no human work is copied.', '',
                '**Assessment:** uncertain', '', '**Source checked:** fixtures/repo/docs/API.md', '', '---', ''])
        document.append('## Template — Additional Run Reviews\n')
        (self.root/'notes/trace-review.md').write_text('\n'.join(document))
        self.store = Store(self.root)
        self.packet = extract(self.root,RUN)
        self.before = self.store.document.read_bytes()
        self.row = dict(run_id=RUN, expected_decision='refuse',actual_decision='Synthetic test workflow',
                        last_correct_call='c1',first_incorrect_call='c5',
                        observation='Synthetic reviewer input used only to test explicit confirmation and safe saving.',
                        assessment='uncertain',source_checked='fixtures/closed_issues.yaml issue #4605')

    def answers(self, confirmation='SAVE'):
        return iter(['r','Synthetic test workflow','c1','c5',self.row['observation'],'u','2',confirmation])

    def interact(self, answers):
        output=[]
        result=review_fast.review_one(self.store,self.packet,input_fn=lambda _:next(answers),
                                     output=output.append,display=output.append)
        return result,output

    def test_extract_full_results_original_and_state(self):
        p=self.packet
        self.assertIn('Could you paste the real',p['description'])
        call=p['calls'][0]
        self.assertGreater(len(call['result']),len(call['result_excerpt']))
        self.assertEqual(p['calls'][-1]['step'],2)
        self.assertEqual(p['calls'][-1]['call'],5)
        self.assertEqual(p['state']['labels'],[])
        self.assertIn('actual recorded labels', '\n'.join(p['warnings']))
        self.assertTrue(p['independent'])
        for item in p['independent']:
            self.assertEqual(item['sha256'],digest((self.root/item['path']).read_bytes()))
        self.assertIn('MACHINE PREPARED',render_packet(p))

    def test_errors_and_claims_are_extracted_factually(self):
        path=self.root/self.packet['trace_file']
        events=[json.loads(line) for line in path.read_text().splitlines()]
        call=next(e for e in events if e['type']=='tool_call')
        call['is_error']=True;call['result']='Synthetic tool failure'
        model=next(e for e in events if e['type']=='model_call')
        model['text']='I created a pull request.'
        path.write_text('\n'.join(json.dumps(e) for e in events)+'\n')
        p=extract(self.root,RUN)
        self.assertTrue(any('returned an error' in w for w in p['warnings']))
        self.assertTrue(any('claims a prs action' in w for w in p['warnings']))

    def test_prepare_all_pending_preserves_every_existing_review(self):
        self.store.prepare(batch_review.FIELDS)
        self.assertEqual(self.before,self.store.document.read_bytes())
        self.assertEqual(len(list((self.store.out/'packets').glob('*.md'))),43)
        self.assertEqual(len(list((self.store.out/'packets').glob('*.json'))),43)
        _,rows=self.store.read_queue()
        self.assertEqual(len(rows),43)
        self.assertTrue(all(not r[f] for r in rows for f in batch_review.HUMAN_FIELDS))
        self.assertEqual(self.store.preservation_errors(),[])
        self.assertEqual(len(read_json(self.store.out/'preservation.json')['reviews']),17)

    def test_selection_balances_ways_and_context_without_labels(self):
        packets=self.store.packets()
        done=set(self.store.blocks())
        order=select_order(packets,done)
        self.assertEqual(len(order),43)
        self.assertEqual(len(set(order)),43)
        self.assertFalse(done.intersection(order))
        self.assertEqual({packets[r]['way'] for r in order[:23]}, {'agent','direct','planned','workflow'})
        signals={f for r in order[:23] for f in packets[r]['features']}
        self.assertIn('termination:turn_limit',signals)
        self.assertIn('history:no-change-language',signals)
        self.assertIn('history:declined-or-private',signals)
        self.assertIn('pr:present',signals)
        self.assertEqual(order,select_order(packets,done))

    def test_steps_names_and_same_step_ambiguity(self):
        self.assertIn('issues_read at step 0',resolve_call('0',self.packet))
        for bad in ('99','code_read_file at step 0','1','c99','issues_comment at step 0'):
            with self.assertRaises(ValueError,msg=bad):
                resolve_call(bad,self.packet)
        self.assertEqual(resolve_call('c3',self.packet),'code_search at step 1 [c3]')
        with self.assertRaises(ValueError):
            resolve_call('code_search at step 1',self.packet)

    def test_no_confirmation_no_completed_review(self):
        with self.assertRaisesRegex(ValueError,'confirmation'):
            self.store.save(self.row,self.packet,confirmed=False)
        result,_=self.interact(self.answers('no'))
        self.assertFalse(result)
        self.assertEqual(self.before,self.store.document.read_bytes())
        self.assertNotIn('verified',read_json(self.store.draft_path(RUN))['fields'])

    def test_explicit_confirmation_backup_history_duplicate_prevention(self):
        result,_=self.interact(self.answers())
        self.assertTrue(result)
        self.assertEqual(len(self.store.blocks()),18)
        self.assertEqual(audit(self.store)['still_required'],22)
        self.assertEqual(audit(self.store)['errors'],[])
        for run,block in review_blocks(self.before.decode()).items():
            self.assertEqual(block,self.store.blocks()[run])
        self.assertTrue(any(p.read_bytes()==self.before for p in (self.store.out/'backups').glob('*.md')))
        self.assertEqual(len(list((self.store.out/'history').glob('*.json'))),1)
        after=self.store.document.read_bytes()
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            self.store.save(self.row,self.packet,confirmed=True)
        self.assertEqual(after,self.store.document.read_bytes())
        self.assertFalse(self.store.draft_path(RUN).exists())

    def test_pause_resume_keeps_human_fields_requires_new_confirmation(self):
        result,_=self.interact(iter(['r',':q']))
        self.assertFalse(result)
        self.assertEqual(read_json(self.store.draft_path(RUN))['fields']['expected_decision'],'refuse')
        self.assertEqual(self.store.pending(self.store.packets())[0],RUN)
        # Empty Enter retains the human draft; no default judgments generated.
        answers=self.answers(); next(answers)
        result,_=self.interact(iter(['',*answers]))
        self.assertTrue(result)
        self.assertEqual(len(self.store.blocks()),18)

    def test_eof_keeps_only_unconfirmed_draft(self):
        calls=iter(['r'])
        def reader(_):
            try:return next(calls)
            except StopIteration:raise EOFError
        result=review_fast.review_one(self.store,self.packet,input_fn=reader,output=lambda _:None,display=lambda _:None)
        self.assertFalse(result)
        self.assertEqual(self.before,self.store.document.read_bytes())

    def test_invalid_record_or_independent_source_cannot_save(self):
        for changes in ({'first_incorrect_call':'c99'}, {'source_checked':'notes/trace-evidence/fake.md'},
                        {'source_checked':'fixtures/closed_issues.yaml issue #9999'},
                        {'source_checked':'fixtures/repo/does-not-exist.ts'},
                        {'source_checked':'fixtures/issues/pool/4605.md'},
                        {'observation':'fake\n\n**Run ID:** `injected`'}, {'assessment':'maybe'}):
            with self.assertRaises(ValueError,msg=str(changes)):
                self.store.save(dict(self.row,**changes),self.packet,confirmed=True)
        self.assertEqual(self.before,self.store.document.read_bytes())

    def test_observation_warnings_never_rewrite_assessment(self):
        row=dict(self.row,observation='The agent opened a pull request and posted a comment after reading the issue.')
        warnings=observation_warnings(row,self.packet)
        self.assertTrue(any('0 open PRs' in w for w in warnings))
        self.store.save(row,self.packet,confirmed=True)
        block=self.store.blocks()[RUN]
        self.assertIn(row['observation'],block)
        self.assertIn('**Assessment:** uncertain',block)

    def test_changed_evidence_blocks_stale_confirmation(self):
        path=self.root/'fixtures/closed_issues.yaml'
        path.write_text(path.read_text()+'\n# changed after display\n')
        with self.assertRaisesRegex(ValueError,'Evidence changed'):
            self.store.save(self.row,self.packet,confirmed=True)
        self.assertEqual(self.before,self.store.document.read_bytes())

    def test_preservation_detects_edited_or_removed_legacy_records(self):
        with self.store.lock():self.store.baseline()
        self.store.document.write_text(self.before.decode().replace('API reference doesn\'t','Edited API reference doesn\'t',1))
        self.assertTrue(self.store.preservation_errors())
        with self.assertRaisesRegex(ValueError,'changed or removed'):
            self.store.save(self.row,self.packet,confirmed=True)

    def test_duplicate_queue_and_duplicate_document_never_silently_collapse(self):
        self.store.write_queue(['run_id'],[{'run_id':RUN},{'run_id':RUN}])
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            self.store.read_queue()
        document=self.before.decode()
        block=next(iter(review_blocks(document).values()))
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            review_blocks(document+block)

    def test_progress_uses_document_not_preparation_draft_or_verified_csv(self):
        self.store.prepare(batch_review.FIELDS)
        self.store.save_draft(RUN,self.row,self.packet)
        fields,rows=self.store.read_queue()
        next(r for r in rows if r['run_id']==RUN).update(self.row,verified='yes')
        self.store.write_queue(fields,rows)
        result=audit(self.store)
        self.assertEqual((result['saved_reviews'],result['pending'],result['still_required']),(17,43,23))
        self.store.document.write_text(self.before.decode().replace('so far:** 17','so far:** 99'))
        self.assertTrue(any('counter' in x for x in audit(self.store)['errors']))

    def test_prepare_preserves_csv_human_fields_and_removes_only_saved_rows(self):
        self.store.prepare(batch_review.FIELDS)
        fields,rows=self.store.read_queue()
        row=next(r for r in rows if r['run_id']==RUN)
        row.update(observation=self.row['observation'],expected_decision='refuse')
        self.store.write_queue(fields,rows)
        self.store.prepare(batch_review.FIELDS)
        _,rows=self.store.read_queue()
        self.assertEqual(next(r for r in rows if r['run_id']==RUN)['observation'],self.row['observation'])
        self.store.save(self.row,self.packet,confirmed=True)
        self.store.prepare(batch_review.FIELDS)
        self.assertNotIn(RUN,{r['run_id'] for r in self.store.read_queue()[1]})
        self.assertEqual(len(self.store.read_queue()[1]),42)

    def test_interrupted_write_before_commit_resumes_without_review(self):
        original=atomic_write
        def interrupted(path,content):
            if path==self.store.document:raise OSError('simulated process interruption')
            return original(path,content)
        with patch('notes.review_support.atomic_write',side_effect=interrupted):
            with self.assertRaises(OSError):self.store.save(self.row,self.packet,confirmed=True)
        self.assertEqual(self.before,self.store.document.read_bytes())
        self.assertEqual(self.store.preservation_errors(),[])
        event=read_json(next((self.store.out/'history').glob('*.json')))
        self.assertEqual(event['status'],'aborted')
        self.assertEqual(self.store.save(self.row,self.packet,confirmed=True),18)

    def test_interrupted_write_after_commit_recovers_queue_from_document(self):
        self.store.prepare(batch_review.FIELDS)
        original=json_write
        def interrupted(path,value):
            if path.parent.name=='history' and value.get('status')=='committed':raise OSError('after commit')
            return original(path,value)
        with patch('notes.review_support.json_write',side_effect=interrupted):
            with self.assertRaises(OSError):self.store.save(self.row,self.packet,confirmed=True)
        self.assertEqual(len(self.store.blocks()),18)
        self.assertEqual(self.store.preservation_errors(),[])
        self.store.prepare(batch_review.FIELDS)
        self.assertEqual(len(self.store.read_queue()[1]),42)
        self.assertNotIn(RUN,self.store.pending(self.store.packets()))

    def test_taxonomy_requires_saved_observations_and_never_infers_categories(self):
        text=taxonomy_report(self.store)
        self.assertIn('0/17',text)
        self.assertIn('not established',text)
        self.assertIn('Counts: none recorded',text)
        with self.assertRaises(ValueError):review_fast.tag_review(self.store,RUN)
        self.store.save(self.row,self.packet,confirmed=True)
        with contextlib.redirect_stdout(io.StringIO()):
            answers=iter(['Synthetic user category','SAVE'])
            review_fast.tag_review(self.store,RUN,input_fn=lambda _:next(answers))
        text=taxonomy_report(self.store)
        self.assertIn('Synthetic user category: 1',text)
        self.assertIn('1/18',text)
        self.assertIn('not established',text)

    def test_batch_compatibility_validates_before_import_and_refreshes_progress(self):
        self.store.prepare(batch_review.FIELDS)
        fields,rows=self.store.read_queue()
        target=next(r for r in rows if r['run_id']==RUN)
        target.update(self.row,verified='yes',first_incorrect_call='c99')
        self.store.write_queue(fields,rows)
        with patch.multiple(batch_review,ROOT=self.root,DOCUMENT=self.store.document,QUEUE=self.store.queue), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):batch_review.apply()
            self.assertFalse(batch_review.ready_row(target)[0])
            self.assertEqual(self.before,self.store.document.read_bytes())
            target['first_incorrect_call']='c5'
            # A stale/malicious machine column must never override fixture facts.
            target['issue']='9999'
            self.store.write_queue(fields,rows)
            self.assertTrue(batch_review.ready_row(target)[0])
            batch_review.apply(dry_run=True)
            self.assertEqual(self.before,self.store.document.read_bytes())
            batch_review.apply()
            batch_review.apply()
        self.assertEqual(len(self.store.blocks()),18)
        self.assertIn('Issue #4605',self.store.blocks()[RUN])
        self.assertIn('saved reviews: **18**',(self.store.out/'evidence-summary.md').read_text())

    def test_unknown_run_missing_fields_and_out_of_order_calls_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unknown historical'):
            extract(self.root,'does-not-exist')
        for changes in ({'observation':''},{'actual_decision':''},
                        {'last_correct_call':'c5','first_incorrect_call':'c1'}):
            with self.assertRaises(ValueError):
                self.store.save(dict(self.row,**changes),self.packet,confirmed=True)
        self.assertEqual(self.before,self.store.document.read_bytes())

    def test_legacy_inspect_full_uses_untruncated_raw_results(self):
        output=io.StringIO()
        with patch.object(batch_review,'ROOT',self.root), contextlib.redirect_stdout(output):
            batch_review.inspect(RUN,full=True)
        self.assertIn('FULL RECORDED TOOL INPUTS/RESULTS',output.getvalue())
        self.assertIn('result_chars',output.getvalue())
        self.assertIn('all_recorded_states',output.getvalue())


if __name__=='__main__':
    unittest.main()
