"""Experiment 004 rescaling invariants, verified independently of chemistry metrics."""
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "verifiers"), str(Path(__file__).resolve().parents[1] / "kickmix")]
from scripts.sweep_chem_angle_precision import rescale_words


class WordRescaleTests(unittest.TestCase):
    def test_identity_at_source_width(self):
        x = np.array([[0, 1, 2047, 4095]], dtype=np.int64)
        for rule in ("floor", "nearest_even", "nearest_up"):
            np.testing.assert_array_equal(x, rescale_words(x, 12, 12, rule))

    def test_exact_even_halving(self):
        values = np.arange(0, 4096, 2, dtype=np.int64).reshape(1, -1)
        np.testing.assert_array_equal(values // 2, rescale_words(values, 12, 11))

    def test_round_half_to_even(self):
        x = np.array([[1, 3, 5, 7, 4095]], dtype=np.int64)
        self.assertEqual(rescale_words(x, 12, 11, "nearest_even").tolist(),
                         [[0, 2, 2, 4, 0]])
        self.assertEqual(rescale_words(x, 12, 11, "floor").tolist(),
                         [[0, 1, 2, 3, 2047]])
        self.assertEqual(rescale_words(x, 12, 11, "nearest_up").tolist(),
                         [[1, 2, 3, 4, 0]])

    def test_quarter_turn_equality(self):
        x = np.array([[0, 1024, 2048, 3072]], dtype=np.int64)
        y = rescale_words(x, 12, 10, "nearest_even")
        self.assertEqual(y.tolist(), [[0, 256, 512, 768]])

    def test_malformed_source_rejected(self):
        with self.assertRaises(ValueError):
            rescale_words(np.array([[-1]]), 12, 11)
        with self.assertRaises(ValueError):
            rescale_words(np.array([[4096]]), 12, 11)
        with self.assertRaises(ValueError):
            rescale_words(np.array([[1]]), 12, 13)


if __name__ == "__main__":
    unittest.main()
