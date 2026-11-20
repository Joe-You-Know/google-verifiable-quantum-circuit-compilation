"""Exact source-to-scored-Q row mapping tests with absent native provenance."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from join_dqi_square_source import join_source_to_square
from profile_dqi_source_allocations import audit_instance


class SourceSquareTests(unittest.TestCase):
    def test_known_and_unobserved_source_slots(self):
        receipt={"experiment":"011","num_qubits_compiled":3,
                 "explicit_events":[
                     {"kind":"named_input","physical_slots":[0,1],
                      "source_occurrences":["q0@gen1","q1@gen1"],
                      "stage":[],"label":"S0"},
                     {"kind":"release","physical_slots":[0],
                      "source_occurrences":["q0@gen1"],"stage":[]},
                     {"kind":"temporary","physical_slots":[0],
                      "source_occurrences":["q0@gen2"],
                      "stage":["forney_step"],"label":"temp"},
                 ]}
        result=join_source_to_square(receipt)
        self.assertEqual(result["square_factor"],9)
        self.assertEqual(result["one_qubit_marginal_if_validly_recompiled"],5)
        self.assertEqual(result["rows_without_observed_source_occurrences"],1)
        self.assertEqual(result["slots_reused_by_source"],1)
        self.assertEqual([r["new_square_positions"] for r in result["indexed_rows"]],[1,3,5])
        self.assertEqual(result["indexed_rows"][2]["source_allocation_status"],
                         "native_or_unobserved")

    def test_original_small_decoder_physical_slots(self):
        source=audit_instance(6,15,6)
        result=join_source_to_square(source)
        self.assertEqual(result["scored_Q"],180)
        self.assertEqual(result["square_factor"],32400)
        self.assertEqual(result["one_qubit_marginal_if_validly_recompiled"],359)
        self.assertEqual(result["slots_reused_by_source"],36)
        self.assertEqual(result["rows_without_observed_source_occurrences"],3)
        self.assertEqual(len(result["indexed_rows"]),180)

    def test_bad_source_slot_rejected(self):
        source={"num_qubits_compiled":2,"explicit_events":[
            {"kind":"temporary","physical_slots":[2],
             "source_occurrences":["q2@gen1"]}]}
        with self.assertRaises(ValueError):
            join_source_to_square(source)


if __name__=="__main__":
    unittest.main()
