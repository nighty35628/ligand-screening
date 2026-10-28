import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from allis_benchmark.core import RFBundle, predict_rf
from allis_delivery.core import Dataset

ROOT = Path(__file__).resolve().parents[1]


class DifferenceTree:
    def predict(self, x):
        return x[:, x.shape[1] // 3 * 2]


class DifferenceForest(DifferenceTree):
    estimators_ = [DifferenceTree(), DifferenceTree()]


class BaselineTests(unittest.TestCase):
    def test_reference_reconstruction_and_no_label_access(self):
        # A known affine function: reference_y plus x_query-x_reference must recover x_query.
        model=RFBundle(1,'test',np.array([0]),['a','unused'],['history'],DifferenceForest(),
                       np.array([[0.,1.],[1.,2.]],dtype=np.float32),np.array([0.,1.]))
        candidates={'features':np.array([[2.,99.],[3.,88.]],dtype=np.float32),
                    'dose_pmol':np.tile(np.arange(1,41),(2,1)),
                    'ids':np.array(['new1','new2']),'feature_names':np.array(['a','unused'])}
        with patch.object(Dataset,'responses',side_effect=AssertionError('Oracle access')):
            result=predict_rf(model,candidates)
        np.testing.assert_allclose(result['rf_curves'],np.repeat([[2.],[3.]],40,axis=1))
        np.testing.assert_allclose(result['rf_q'],[2.,3.])
        np.testing.assert_allclose(result['rf_upper_q'],[2.,3.])
        with self.assertRaisesRegex(ValueError,'no labels'):
            predict_rf(model,dict(candidates,gold_Q=np.array([2,3])))
        with self.assertRaisesRegex(ValueError,'overlap'):
            predict_rf(model,dict(candidates,ids=np.array(['history','new2'])))

    def test_portable_six_method_run_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory(prefix='ligand-benchmark-') as tmp:
            dest=Path(tmp)
            for package in ('allis_delivery','allis_benchmark'):
                shutil.copytree(ROOT/package,dest/package,ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copy2(ROOT/'run_project.sh',dest/'run_project.sh')
            env=dict(os.environ,ALLIS_PYTHON=sys.executable)
            cmd=['bash',str(dest/'run_project.sh')]
            proc=subprocess.run(cmd+['run','--output',str(dest/'out')],env=env,capture_output=True,text=True,timeout=90)
            self.assertEqual(proc.returncode,0,proc.stderr)
            report=json.loads((dest/'out/verification.json').read_text())
            self.assertEqual(report['rows'],90)
            self.assertTrue(report['pass'])
            self.assertEqual(json.loads((dest/'out/execution.json').read_text())['new_fits'],0)
            altered=dest/'out/predictions/r0_f0.json';altered.write_text(altered.read_text()+' ')
            proc=subprocess.run(cmd+['verify','--run-dir',str(dest/'out')],env=env,capture_output=True,text=True,timeout=60)
            self.assertNotEqual(proc.returncode,0)
            self.assertIn('Integrity check failed',proc.stderr)
            proc=subprocess.run(cmd+['run','--output',str(dest/'out')],env=env,capture_output=True,text=True,timeout=60)
            self.assertNotEqual(proc.returncode,0)
            self.assertIn('empty/new',proc.stderr)


if __name__=='__main__':unittest.main()
