"""Independent deterministic checks of source-vector Givens angle projection."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from chem007_vector_projection import (
    decode_vectors, quotient_remainder_nearest, reverse_source_projection,
)


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        # Every edge adds a new vertex from an already participating vertex.
        self.tree = np.array([[0, 1], [0, 2], [1, 3], [2, 4]], dtype=np.int64)

    def test_identity_exact_source_angle(self):
        source = np.array([[0, 1024, 2048, 3072], [2, 4, 6, 8]], dtype=np.int64)
        coarse = quotient_remainder_nearest(source, 12, 11)
        fine = decode_vectors(source, self.tree, 12)
        projected = decode_vectors(coarse, self.tree, 11)
        np.testing.assert_allclose(projected, fine, atol=1e-12)

    def test_rounding_uses_quotient_and_remainder(self):
        words = np.array([[1, 3, 5, 7, 4095]], dtype=np.int64)
        self.assertEqual(quotient_remainder_nearest(words, 12, 11).tolist(),
                         [[0, 2, 2, 4, 0]])

    def test_vector_loss_nonincrease_for_random_rows(self):
        rng = np.random.default_rng(20261120)
        source = rng.integers(0, 4096, size=(512, len(self.tree)), dtype=np.int64)
        before = quotient_remainder_nearest(source, 12, 11)
        after, report = reverse_source_projection(source, self.tree, 12, 11, 3)
        target_vec = decode_vectors(source, self.tree, 12)
        original_vec = decode_vectors(before, self.tree, 11)
        optimized_vec = decode_vectors(after, self.tree, 11)
        loss0 = np.sum((original_vec - target_vec) ** 2, axis=1)
        loss1 = np.sum((optimized_vec - target_vec) ** 2, axis=1)
        self.assertTrue(np.all(loss1 <= loss0 + 2e-12))
        self.assertLessEqual(report["final_squared_error_total"],
                             report["initial_squared_error_total"] + 1e-10)

    def test_preserves_angular_period(self):
        source = np.array([[4095, 0, 0, 0]], dtype=np.int64)
        projected, _ = reverse_source_projection(source, self.tree, 12, 11, 2)
        self.assertTrue(np.all(projected >= 0))
        self.assertTrue(np.all(projected < 2048))

    def test_reject_bad_width(self):
        with self.assertRaises(ValueError):
            reverse_source_projection(np.ones((1, 4), dtype=np.int64),
                                      self.tree, 10, 11, 2)


if __name__ == "__main__":
    unittest.main()
