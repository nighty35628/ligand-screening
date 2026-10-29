"""No-training acceptance for frozen public research cases and result provenance."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from amadeus import workflow

class SnapshotTest(unittest.TestCase):
    def test_new_cases_without_training(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(workflow,'HOME',Path(tmp)), patch.object(workflow,'DB',Path(tmp)/'test.sqlite3'), patch.object(workflow,'train_table',side_effect=AssertionError('Snapshot must not train')), patch('subprocess.Popen',side_effect=AssertionError('Snapshot must not spawn training')):
            workflow.init(None,recover=False)
            for case in ('double_perovskites_gap','citrine_thermal_conductivity'):
                with self.subTest(case=case):
                    cfg=workflow.MATERIAL_CASES[case]
                    fixture=json.loads((workflow.ROOT/'amadeus/web'/cfg['snapshot']).read_text())
                    original=json.loads((workflow.ROOT/'results/unprepared-20261029'/case/'result.json').read_text())
                    p=workflow.create({'title':cfg['title'],'goal':cfg['goal']})
                    workflow.load_material_example(p,case,replay=True)
                    self.assertEqual(p['analysis']['candidates'],original['candidates'])
                    self.assertEqual(p['analysis']['order'],original['order'])
                    self.assertNotIn(cfg['target'],p['datasets']['candidates']['columns'])
                    self.assertFalse(p['measurements'])
                    self.assertNotIn('oracle',workflow.visible(p))
                    first=p['selected'][:]
                    workflow.save_plan(p)
                    workflow.historical_results(p);workflow.historical_results(p)
                    self.assertEqual(len(p['measurements']),3)
                    for m in p['measurements']:
                        self.assertEqual(m['unit'],cfg['unit'])
                        self.assertEqual(m['value'],fixture['oracle'][m['candidate_id']])
                        self.assertEqual(m['source'],'公开'+cfg['label'])
                    workflow.next_round(p)
                    self.assertFalse(set(first)&set(p['selected']))
                    workflow.save(p);reopened=workflow.load(p['id'])
                    self.assertEqual(reopened['analysis'],p['analysis'])
                    report=workflow.export_report(p).decode()
                    self.assertIn(cfg['title'],report);self.assertIn(cfg['label'],report)
                    self.assertIn('combined / ET' if case=='double_perovskites_gap' else 'XGBoost',report)

if __name__=='__main__': unittest.main()
