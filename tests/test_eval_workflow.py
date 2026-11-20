"""Synthetic, isolated tests of experiment ordering, human boundaries and exports.

All labels, comments, sessions and run records below are test data in temporary
roots; none is assignment evidence or copied into the student's artifacts.
"""
from contextlib import contextmanager
import csv
import io
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import yaml
from harness import ROOT
from eval import experiment_07 as experiment, judge, report_07, validation_07 as validation
from eval.results_07 import build_rows
from eval.stats import mean,standard_error,pass_at_k,pass_hat_k
from notes import human_judge_cli
from notes.review_support import json_write


class MathsAndMatrixTests(unittest.TestCase):
    def rows(self):
        return {a:[{'task':i,'sweep':s,'measure':0,'cost_usd':.25,'passed':False,
                    'facts':{'present':0,'total':1},'metrics':{'no_tools':True}}
                   for s in (1,2,3) for i in ('a','b','c','d','e','f','g','h')] for a in ('A','B')}

    def test_exact_estimators_and_standard_error(self):
        self.assertEqual(pass_at_k(5,2,3),.9)
        self.assertEqual(pass_hat_k(5,2,3),0)
        self.assertAlmostEqual(mean([1,3,5]),3)
        self.assertAlmostEqual(standard_error([1,3,5]),2/(3**.5))
        for values in ((0,0,1),(5,6,1),(5,2,6),(5,2,0),(5,-1,1)):
            with self.assertRaises(ValueError):pass_at_k(*values)
        with self.assertRaises(ValueError):standard_error([1])

    def test_zero_variance_fallback_is_one_eighth_not_one(self):
        result=experiment.pilot_numbers(self.rows(),list('abcdefgh'),.25)
        self.assertEqual(result['s_a'],0)
        self.assertEqual(result['effective_s_a'],.125)
        self.assertEqual(result['n_needed'],4)
        self.assertEqual(result['pilot_cost_per_sweep_usd'],2)
        self.assertNotIn('difference',result)
        self.assertNotIn('mean',result)
        self.assertEqual(result['price_usd'],16)

    def test_duplicate_or_missing_matrix_rejected(self):
        rows=self.rows()['A']
        for bad in (rows[:-1],rows+[rows[0]],rows[1:]+[dict(rows[0],task='unexpected')]):
            with self.assertRaises(validation.InputError):experiment.matrix(bad,list('abcdefgh'),range(1,4))
        with self.assertRaises(ValueError):report_07.sweep_values(rows+[rows[0]])

    def test_sweep_statistics_use_sweeps_and_combinatorial_pass_hat(self):
        rows=self.rows()['A']
        for r in rows:r['passed']=r['sweep']<3;r['measure']=r['sweep']
        result=report_07.arm_numbers(rows,k=3)
        self.assertEqual(result['measure']['mean'],2)
        self.assertEqual(result['measure']['sd'],1)
        self.assertEqual(result['pass_at_k'],1)
        self.assertEqual(result['pass_hat_k'],0)
        self.assertEqual(result['cost_per_sweep_usd'],2)


class HumanBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        out=self.root/'fixtures/judge/outputs';out.mkdir(parents=True)
        ids=[f'j{i:02}' for i in range(1,61)]
        self.parts={'examples':ids[:8],'tuning':ids[8:34],'test':ids[34:]}
        for identifier in ids:
            (out/f'{identifier}.json').write_text(json.dumps({'id':identifier,'system':'test-system',
                'issue':{'title':'Synthetic fixture','body':'Synthetic issue'},'evidence':[],
                'comment':f'Synthetic comment {identifier}','versions':{'list':'Synthetic list','long':'Synthetic long'}}))
        self.label_path=self.root/'eval/labels/labels.csv';self.label_path.parent.mkdir(parents=True)
        with self.label_path.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=['id','label','reason']);writer.writeheader()
            for n,i in enumerate(ids):writer.writerow({'id':i,'label':'pass' if n%2 else 'fail',
                'reason':'HELD_OUT_LABEL_SECRET' if i in self.parts['test'] else 'Synthetic development reason'})
        (self.label_path.parent/'split.yaml').write_text(yaml.safe_dump(self.parts))
        (self.root/'eval/judge').mkdir()
        self.criterion=self.root/'eval/judge/criterion.md';self.criterion.write_text('Synthetic criterion used only inside this test.')
        json_write(self.root/'eval/judge/human_criterion.json',{'human_confirmed':True,'sha256':validation.sha(self.criterion)})
        (self.root/'prompts').mkdir();(self.root/'prompts/judge.md').write_text('Synthetic generic judge instructions.')
        for p in ('settings.yaml','pricing.yaml','eval/judge.py','eval/validation_07.py'):
            shutil.copy2(ROOT/p,self.root/p)

    def test_complete_human_labels_validated_without_substantive_edits(self):
        before=self.label_path.read_bytes()
        self.assertEqual(len(validation.labels(self.root)),60)
        self.assertEqual(validation.split(self.root),self.parts)
        self.assertEqual(before,self.label_path.read_bytes())

    def test_duplicates_unknown_ids_and_incomplete_human_labels_rejected(self):
        before=self.label_path.read_text()
        for suffix in ('j01,pass,Synthetic duplicate\n','j99,fail,Synthetic unknown\n'):
            self.label_path.write_text(before+suffix)
            with self.assertRaises(validation.InputError):validation.labels(self.root)
        self.label_path.write_text('id,label,reason\n')
        with self.assertRaisesRegex(validation.InputError,'0/60'):validation.labels(self.root)
        self.assertEqual(validation.labels(self.root,complete=False),{})

    def test_prompt_uses_only_example_labels(self):
        prompt=judge.make_prompt(self.root)
        self.assertIn('Synthetic development reason',prompt)
        self.assertNotIn('HELD_OUT_LABEL_SECRET',prompt)
        for i in self.parts['test']:self.assertNotIn(f'"id": "{i}"',prompt)
        examples=validation.labels(self.root,allowed=set(self.parts['examples']))
        self.assertEqual(set(examples),set(self.parts['examples']))

    def test_criterion_revision_invalidates_confirmation(self):
        self.criterion.write_text('A different synthetic criterion revision.')
        with self.assertRaisesRegex(validation.InputError,'authorship confirmation'):validation.criterion(self.root)

    def test_no_label_saved_without_human_confirmation_and_no_overwrite(self):
        self.label_path.write_text('id,label,reason\n')
        with patch.multiple(human_judge_cli,ROOT=self.root,LABELS=self.label_path):
            with self.assertRaises(ValueError):human_judge_cli.save_label('j01','pass','Synthetic reason',confirmed=False)
            self.assertEqual(human_judge_cli.save_label('j01','pass','Synthetic reason',confirmed=True),1)
            before=self.label_path.read_bytes()
            with self.assertRaises(ValueError):human_judge_cli.save_label('j01','fail','Other synthetic reason',confirmed=True)
            self.assertEqual(before,self.label_path.read_bytes())
            self.assertEqual(len(list((self.label_path.parent/'backups').glob('*.csv'))),1)

    def test_frozen_configuration_detects_edits(self):
        with patch.object(validation,'committed',return_value='synthetic-test-commit'), patch.object(validation,'git',return_value='synthetic-test-commit'):
            judge.freeze(self.root)
            judge.check_frozen(self.root)
            (self.root/'prompts/judge.md').write_text('Changed synthetic prompt')
            with self.assertRaisesRegex(validation.InputError,'changed after freezing'):judge.check_frozen(self.root)

    def test_scripted_partial_verdicts_resume_without_overwriting(self):
        calls=[]
        @contextmanager
        def fake_session(name,**kwargs):
            def create(**kwargs):
                calls.append(kwargs)
                return SimpleNamespace(text='{"reasoning":"Synthetic test evidence","answer":"Pass"}',model='synthetic-model')
            yield SimpleNamespace(id='synthetic-session',client=SimpleNamespace(create=create,total_tokens=0),
                                  trace=SimpleNamespace(model_call=lambda *a,**k:None))
        output=self.root/'eval/judge/verdicts/test-1_scripted.jsonl';output.parent.mkdir()
        first={'id':self.parts['test'][0],'answer':'fail','reasoning':'Preserved synthetic earlier verdict',
               'session':'prior-synthetic-session','model':'synthetic-model'}
        original=json.dumps(first)+'\n';output.write_text(original)
        count=judge.run_verdicts('test',1,root=self.root,scripted=True,session_factory=fake_session)
        self.assertEqual(count,26);self.assertEqual(len(calls),25)
        self.assertTrue(output.read_text().startswith(original))
        judge.run_verdicts('test',1,root=self.root,scripted=True,session_factory=fake_session)
        self.assertEqual(len(calls),25)
        self.assertNotIn('HELD_OUT_LABEL_SECRET',json.dumps(calls))

    def test_coin_boundary_and_minimum_bootstrap_samples(self):
        with self.assertRaises(judge.CoinJudge):judge.correct(.5,.6,.5)
        with self.assertRaises(ValueError):judge.bootstrap({}, {},.5,resamples=1999)

    def test_prompt_revision_cannot_change_held_out_test_configuration(self):
        with self.assertRaisesRegex(validation.InputError,'only for examples/tuning'):
            judge.run_verdicts('test',1,root=self.root,revision='tuned-on-test')


class ExportTests(unittest.TestCase):
    def test_real_scripted_separation_and_tracker_root_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);tasks=root/'eval/golden/v1/tasks';tasks.mkdir(parents=True)
            shutil.copy2(ROOT/'eval/golden/v1/tasks/g01.yaml',tasks/'g01.yaml')
            subset=root/'eval/subsets';subset.mkdir();(subset/'claim.txt').write_text('g01\n')
            runs=root/'runs';runs.mkdir()
            def trace(rid,backend,sweep):
                data=[{'type':'run_start','run_id':rid,'lab':'07','way':'planned','backend':backend,'task':'g01','sweep':sweep,
                       'started_at':'2020-01-01T00:00:00Z','switches':{}},
                      {'type':'end','terminal_reason':'model_stopped'},
                      {'type':'run_end','elapsed_s':7,'totals':{'total_tokens':123,'cost_usd':.5}}]
                (runs/f'{rid}.jsonl').write_text('\n'.join(json.dumps(e) for e in data)+'\n')
            trace('synthetic-real','openai-compatible',1)
            trace('synthetic-free','harness.scripted:ScriptedTriage',2)
            trace('synthetic-unknown','unsupported-test-backend',3)
            rows=build_rows('A','planned','plan',root=root)
            self.assertEqual([r['run_id'] for r in rows],['synthetic-real'])
            self.assertEqual(rows[0]['tokens'],123);self.assertEqual(rows[0]['cost_usd'],.5)
            self.assertFalse(rows[0]['passed'])
            free=build_rows('A','planned','plan',root=root,scripted=True)
            self.assertEqual([r['run_id'] for r in free],['synthetic-free'])
            trace('synthetic-duplicate','openai-compatible',1)
            with self.assertRaisesRegex(ValueError,'Duplicate'):build_rows('A','planned','plan',root=root)


class ProvenanceGateTests(unittest.TestCase):
    def test_fourth_sweep_blocked_before_any_model_command(self):
        with patch.object(experiment,'preflight',return_value={}), \
             patch.object(experiment,'design',return_value={'arm_a':{'way':'planned'},'arm_b':{'way':'agent'}}), \
             patch.object(validation,'committed',side_effect=validation.InputError('Threshold not committed')), \
             patch.object(experiment.subprocess,'run') as command:
            with self.assertRaisesRegex(validation.InputError,'not committed'):experiment.run_stage('finish')
            command.assert_not_called()

    def test_unfinished_fourth_sweep_prevents_retrospective_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'eval/subsets').mkdir(parents=True);(root/'runs').mkdir()
            (root/'eval/experiment_plan.yaml').write_text(yaml.safe_dump({'arm_a':{'way':'planned'},'arm_b':{'way':'agent'}}))
            (root/'eval/subsets/claim.txt').write_text('g01\n')
            (root/'runs/synthetic-unfinished.jsonl').write_text(json.dumps({'type':'run_start','backend':'openai-compatible',
                'task':'g01','way':'agent','sweep':4})+'\n')
            with patch.object(experiment,'export') as exporter:
                with self.assertRaisesRegex(validation.InputError,'already started'):experiment.threshold(root)
                exporter.assert_not_called()

    def test_first_failure_references_must_match_actual_failed_traces(self):
        from eval.failure_review_07 import validate_annotations
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'runs').mkdir()
            (root/'runs/synthetic.jsonl').write_text(json.dumps({'type':'tool_call','name':'issues_read','step':0})+'\n')
            failures=[{'run_id':'synthetic','arm':'A'}]
            row={'run_id':'synthetic','arm':'A','last_good':'issues_read','first_wrong':'stop','cause':'structural'}
            self.assertEqual(validate_annotations([row],failures,root),[row])
            for bad in ([],[dict(row,arm='B')],[dict(row,first_wrong='pulls_open')],[row,row]):
                with self.assertRaises(ValueError):validate_annotations(bad,failures,root)


if __name__=='__main__':unittest.main()
