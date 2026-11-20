"""Constructive Q^2 is an indexed union of one row and column per stage."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from constructive_qubit_square import (
    construct_rows, indexed_qubit_penalty, occurrence_pairs,
)


class ConstructiveSquareTests(unittest.TestCase):
    def test_all_square_cells_unique_and_witnessed(self):
        for Q in range(1, 13):
            witnesses = list(occurrence_pairs(Q))
            cells = [(r,c) for r,c,_,_ in witnesses]
            self.assertEqual(len(cells), Q * Q)
            self.assertEqual(len(set(cells)), Q * Q)
            self.assertEqual(set(cells), {(r,c) for r in range(1,Q+1)
                                               for c in range(1,Q+1)})
            for r, c, stage, _ in witnesses:
                self.assertEqual(stage, max(r,c))

    def test_stage_sources_distinguished(self):
        for i, row in enumerate(construct_rows(64), start=1):
            self.assertEqual(row["stage_index"], i)
            self.assertEqual(row["row_source"]["new_positions"], i-1)
            self.assertEqual(row["column_source"]["new_positions"], i-1)
            self.assertEqual(row["corner_source"]["new_positions"], 1)
            self.assertEqual(row["new_positions"], 2*i-1)
            self.assertEqual(row["cumulative_positions"], i*i)

    def test_benchmark_1893_source_rows(self):
        audit = indexed_qubit_penalty(1893,1)
        self.assertEqual(audit["Q_squared_scored_factor"], 3583449)
        self.assertEqual(audit["marginal_terminal_stage"], 3785)
        self.assertEqual(audit["Q_squared_after_recompile"], 3579664)
        self.assertEqual(audit["scored_factor_reduction"], 3785)
        self.assertEqual(len(audit["indexed_rows"]),1893)

    def test_many_qubits_recompiled(self):
        for Q in range(1,33):
            for k in range(Q+1):
                result=indexed_qubit_penalty(Q,k)
                self.assertEqual(result["scored_factor_reduction"],k*(2*Q-k))
                self.assertEqual(result["Q_squared_after_recompile"],(Q-k)**2)

    def test_reject_bad_counts(self):
        for Q in (-1,1.2,True):
            with self.assertRaises(ValueError):
                construct_rows(Q)
        for k in (-1,4,1.2,True):
            with self.assertRaises(ValueError):
                indexed_qubit_penalty(3,k)


if __name__ == "__main__":
    unittest.main()
