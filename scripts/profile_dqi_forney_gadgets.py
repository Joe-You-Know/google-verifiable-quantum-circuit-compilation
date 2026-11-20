#!/usr/bin/env python3
"""Experiment 009: isolate the four scored DQI Forney construction gadgets.

These are the literal primitive builder calls used by the reference DQI
Forney loop, not a replacement circuit. Counts are static and should be
cross-checked against the 351-gate-per-position source law at degree 12.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "kickmix"), str(ROOT / "verifiers")]
import kickmix as km


def build_gadget(degree: int, name: str):
    b = km.CircuitBuilder()
    gf = km.GF2Field(degree)
    if name == "inverse_scaffold_round_trip":
        src = b.create_quantum_register(degree, "sigma_prime")
        target = b.alloc_qubits(degree)
        _, chain = b.init_gf2_inverse_with_scaffold(src, target=target, field=gf)
        b.del_gf2_inverse_with_scaffold(src, target=target, scaffold=chain, field=gf)
        b.free(chain)
        b.free(target)
    elif name == "gf2_masked_product_phase":
        u = b.create_quantum_register(degree, "located")
        v = b.create_quantum_register(degree, "inverse")
        m = b.create_classical_register(degree, "mbuc_mask")
        b.gf2_phase_by_product(u, v, mask=m, field=gf)
    elif name == "gf2_variable_accumulate_mul":
        u = b.create_quantum_register(degree, "numerator")
        v = b.create_quantum_register(degree, "denominator")
        target = b.create_quantum_register(degree, "accumulator")
        b.ixor_gf2_mul(u, v, target=target, field=gf)
    elif name == "zero_detect_round_trip":
        src = b.create_quantum_register(degree, "sigma")
        target = b.alloc_qubits(1)[0]
        b.flip_if_equal(src, 0, target=target)
        b.flip_if_equal(src, 0, target=target)
        b.free(target)
    elif name == "masked_located_and_round_trip":
        is_zero = b.create_quantum_register(1, "is_zero")[0]
        omega = b.create_quantum_register(degree, "omega")
        located = b.alloc_qubits(degree)
        b.init_and(is_zero, omega, located)
        b.del_and(is_zero, omega, located)
        b.free(located)
    else:
        raise ValueError(f"unknown gadget {name}")
    circuit = b.finish_circuit()
    stats = circuit.operation_statistics()
    return {
        "gadget": name,
        "degree": degree,
        "toffoli_like": int(stats.num_toffoli_like),
        "CCX": int(stats["CCX"]) if "CCX" in stats else 0,
        "CCZ": int(stats["CCZ"]) if "CCZ" in stats else 0,
        "CSWAP": int(stats["CSWAP"]) if "CSWAP" in stats else 0,
        "num_ops": len(circuit),
        "num_qubits": circuit.num_qubits,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--degrees", type=int, nargs="+", default=[6, 8, 12])
    p.add_argument("--report", type=Path, default=Path("/tmp/vqcc_dqi009.json"))
    args = p.parse_args()
    if args.report.exists():
        p.error("refusing to overwrite report")
    names = (
        "inverse_scaffold_round_trip", "gf2_masked_product_phase",
        "zero_detect_round_trip", "masked_located_and_round_trip",
        "gf2_variable_accumulate_mul",
    )
    records = []
    for degree in args.degrees:
        for name in names:
            row = build_gadget(degree, name)
            records.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
    receipt = {
        "experiment": "009",
        "method": "unmodified original Kickmix builder primitives isolated",
        "gadget_records": records,
        "official_dqi_verifier": "NOT_RUN",
        "interpretation": "Structural cost attribution, not evidence that any gadget can be omitted.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Saved: {args.report}")


if __name__ == "__main__":
    main()
