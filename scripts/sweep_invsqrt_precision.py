#!/usr/bin/env python3
"""Experiment 003: deterministic precision-width screening for Invsqrt.

Uses the reference's own fixed_point_model as a numerical *screen*, not as
proof that its quantum circuit satisfies the official benchmark. Any candidate
must also pass the unmodified official Kickmix verifier.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "verifiers"), str(ROOT / "kickmix")]
import numpy as np
from invsqrt.nr_reference_circuit import Precision, relative_error, build_nr_circuit

N_P = 10
MAX_X = 3 * (2**N_P - 2)**2
TOLERANCE = 2.0**-24
FIELDS = ("delta_bits", "coef_bits", "square_bits", "product_bits", "result_bits")


def directed_sample(max_x: int) -> np.ndarray:
    """Deterministically cover small inputs, edges, dyadic transitions, and bulk."""
    xs: set[int] = set(range(1, min(max_x, 256) + 1))
    xs.update(range(max(1, max_x - 255), max_x + 1))
    xs.update(int(v) for v in np.linspace(1, max_x, num=4096))
    xs.update(int(v) for v in np.geomspace(1, max_x, num=2048))
    for exponent in range(2 * N_P + 4):
        pivot = 1 << exponent
        for center in (pivot, 3 * pivot, (3 * pivot) // 2):
            for delta in range(-8, 9):
                x = center + delta
                if 1 <= x <= max_x:
                    xs.add(x)
    return np.asarray(sorted(xs), dtype=np.int64)


def screen(precision: Precision, xs: np.ndarray) -> dict:
    try:
        errors = relative_error(N_P, precision, xs)
        if not np.isfinite(errors).all():
            return {"status": "INVALID", "reason": "nonfinite relative error"}
        index = int(np.argmax(errors))
        worst = float(errors[index])
        return {
            "status": "PASS" if worst < TOLERANCE else "FAIL",
            "worst_relative_error": worst,
            "worst_x": int(xs[index]),
            "ratio_to_tolerance": worst / TOLERANCE,
            "tested_x": int(len(xs)),
        }
    except (ValueError, OverflowError, FloatingPointError, TypeError) as ex:
        return {"status": "INVALID", "reason": str(ex), "tested_x": int(len(xs))}


def full_domain(precision: Precision, chunk: int) -> dict:
    """Check every input x = 1..MAX_X in deterministic bounded-size chunks."""
    worst = -1.0
    worst_x = None
    tested = 0
    for start in range(1, MAX_X + 1, chunk):
        xs = np.arange(start, min(MAX_X + 1, start + chunk), dtype=np.int64)
        check = screen(precision, xs)
        tested += len(xs)
        if check["status"] == "INVALID":
            return {**check, "tested_x": tested, "entire_domain_checked": False}
        if check["worst_relative_error"] > worst:
            worst = check["worst_relative_error"]
            worst_x = check["worst_x"]
        if worst >= TOLERANCE:
            return {
                "status": "FAIL",
                "worst_relative_error_seen": worst,
                "worst_x": worst_x,
                "tested_x": tested,
                "entire_domain_checked": False,
            }
    return {
        "status": "PASS",
        "worst_relative_error": worst,
        "worst_x": worst_x,
        "ratio_to_tolerance": worst / TOLERANCE,
        "tested_x": tested,
        "entire_domain_checked": True,
    }


def candidate_precisions(levels: tuple[int, ...], *, pairwise: bool = False,
                         combination_order: int = 1):
    baseline = Precision()
    yield "baseline", baseline
    for field in FIELDS:
        for reduction in levels:
            if reduction < 1:
                raise ValueError("level reductions must be positive")
            new_value = getattr(baseline, field) - reduction
            if new_value > 0:
                yield f"{field}_minus_{reduction}", replace(baseline, **{field: new_value})
    from itertools import combinations
    max_order = max(combination_order, 2 if pairwise else 1)
    for order in range(2, max_order + 1):
        for chosen in combinations(FIELDS, order):
            replacements = {field: getattr(baseline, field) - 1 for field in chosen}
            yield "_and_".join(chosen) + "_minus_1", replace(
                baseline, **replacements,
            )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--levels", nargs="+", type=int, default=[1], help="bit reductions per field (default: 1)")
    p.add_argument("--full", action="store_true", help="exhaustively check all 3,133,452 x values for screen PASS candidates")
    p.add_argument("--pairwise", action="store_true", help="also test every pair of one-bit reductions")
    p.add_argument("--combination-order", type=int, choices=(1, 2, 3, 4, 5), default=1,
                   help="exhaustive combinations of one-bit width reductions up to this order")
    p.add_argument("--chunk", type=int, default=32768, help="full-check chunk size, default 32768")
    p.add_argument("--output-dir", type=Path, default=Path("/tmp/vqcc_precision_003"))
    p.add_argument("--report", type=Path, default=Path("/tmp/vqcc_precision_003.json"))
    p.add_argument("--no-circuits", action="store_true", help="numeric screen only; do not build/write Kickmix circuits")
    args = p.parse_args()
    if args.chunk < 1:
        p.error("--chunk must be positive")
    if args.report.exists():
        p.error(f"refusing to overwrite existing report: {args.report}")
    if args.report.resolve() == args.output_dir.resolve():
        p.error("report must not equal output directory")

    xs = directed_sample(MAX_X)
    baseline = Precision()
    provenance = {
        "experiment": "003",
        "task": "invsqrt",
        "reference_generator_sha256": hashlib.sha256((ROOT / "verifiers/invsqrt/nr_reference_circuit.py").read_bytes()).hexdigest(),
        "precision_default": asdict(baseline),
        "tolerance": TOLERANCE,
        "domain_x": [1, MAX_X],
        "preliminary_sample_size": len(xs),
        "full_scan_requested": args.full,
        "pairwise": args.pairwise,
        "combination_order": args.combination_order,
        "verification": "reference numerical model only; official Kickmix verifier NOT run",
        "candidates": [],
    }
    for name, prec in candidate_precisions(tuple(args.levels), pairwise=args.pairwise,
                                           combination_order=args.combination_order):
        result = {"name": name, "precision": asdict(prec), "sample": screen(prec, xs)}
        if result["sample"]["status"] == "PASS":
            if args.full:
                result["full"] = full_domain(prec, args.chunk)
            if (not args.full or result["full"]["status"] == "PASS") and not args.no_circuits:
                try:
                    circuit = build_nr_circuit(N_P, prec=prec)
                    result["static_toffoli_like"] = int(circuit.operation_statistics().num_toffoli_like)
                    result["num_qubits"] = int(circuit.num_qubits)
                    result["num_operations"] = int(len(circuit))
                    result["static_qubit_toffoli_proxy"] = result["static_toffoli_like"] * result["num_qubits"]
                    args.output_dir.mkdir(parents=True, exist_ok=True)
                    target = args.output_dir / (name + ".kmb")
                    if target.exists():
                        raise FileExistsError(f"refusing to overwrite circuit: {target}")
                    circuit.to_file(target, format="kmb")
                    result["circuit_path"] = str(target)
                except (ValueError, OverflowError, OSError, RuntimeError) as ex:
                    result["build_error"] = str(ex)
        provenance["candidates"].append(result)
        print(json.dumps(result, sort_keys=True), flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"Saved screening receipt: {args.report}")
    if not args.full:
        print("WARNING: full domain has not been checked. No competition correctness claim.")
    print("WARNING: passing numerical model does not imply official Kickmix verifier PASS.")


if __name__ == "__main__":
    main()
