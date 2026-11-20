#!/usr/bin/env python3
"""DQI Experiment 011: distinguish source qubit allocation occurrences from physical slots.

Intercept explicit Kickmix CircuitBuilder alloc_qubits/create_quantum_register
and free calls during source generation, retain q.id, occurrence generation,
named stage labels, and allocator high-water mark. Native helper methods may
allocate internal scratch without crossing the Python proxy; those are
*not* represented as explicit source occurrences. The final qubit count is
taken directly from the finished compiled Kickmix circuit.

The test does not alter the constructed operations, the original source
decoder, or the grader. It does not prove safe qubit omission.
"""
from __future__ import annotations

import argparse
import math
from collections import Counter, defaultdict
from contextlib import AbstractContextManager
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "kickmix"), str(ROOT / "verifiers")]
import kickmix as km
from dqi.dqi_reference_circuit import ProosAndZalkaDecoder, default_n_iters


def handles(value):
    if isinstance(value, (km.q, km.b)):
        return [value]
    return list(value)


def allocator_value(builder, name: str):
    value = getattr(builder, name)
    result = value() if callable(value) else value
    return None if isinstance(result, float) and math.isinf(result) else int(result)


class LabeledMark(AbstractContextManager):
    def __init__(self, ledger, name, original):
        self.ledger = ledger
        self.name = name
        self.original = original

    def __enter__(self):
        self.original.__enter__()
        self.ledger.stack.append(self.name)
        self.ledger.mark_entries.append({
            "stage": list(self.ledger.stack),
            "max_qubits_on_enter": allocator_value(self.ledger.inner, "max_qubits"),
            "allocated_qubits_on_enter": allocator_value(self.ledger.inner, "num_allocated_qubits"),
        })
        return self

    def __exit__(self, exc_type, exc, tb):
        self.ledger.stage_exits.append({
            "stage": list(self.ledger.stack),
            "max_qubits_on_exit": allocator_value(self.ledger.inner, "max_qubits"),
            "allocated_qubits_on_exit": allocator_value(self.ledger.inner, "num_allocated_qubits"),
        })
        self.ledger.stack.pop()
        return self.original.__exit__(exc_type, exc, tb)


class AllocatorLedger:
    def __init__(self):
        self.inner = km.CircuitBuilder()
        self.stack = []
        self.events = []
        self.mark_entries = []
        self.stage_exits = []
        self.live = {}
        self.generations = defaultdict(int)
        self.allocation_counts = Counter()
        self.release_counts = Counter()
        self.max_explicit_live = 0
        self.max_explicit_slot_id = -1

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def mark(self, name):
        return LabeledMark(self, name, self.inner.mark(name))

    def _register(self, value, kind: str, label: str):
        qs = handles(value)
        physical_ids = []
        occurrences = []
        for q in qs:
            if not isinstance(q, km.q):
                raise ValueError(f"{kind}: non-qubit registered in quantum ledger")
            physical_id = int(q.id)
            self.max_explicit_slot_id = max(self.max_explicit_slot_id, physical_id)
            if physical_id in self.live:
                raise AssertionError(f"physical qubit {physical_id} allocated twice without release")
            self.generations[physical_id] += 1
            occurrence = f"q{physical_id}@generation{self.generations[physical_id]}"
            self.live[physical_id] = occurrence
            physical_ids.append(physical_id)
            occurrences.append(occurrence)
        self.allocation_counts[kind] += len(qs)
        self.max_explicit_live = max(self.max_explicit_live, len(self.live))
        self.events.append({
            "kind": kind,
            "label": label,
            "stage": list(self.stack),
            "count": len(qs),
            "physical_slots": physical_ids,
            "source_occurrences": occurrences,
            "source_live_count": len(self.live),
            "allocator_live_count": allocator_value(self.inner, "num_allocated_qubits"),
            "allocator_peak_slots": allocator_value(self.inner, "max_qubits"),
        })
        return value

    def create_quantum_register(self, width, name):
        return self._register(self.inner.create_quantum_register(width, name),
                              "named_input", str(name))

    def alloc_qubits(self, width):
        return self._register(self.inner.alloc_qubits(width),
                              "temporary", f"alloc_qubits({width})")

    def free(self, register):
        qs = handles(register)
        quantum = [q for q in qs if isinstance(q, km.q)]
        classical = [q for q in qs if isinstance(q, km.b)]
        if len(quantum) + len(classical) != len(qs):
            raise ValueError("unknown released handle type")
        released = []
        physical_ids = []
        for q in quantum:
            index = int(q.id)
            if index not in self.live:
                raise AssertionError(f"source-tracked qubit {index} freed without known allocation")
            released.append(self.live[index])
            physical_ids.append(index)
        # Native builder may reject an invalid release. Do not mutate ledger
        # until it has accepted it.
        self.inner.free(register)
        for index in physical_ids:
            del self.live[index]
        self.release_counts["quantum"] += len(quantum)
        self.release_counts["classical"] += len(classical)
        if quantum:
            self.events.append({
                "kind": "release",
                "stage": list(self.stack),
                "count": len(quantum),
                "physical_slots": physical_ids,
                "source_occurrences": released,
                "source_live_count": len(self.live),
                "allocator_live_count": allocator_value(self.inner, "num_allocated_qubits"),
                "allocator_peak_slots": allocator_value(self.inner, "max_qubits"),
            })

    def finish_circuit(self):
        return self.inner.finish_circuit()


def audit_instance(n: int, m: int, degree: int):
    ledger = AllocatorLedger()
    syndromes = [
        ledger.create_quantum_register(degree, name=f"S{i}")
        for i in range(n)
    ]
    error_masks = [
        ledger.create_classical_register(degree, name=f"E{j}")
        for j in range(m)
    ]
    ProosAndZalkaDecoder(n, km.GF2Field(degree)).build_syndrome_decoding_mbuc(
        ledger, syndromes=syndromes, error_mbuc=error_masks,
        n_iters=default_n_iters(n),
    )
    circuit = ledger.finish_circuit()
    static = circuit.operation_statistics()
    peak = int(circuit.num_qubits)
    allocator_peak = allocator_value(ledger.inner, "max_qubits")
    if peak <= ledger.max_explicit_slot_id:
        raise AssertionError(
            f"compiled qubit count {peak} does not cover "
            f"source qubit slot {ledger.max_explicit_slot_id}"
        )
    expected_live_ids = {int(q.id) for register in syndromes for q in register}
    if set(ledger.live) != expected_live_ids:
        raise AssertionError("source quantum ledger did not end with exactly the named syndrome registers")

    reused = [index for index, count in ledger.generations.items() if count > 1]
    max_non_input = peak - n * degree
    if max_non_input < 0:
        raise AssertionError("negative non-syndrome resource count")
    by_source_stage = Counter()
    for e in ledger.events:
        if e["kind"] == "temporary":
            by_source_stage["/".join(e["stage"]) or "(root)"] += e["count"]
    return {
        "experiment": "011",
        "source_class": "ProosAndZalkaDecoder",
        "n": n, "m": m, "degree": degree,
        "num_qubits_compiled": peak,
        "num_ops": len(circuit),
        "static_toffoli_like": int(static.num_toffoli_like),
        "named_syndrome_qubits": n * degree,
        "non_syndrome_peak_slots": max_non_input,
        "max_explicit_live": ledger.max_explicit_live,
        "configured_allocator_qubit_cap": allocator_peak,
        "highest_explicit_source_slot_id": ledger.max_explicit_slot_id,
        "named_qubits_created": ledger.allocation_counts["named_input"],
        "temporary_occurrences_created": ledger.allocation_counts["temporary"],
        "quantum_occurrences_released": ledger.release_counts["quantum"],
        "distinct_slots_used_for_explicit_sources": len(ledger.generations),
        "physical_slots_with_multiple_source_occurrences": len(reused),
        "largest_source_occurrence_generation": max(ledger.generations.values(), default=0),
        "explicit_source_stage_allocation_counts": dict(by_source_stage),
        "explicit_events": ledger.events,
        "mark_entries": ledger.mark_entries,
        "mark_exits": ledger.stage_exits,
        "verified": {
            "compiled_qubits_cover_explicit_source_slots": True,
            "named_syndrome_registers_retained": True,
            "all_tracked_temporaries_released": True,
        },
        "source_limit": (
            "The builder.max_qubits property is a capacity limit, often infinity, "
            "not the observed high-water count. The compiled num_qubits "
            "is authoritative for the scored Q. "
            "Native builder helper methods may allocate/release additional "
            "scratch qubits without Python proxy visibility. Source "
            "allocations are not a complete physical qubit-use history."
        ),
        "official_DQI_phase_verifier": "NOT_RUN",
        "reduced_qubit_count": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=6)
    p.add_argument("--m", type=int, default=15)
    p.add_argument("--degree", type=int, default=6)
    p.add_argument("--report", type=Path, default=Path("/tmp/vqcc_dqi011.json"))
    args = p.parse_args()
    if args.report.exists():
        p.error(f"refusing to overwrite {args.report}")
    result = audit_instance(args.n, args.m, args.degree)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    concise = {k: v for k, v in result.items()
               if k not in ("explicit_events", "mark_entries", "mark_exits")}
    print(json.dumps(concise, indent=2, sort_keys=True))
    print(f"Stored {len(result['explicit_events'])} source events and "
          f"{len(result['mark_entries'])} stage entries at {args.report}")


if __name__ == "__main__":
    main()
