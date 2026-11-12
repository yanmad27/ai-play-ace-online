import tempfile
import unittest
from pathlib import Path

import numpy as np

from ace_pilot.learning import History, train


class LearningTests(unittest.TestCase):
    def test_temporal_history_preserves_order(self):
        history = History()
        black = np.zeros((54, 96, 3), dtype=np.uint8)
        white = np.full_like(black, 255)
        history.push(black)
        result = history.push(white).reshape(3, -1)
        np.testing.assert_array_equal(result[:2], 0)
        np.testing.assert_array_equal(result[2], 1)

    def test_validation_session_is_never_trained_on(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in [('01', 0), ('02', 1)]:
                session = root / 'sessions' / name
                session.mkdir(parents=True)
                np.savez_compressed(session / 'samples.npz', x=np.zeros((60, 8)), y=np.full((60, 14), value))
            report = train(root)
            self.assertEqual(report['training_sessions'], ['01'])
            self.assertEqual(report['validation_session'], '02')
            self.assertEqual(report['mouse_normalized_mae'], 1)
            self.assertFalse((root / 'active.joblib').exists())

    def test_training_requires_independent_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                train(directory)
