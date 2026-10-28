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

from allis_delivery.core import Dataset, ModelBundle, predict_models, validate_candidates
from allis_delivery.evaluation import expected_best, independent_curve, ranks, replay_selection

ROOT = Path(__file__).resolve().parents[1]


class PairPredictor:
    def predict(self, x):
        return x[:, 6]  # first coordinate of a-b, for point inputs of width three


class DirectPredictor:
    def predict(self, x):
        return x[:, 0]


class PolicyTests(unittest.TestCase):
    def test_exact_tie_expectation_against_subsets(self):
        gold = np.array([0.2, 1.8, 1.1, 0.5, 0.9, 1.3, 0.7])
        for ranking in ([1] * 7, [1, 1, 2, 2, 2, 3, 4], [1, 2, 3, 4, 5, 6, 7]):
            np.testing.assert_allclose(expected_best(ranking, gold), independent_curve(ranking, gold), atol=1e-12, rtol=0)

    def test_midrank_and_equal_weights(self):
        r = ranks([3, 1, 3, 2], [1, 4, 3, 2])
        np.testing.assert_array_equal(r['paired_ET'], [1.5, 4, 1.5, 3])
        np.testing.assert_array_equal(r['equal_rank'], [2.75, 2.5, 1.75, 3])

    def test_tied_replay_never_exceeds_budget(self):
        for budget in range(1, 6):
            selected = replay_selection([1] * 18, budget, 42)
            self.assertEqual(len(selected), budget)
            self.assertEqual(len(set(selected)), budget)
            np.testing.assert_array_equal(selected, replay_selection([1] * 18, budget, 42))

    def test_feature_only_prediction_has_no_label_access(self):
        candidate = {'features': np.array([[2, 0], [3, 0]], dtype=np.float32),
                     'dose_pmol': np.tile(np.arange(1, 41, dtype=np.float32), (2, 1)),
                     'ids': np.array(['test0', 'test1']), 'feature_names': np.array(['a', 'b'])}
        model = ModelBundle(1, 'tiny', np.array([0, 1]), ['a', 'b'], ['train0', 'train1'],
                            PairPredictor(), DirectPredictor(),
                            np.array([[0, 0, 1], [1, 0, 1]], dtype=np.float32), np.array([0., 1.]))
        with patch.object(Dataset, 'responses', side_effect=AssertionError('Prediction must not read labels')):
            result = predict_models(model, candidate)
        np.testing.assert_allclose(result['paired_q'], [2, 3])
        np.testing.assert_allclose(result['direct_q'], [2, 3])
        contaminated = dict(candidate, gold_Q=np.array([8, 9]))
        with self.assertRaisesRegex(ValueError, 'no labels'):
            validate_candidates(contaminated, ['a', 'b'])
        wrong = dict(candidate, feature_names=np.array(['b', 'a']))
        with self.assertRaisesRegex(ValueError, 'order'):
            validate_candidates(wrong, ['a', 'b'])
        overlapping = dict(candidate, ids=np.array(['train0', 'test1']))
        with self.assertRaisesRegex(ValueError, 'overlap'):
            predict_models(model, overlapping)


class PortableIntegrationTests(unittest.TestCase):
    def test_one_click_without_research_tree_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory(prefix='allis-portable-') as temp:
            dest = Path(temp)
            shutil.copytree(ROOT / 'allis_delivery', dest / 'allis_delivery', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copy2(ROOT / 'run_allis.sh', dest / 'run_allis.sh')
            env = dict(os.environ, ALLIS_PYTHON=sys.executable)
            result = subprocess.run(['bash', str(dest / 'run_allis.sh'), 'run', '--mode', 'cached', '--output', str(dest / 'out')],
                                    env=env, capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            out = dest / 'out'
            receipt = json.loads((out / 'verification.json').read_text())
            self.assertTrue(receipt['pass'])
            self.assertEqual(receipt['new_fits'], 0)
            self.assertEqual(receipt['scored_rows'], 90)
            metrics = json.loads((out / 'evaluation/metrics.json').read_text())
            fused = next(r for r in metrics['summary'] if r['scope'] == 'all' and r['method'] == 'equal_rank')
            self.assertAlmostEqual(fused['AUR'], 0.08180303167138003, places=12)
            hidden = json.loads((out / 'replays/r0_f0-equal_rank-hidden.json').read_text())
            self.assertEqual(hidden['selected_count'], hidden['budget'])
            self.assertNotIn('candidate_oracle_Q', hidden)
            self.assertFalse(any('archived_measured_Q' in r for r in hidden['recommendations']))
            altered = out / 'predictions/r0_f0.json'
            altered.write_text(altered.read_text() + ' ')
            verify = subprocess.run(['bash', str(dest / 'run_allis.sh'), 'verify', '--run-dir', str(out)],
                                    env=env, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(verify.returncode, 0)
            self.assertIn('Integrity check failed', verify.stderr)
            duplicate = subprocess.run(['bash', str(dest / 'run_allis.sh'), 'prepare', '--output', str(out)],
                                       env=env, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn('not empty', duplicate.stderr)


if __name__ == '__main__':
    unittest.main()
