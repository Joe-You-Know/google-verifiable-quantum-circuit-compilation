#!/usr/bin/env python3
"""Experiment 013: reconstruct actual overlapping source qubit lifetimes.

Input: JSON receipt from profile_dqi_source_allocations.py.  Replay every
indexed allocation and release in event order, independently validating each
occurrence identity and remaining source-live count. Identify first and last
events at the observed source-live maximum and preserve a provenance ledger
for *all* qubits live at the first peak.

Distinct source allocations are not extra physical qubits. max_qubits is a
configured *limit* and must not be confused with the compiled peak Q.

The replay sees Python-surfaced source events including native-returned
scaffolds, not ephemeral allocations wholly hidden within C++ helpers.
If observed source-live peak is below compiled Q, report a genuine evidence
gap rather than claiming to have identified the physical peak.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


def group(stage):
    return "/".join(stage) if stage else "(root)"


def replay_lifetimes(receipt: dict) -> dict:
    Q = receipt["num_qubits_compiled"]
    if not isinstance(Q, int) or Q < 1:
        raise ValueError("expected positive integer compiled num_qubits")
    events = receipt["explicit_events"]
    active: dict[int, dict] = {}
    by_phase = {}
    triggers = Counter()
    source_releases_without_birth = 0
    peaks = []
    first_peak = None
    max_observed = -1
    first_peak_event = None
    last_peak_event = None
    max_events_seen = 0
    source_occurrence_count = 0
    for index, event in enumerate(events):
        kind = event["kind"]
        slots = event.get("physical_slots", [])
        names = event.get("source_occurrences", [])
        if len(slots) != len(names):
            raise ValueError(f"event {index} physical slot/occurrence mismatch")
        stage = event.get("stage", [])
        stage_path = group(stage)
        if kind == "release":
            for q, name in zip(slots, names):
                if q in active:
                    if active[q]["source_occurrence"] != name:
                        raise AssertionError(
                            f"event {index}: release name differs from live occurrence for slot {q}"
                        )
                    del active[q]
                elif name is None:
                    source_releases_without_birth += 1
                else:
                    raise AssertionError(f"event {index}: release of unknown occurrence {name}")
        else:
            for q, name in zip(slots, names):
                if not isinstance(q, int) or q < 0 or q >= Q:
                    raise ValueError(f"event {index}: invalid physical slot {q}")
                if q in active:
                    raise AssertionError(
                        f"event {index}: physical slot {q} reused before source release"
                    )
                if not isinstance(name, str):
                    raise ValueError(f"event {index}: missing indexed birth identity")
                active[q] = {
                    "physical_slot_id": q,
                    "source_occurrence": name,
                    "birth_event_index": index,
                    "birth_kind": kind,
                    "birth_stage": stage,
                    "birth_label": event.get("label"),
                }
                source_occurrence_count += 1

        observed = len(active)
        if observed != event["source_live_count"]:
            raise AssertionError(
                f"event {index}: replay live {observed} differs from receipt "
                f"{event['source_live_count']}"
            )
        current_stage_peak = by_phase.get(stage_path, 0)
        by_phase[stage_path] = max(observed, current_stage_peak)
        if observed > max_observed:
            max_observed = observed
            first_peak_event = index
            last_peak_event = index
            first_peak = [active[q].copy() for q in sorted(active)]
            max_events_seen = 1
            triggers = Counter({stage_path: 1})
        elif observed == max_observed:
            last_peak_event = index
            max_events_seen += 1
            triggers[stage_path] += 1

    if max_observed != receipt["max_explicit_live"]:
        raise AssertionError("receipt claimed maximum does not equal replay maximum")
    if source_releases_without_birth != receipt.get(
        "native_helper_qubits_released_without_observed_birth", 0
    ):
        raise AssertionError("unobserved release count differs from source receipt")

    persistent = [
        x for x in (first_peak or [])
        if x["birth_stage"] == [] and x["birth_kind"] in ("temporary", "named_input")
    ]
    other = [
        x for x in (first_peak or [])
        if not (x["birth_stage"] == [] and x["birth_kind"] in ("temporary","named_input"))
    ]
    source_roles = Counter(x["birth_kind"] for x in first_peak or [])
    stage_roles = Counter(group(x["birth_stage"]) for x in other)
    named_qubits = receipt.get("named_syndrome_qubits", 0)
    root_temp_occurrences = receipt.get("explicit_source_stage_allocation_counts",{}).get("(root)")
    # Do not assume a root occurrence is live at the maximum unless witnessed.
    return {
        "experiment": "013",
        "source_experiment": receipt.get("experiment"),
        "source_parameters": {k:receipt[k] for k in ("n","m","degree") if k in receipt},
        "compiled_physical_Q": Q,
        "compiled_Q_squared": Q*Q,
        "observed_source_live_peak": max_observed,
        "unobserved_peak_qubit_gap": Q-max_observed,
        "observed_peak_equals_compiled_Q": max_observed == Q,
        "first_peak_event_index": first_peak_event,
        "last_peak_event_index": last_peak_event,
        "peak_event_count": max_events_seen,
        "first_peak_trigger_stage": group(events[first_peak_event].get("stage",[])) if first_peak_event is not None else None,
        "first_peak_trigger_kind": events[first_peak_event]["kind"] if first_peak_event is not None else None,
        "trigger_stage_counts": dict(triggers),
        "stage_local_live_maxima": dict(sorted(by_phase.items())),
        "first_peak_root_or_named_count": len(persistent),
        "first_peak_other_workspace_count": len(other),
        "first_peak_source_producer_counts": dict(source_roles),
        "first_peak_workspace_stage_counts": dict(stage_roles),
        "source_named_syndrome_qubits":named_qubits,
        "source_root_temporary_allocation_occurrences":root_temp_occurrences,
        "source_occurrence_births_replayed":source_occurrence_count,
        "source_release_without_birth_count":source_releases_without_birth,
        "first_peak_other_source_occurrences":other,
        "first_peak_all_live_source_occurrences":first_peak,
        "last_observed_source_live_count":len(active),
        "interpretation": (
            "Identifies observed simultaneous source qubit allocation and "
            "the allocation event reaching its maximum. The original "
            "physical circuit may have native C++ scratch invisible to this "
            "Python-level source replay. Live allocation does not prove "
            "which specific qubits participate in every gate at the peak. "
            "No qubit reduction or phase equivalence demonstrated."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_ledger", type=Path)
    parser.add_argument("--report",type=Path,default=Path("/tmp/vqcc_dqi013_peak.json"))
    args = parser.parse_args()
    if args.report.exists():
        parser.error("refusing to overwrite existing report")
    source = json.loads(args.source_ledger.read_text(encoding="utf-8"))
    result = replay_lifetimes(source)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(
        {k:v for k,v in result.items()
         if k not in ("first_peak_all_live_source_occurrences",
                      "first_peak_other_source_occurrences",
                      "stage_local_live_maxima","trigger_stage_counts")},
        indent=2,sort_keys=True,
    ))
    print(f"Stored {len(result['first_peak_all_live_source_occurrences'])} "
          f"source occurrences at first observed peak in {args.report}")


if __name__=="__main__":
    main()
