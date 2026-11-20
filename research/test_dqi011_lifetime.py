"""DQI source allocation identities must preserve actual released generations."""
from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from profile_dqi_source_allocations import AllocatorLedger, audit_instance


class DqiSourceAllocatorTests(unittest.TestCase):
    def test_released_physical_slots_get_distinct_occurrences(self):
        b=AllocatorLedger()
        first=b.alloc_qubits(2)
        old_ids=[int(q.id) for q in first]
        old_occ=[b.live[i] for i in old_ids]
        b.free(first)
        second=b.alloc_qubits(2)
        new_ids=[int(q.id) for q in second]
        new_occ=[b.live[i] for i in new_ids]
        for index in set(old_ids).intersection(new_ids):
            self.assertEqual(b.generations[index],2)
            self.assertNotEqual(old_occ[old_ids.index(index)],new_occ[new_ids.index(index)])
        b.free(second)
        self.assertEqual(b.live,{})
        self.assertEqual(b.release_counts["quantum"],4)
        self.assertEqual(b.allocation_counts["temporary"],4)

    def test_dqi_original_small_builder_unchanged(self):
        recorded=audit_instance(6,15,6)
        self.assertEqual(recorded["num_qubits_compiled"],180)
        self.assertEqual(recorded["static_toffoli_like"],51991)
        self.assertEqual(recorded["named_syndrome_qubits"],36)
        self.assertEqual(recorded["non_syndrome_peak_slots"],144)
        self.assertTrue(all(recorded["verified"].values()))
        self.assertTrue(recorded["explicit_events"])

    def test_marks_preserve_independent_stage_identities(self):
        recorded=audit_instance(6,15,6)
        top={tuple(item["stage"])[:1] for item in recorded["mark_entries"]}
        for name in ("initial_shift","forward_eea","chien_forney_mbuc",
                     "reverse_eea","uncompute_initial_shift"):
            self.assertIn((name,),top)
        self.assertGreater(recorded["temporary_occurrences_created"],
                           recorded["non_syndrome_peak_slots"])

if __name__=="__main__":
    unittest.main()
