#!/usr/bin/env python3
"""Experiment 022: source-occurrence liveness audit and an independently derived
synchronized-EEA control decomposition.

This script does NOT alter the official DQI source or saved 020 circuit.
The original-source ledger is reused to preserve identities q{id}@generation{n}
and the distinction between unobserved native births and explicit sources.
No competitors' circuits or published quantum gates are imported.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "verifiers")]
from profile_dqi_source_allocations import AllocatorLedger
from research.dqi020_experimental_decoder import (
    ProosAndZalkaDecoder, default_n_iters,
)
from research.dqi022_sparse_control import SparseControlDecoder
from research.dqi022_serial_forney import SerialForneyDecoder, SparseSerialForneyDecoder
from dqi.verify_submission_dqi import (
    ProblemSpecDQI, FieldTables, default_num_accepted_values,
    sample_shots, verify,
)


def control_identity_test():
    """All 8 possible Boolean input states, not a random sample."""
    for h in (0, 1):
        for a in (0, 1):
            for b in (0, 1):
                original = tuple(int(bool(h and ((a, b) == pair)))
                                 for pair in ((0, 0), (1, 0), (0, 1), (1, 1)))
                c1 = h & a
                c2 = h & b
                c3 = c1 & b
                c1 ^= c3
                c2 ^= c3
                c0 = h ^ c1 ^ c2 ^ c3
                derived = (c0, c1, c2, c3)
                assert derived == original, (h, a, b, original, derived)
                # Inverse source operations restore all construction qubits.
                c0 ^= h ^ c1 ^ c2 ^ c3
                c2 ^= c3
                c1 ^= c3
                c3 ^= c1 & b
                c2 ^= h & b
                c1 ^= h & a
                assert (c0, c1, c2, c3) == (0, 0, 0, 0)
    return {"basis_cases": 8, "one_hot_comparison": "PASS",
            "all_source_controls_preserved": True,
            "all_derived_controls_uncomputed": True}


def root_quantum_count(n: int, degree: int):
    m = n + 3
    n_iters = default_n_iters(n)
    # All simultaneous retained sources before transient stage construction.
    return {
        "named_syndrome": n * degree,
        "reg_a_extra": 3 * degree,
        "reg_b": m * degree,
        "metadata_degree_counters": 5 * (m.bit_length() + 1),
        "flag": 1,
        "counter": 2,
        "halting_counter": n_iters.bit_length(),
    }


def source_replay(events):
    live = {}
    first_peak = None
    peak = 0
    max_by_stage = defaultdict(int)
    source_by_stage = Counter()
    witness_sha = hashlib.sha256()
    stage_at_peak = Counter()

    for idx, event in enumerate(events):
        kind = event["kind"]
        stage = tuple(event.get("stage", []))
        witness_sha.update(json.dumps([
            idx, kind, list(stage),
            event.get("source_occurrences", []),
            event.get("physical_slots", []),
            event["source_live_count"],
        ], separators=(',', ':')).encode('utf-8'))
        for physical, occurrence in zip(
                event["physical_slots"], event["source_occurrences"]):
            if kind == "release":
                if physical in live:
                    assert live[physical]["identity"] == occurrence, (
                        idx, physical, occurrence, live[physical])
                    del live[physical]
                else:
                    # Same evidence boundary as Experiment 011.
                    assert occurrence is None
            else:
                assert physical not in live, (idx, physical)
                live[physical] = {
                    "identity": occurrence,
                    "birth_stage": "/".join(stage) or "(root)",
                    "birth_kind": kind,
                    "birth_event": idx,
                }
                source_by_stage["/".join(stage) or "(root)"] += 1

        assert len(live) == event["source_live_count"], (
            idx, len(live), event["source_live_count"])
        stage_name = stage[0] if stage else "(root)"
        max_by_stage[stage_name] = max(max_by_stage[stage_name], len(live))

        if len(live) > peak:
            peak = len(live)
            first_peak = (idx, list(stage), dict(live))
            stage_at_peak = Counter(x["birth_stage"] for x in live.values())

    assert first_peak is not None
    idx, stage, snapshot = first_peak
    sample = {}
    for group in sorted(set(x["birth_stage"] for x in snapshot.values())):
        members = sorted((p, x) for p, x in snapshot.items()
                         if x["birth_stage"] == group)
        sample[group] = {
            "count": len(members),
            "first_five_occurrences": [
                {"physical_slot": p, **x} for p, x in members[:5]]
        }
    return {
        "events_replayed": len(events),
        "event_ledger_sha256": witness_sha.hexdigest(),
        "observed_maximum_simultaneously_live": peak,
        "first_max_event_index": idx,
        "first_max_trigger_stage": "/".join(stage) or "(root)",
        "first_max_birth_groups": dict(stage_at_peak),
        "first_max_source_examples": sample,
        "max_explicit_live_by_top_stage": dict(max_by_stage),
        "cumulative_source_births_by_stage": dict(source_by_stage),
        "live_source_occurrences_after_circuit": len(live),
    }


def build_audit(n, m, degree, mode, shared_shots=None, seed=20261121,
                confidence=-16):
    ledger = AllocatorLedger()
    syndromes = [
        ledger.create_quantum_register(degree, name=f"S{i}")
        for i in range(n)
    ]
    errors = [
        ledger.create_classical_register(degree, name=f"E{j}")
        for j in range(m)
    ]
    cls = {
        "020_reference": ProosAndZalkaDecoder,
        "sparse_control": SparseControlDecoder,
        "serial_forney": SerialForneyDecoder,
        "sparse_serial_forney": SparseSerialForneyDecoder,
    }[mode]
    cls(n, km.GF2Field(degree), quotient_mode="norm_inverse"
        ).build_syndrome_decoding_mbuc(
            ledger, syndromes=syndromes, error_mbuc=errors,
            n_iters=default_n_iters(n)
        )
    circuit = ledger.finish_circuit()
    stats = circuit.operation_statistics()
    reported = {
        "mode": mode,
        "n": n,
        "m": m,
        "degree": degree,
        "native_compiled": True,
        "num_qubits": int(circuit.num_qubits),
        "static_toffoli_like": int(stats.num_toffoli_like),
        "num_ops": len(circuit),
        "tracked_native_release_without_birth": ledger.unobserved_native_releases,
        "root_retained_formula": root_quantum_count(n, degree),
        "root_retained_sum": sum(root_quantum_count(n, degree).values()),
    }
    source = source_replay(ledger.events)
    source["native_qubit_count_minus_explicit_peak"] = (
        circuit.num_qubits - source["observed_maximum_simultaneously_live"])
    source["all_explicit_temporaries_released"] = (
        set(ledger.live) == {int(q.id) for reg in syndromes for q in reg})
    assert source["all_explicit_temporaries_released"]
    assert circuit.num_qubits >= source["observed_maximum_simultaneously_live"]
    reported["source_liveness"] = source

    if shared_shots is not None:
        spec = ProblemSpecDQI(m=m, n=n, degree=degree,
            r=default_num_accepted_values(degree),
            num_shots=len(shared_shots[0]))
        v = verify(circuit, spec, shots=shared_shots, seed=seed,
            batch_size=128, log2_delta=confidence, max_workers=1)
        reported["sampled_dqi_verification"] = {
            k:v[k] for k in (
                "status", "num_qubits", "verified_shots", "value_errors",
                "phase_errors", "toffoli_count", "max_toffoli_count",
                "score", "log2_delta", "circuit_sha256"
            )
        }
    else:
        reported["sampled_dqi_verification"] = "NOT_RUN"
    del ledger, circuit
    gc.collect()
    return reported


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=6)
    p.add_argument("--m", type=int, default=15)
    p.add_argument("--degree", type=int, default=12)
    p.add_argument("--modes", nargs="+", choices=("020_reference",
         "sparse_control", "serial_forney", "sparse_serial_forney"), default=["020_reference", "sparse_control"])
    p.add_argument("--shots", type=int, default=512,
         help="0 means native compile/liveness only")
    p.add_argument("--seed", type=int, default=20261121)
    p.add_argument("--confidence", type=float, default=-16.0)
    p.add_argument("--out", type=Path,
         default=Path("/tmp/vqcc_dqi022_report.json"))
    args = p.parse_args()
    if args.degree != 12: p.error("authenticated source requires degree=12")
    if not (2 <= args.n <= args.m <= 4095): p.error("require 2<=n<=m<=4095")
    if args.shots and (args.m <= args.n or args.shots % 128 != 0):
        p.error("sampled verifier requires n<m and shots divisible by 128")
    shots = None
    if args.shots:
        spec = ProblemSpecDQI(m=args.m,n=args.n,degree=args.degree,
            r=default_num_accepted_values(args.degree),num_shots=args.shots)
        shots = sample_shots(spec, FieldTables(km.GF2Field(args.degree)),
                             np.random.default_rng(args.seed), args.shots)
    result = {
        "experiment": "022",
        "original_decoder_untouched": True,
        "source": "original authored Experiment 020 plus independently derived causal controls",
        "control_basis_truth_table": control_identity_test(),
        "results": [],
    }
    for mode in args.modes:
        r = build_audit(args.n,args.m,args.degree,mode,shots,
                        args.seed,args.confidence)
        result["results"].append(r)
        print("COMPILED_AND_AUDITED", json.dumps({
            "mode":mode,
            "Q":r["num_qubits"],
            "T_static":r["static_toffoli_like"],
            "operations":r["num_ops"],
            "observed_source_peak":r["source_liveness"][
                "observed_maximum_simultaneously_live"],
            "first_peak_stage":r["source_liveness"][
                "first_max_trigger_stage"],
            "peak_birth_groups":r["source_liveness"][
                "first_max_birth_groups"],
            "sampled_verification":r["sampled_dqi_verification"]
        }), flush=True)
    if len(result["results"]) == 2:
        a,b = result["results"]
        result["candidate_differences"] = {
            key: b[key] - a[key]
            for key in ("num_qubits", "static_toffoli_like", "num_ops")
        }
        result["both_phase_verifications_pass"] = (
            isinstance(a["sampled_dqi_verification"], dict) and
            isinstance(b["sampled_dqi_verification"], dict) and
            a["sampled_dqi_verification"]["status"] == "PASS" and
            b["sampled_dqi_verification"]["status"] == "PASS" and
            a["sampled_dqi_verification"]["value_errors"] == 0 and
            b["sampled_dqi_verification"]["value_errors"] == 0 and
            a["sampled_dqi_verification"]["phase_errors"] == 0 and
            b["sampled_dqi_verification"]["phase_errors"] == 0
        )
        if args.shots:
            assert result["both_phase_verifications_pass"]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("RECEIPT", json.dumps({
        "path": str(args.out),
        "diff": result.get("candidate_differences"),
        "phase_pass": result.get("both_phase_verifications_pass")
    }), flush=True)


if __name__=="__main__":
    main()
