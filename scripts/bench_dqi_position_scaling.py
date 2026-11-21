#!/usr/bin/env python3
"""Experiment 008: DQI source-generation resource scaling under controlled m.

Build several standalone reference circuits with fixed field degree, fixed
syndrome count and varying number of classical error positions. Measuring
the differences identifies m-dependent Toffoli/Q cost, but is NOT a
phase-verification test or an estimate of the full 4,095-position score.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "kickmix"), str(ROOT / "verifiers")]
from dqi.dqi_reference_circuit import build_reference_circuit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=6)
    p.add_argument("--degree", type=int, default=6)
    p.add_argument("--positions", type=int, nargs="+", default=[15, 31, 63])
    p.add_argument("--report", type=Path, default=Path("/tmp/vqcc_dqi008.json"))
    args = p.parse_args()
    if args.report.exists():
        p.error("refusing to overwrite report")
    if not (2 <= args.n < min(args.positions)):
        p.error("require n >= 2 and all m > n")
    if max(args.positions) > (1 << args.degree) - 1:
        p.error("field has too few nonzero elements for requested m")

    results = []
    for m in sorted(set(args.positions)):
        circuit = build_reference_circuit(m, args.n, args.degree)
        stats = circuit.operation_statistics()
        row = {
            "m": m, "n": args.n, "degree": args.degree,
            "num_qubits": int(circuit.num_qubits),
            "num_bits": int(circuit.num_bits),
            "num_ops": int(len(circuit)),
            "static_toffoli_like": int(stats.num_toffoli_like),
            "CCX": int(stats["CCX"]) if "CCX" in stats else 0,
            "CSWAP": int(stats["CSWAP"]) if "CSWAP" in stats else 0,
            "reaction_depth": int(circuit.reaction_depth()),
        }
        results.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)

    pair_differences = []
    for left, right in zip(results, results[1:]):
        delta_m = right["m"] - left["m"]
        pair_differences.append({
            "from_m": left["m"], "to_m": right["m"],
            "delta_m": delta_m,
            "Toffolis_per_extra_m": (
                right["static_toffoli_like"] - left["static_toffoli_like"]
            ) / delta_m,
            "qubits_change": right["num_qubits"] - left["num_qubits"],
        })
    receipt = {
        "experiment": "008", "method": "build original DQI reference family, static cost only",
        "n": args.n, "degree": args.degree,
        "results": results, "pair_differences": pair_differences,
        "official_verifier": "NOT_RUN", "large_benchmark_extrapolation": "NOT_VALIDATED",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pair_differences": pair_differences}, indent=2))


if __name__ == "__main__":
    main()
