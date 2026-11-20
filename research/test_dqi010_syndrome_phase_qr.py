"""Exact toy finite-field equality controls for direct syndrome phase QR."""
import sys
from pathlib import Path
import random
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import kickmix as km
from dqi010_syndrome_phase_qr import (
    dual_masks, x_positions, syndrome_phase, field_trace,
)


class DirectSyndromePhaseTests(unittest.TestCase):
    def test_exhaustive_all_single_error_values_and_masks(self):
        gf = km.GF2Field(3)
        xs = x_positions(gf)
        duals = dual_masks(gf)
        checks = 0
        for position in range(len(xs)):
            for error_value in range(1, 8):
                for mask in range(8):
                    mbuc = [0] * len(xs)
                    mbuc[position] = mask
                    result = syndrome_phase(
                        gf, {position: error_value}, mbuc, duals, xs)
                    self.assertEqual(result["phase_direct"],
                                     result["phase_remainder"])
                    checks += 1
        self.assertEqual(checks, 392)

    def test_sparse_two_error_random_masks(self):
        gf = km.GF2Field(4)
        xs = x_positions(gf)
        duals = dual_masks(gf)
        rng = random.Random(20261120)
        for trial in range(150):
            indices = rng.sample(range(len(xs)), 2)
            e = {j: rng.randrange(1, 16) for j in indices}
            masks = [rng.randrange(16) for _ in xs]
            checked = syndrome_phase(gf, e, masks, duals, xs)
            self.assertEqual(checked["phase_direct"], checked["phase_remainder"])

    def test_no_error_has_no_phase(self):
        gf = km.GF2Field(4)
        xs = x_positions(gf)
        duals = dual_masks(gf)
        result = syndrome_phase(gf, {}, [15] * len(xs), duals, xs)
        self.assertEqual((result["phase_direct"], result["phase_remainder"]), (0, 0))

    def test_trace_dual_complete(self):
        gf = km.GF2Field(4)
        duals = dual_masks(gf)
        for value in range(16):
            for mask in range(16):
                self.assertEqual(
                    field_trace(gf, gf.mul(duals[mask], value)),
                    int((mask & value).bit_count() & 1),
                )


if __name__ == "__main__":
    unittest.main()
