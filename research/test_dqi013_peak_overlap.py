"""Experiment 013: exact source-event replay with explicit native evidence gaps."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_dqi_peak_overlap import replay_lifetimes
from profile_dqi_source_allocations import audit_instance


def event(kind, slots, names, live, stage=None):
    return {
        "kind":kind,"physical_slots":slots,
        "source_occurrences":names,"stage":stage or [],
        "source_live_count":live,
    }


class PeakOverlapTests(unittest.TestCase):
    def source_fixture(self):
        return {
            "experiment":"011","n":2,"m":2,"degree":1,
            "num_qubits_compiled":5,"named_syndrome_qubits":2,
            "max_explicit_live":5,
            "native_helper_qubits_released_without_observed_birth":0,
            "explicit_source_stage_allocation_counts":{"(root)":1},
            "explicit_events":[
                event("named_input",[0,1],["q0@1","q1@1"],2),
                event("temporary",[2],["q2@1"],3),
                event("temporary",[3,4],["q3@1","q4@1"],5,
                      ["forward_eea","eea_step"]),
                event("release",[3,4],["q3@1","q4@1"],3,
                      ["forward_eea","eea_step"]),
                event("release",[2],["q2@1"],2),
            ],
        }

    def test_peak_preserves_three_witnessed_source_categories(self):
        report=replay_lifetimes(self.source_fixture())
        self.assertEqual(report["compiled_physical_Q"],5)
        self.assertEqual(report["compiled_Q_squared"],25)
        self.assertEqual(report["first_peak_root_or_named_count"],3)
        self.assertEqual(report["first_peak_other_workspace_count"],2)
        self.assertEqual(report["first_peak_trigger_stage"],"forward_eea/eea_step")
        self.assertEqual(report["first_peak_event_index"],2)
        self.assertEqual(report["observed_source_live_peak"],5)
        self.assertTrue(report["observed_peak_equals_compiled_Q"])
        self.assertEqual(report["unobserved_peak_qubit_gap"],0)
        self.assertEqual(report["last_observed_source_live_count"],2)

    def test_replay_rejects_corrupt_retained_count(self):
        f=self.source_fixture()
        f["explicit_events"][1]["source_live_count"]=4
        with self.assertRaises(AssertionError):
            replay_lifetimes(f)

    def test_replay_rejects_premature_source_slot_reuse(self):
        f=self.source_fixture()
        f["explicit_events"].insert(2,event("temporary",[2],["q2@2"],4))
        with self.assertRaises(AssertionError):
            replay_lifetimes(f)

    def test_original_small_dqi_explicit_gap_is_retained(self):
        from profile_dqi_source_allocations import audit_instance
        source=audit_instance(6,15,6)
        report=replay_lifetimes(source)
        self.assertEqual(report["compiled_physical_Q"],180)
        self.assertEqual(report["observed_source_live_peak"],177)
        self.assertEqual(report["unobserved_peak_qubit_gap"],3)
        self.assertFalse(report["observed_peak_equals_compiled_Q"])
        self.assertEqual(report["last_observed_source_live_count"],36)
        self.assertEqual(
            report["first_peak_root_or_named_count"]+
            report["first_peak_other_workspace_count"],177)


if __name__=="__main__":
    unittest.main()
