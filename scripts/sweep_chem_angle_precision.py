#!/usr/bin/env python3
"""Experiment 004: fail-closed DFTHC-SOS precision and batch-width audit.

Retain original factorization, tree edges and source references; change only
quantized diagnostic angle words and rebuild their ANGLE circuit family.
Numerical checks use the shipped verifier and locally retained FCIDUMP.
No external claim is made before the full official Kickmix verifier passes.
"""
from __future__ import annotations

import argparse
from math import ceil
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "verifiers"), str(ROOT / "kickmix")]
import numpy as np
from dfthcsos.verify import (
    load_inputs, evaluate_words, passes_accuracy,
    rejection_reason, resource_costs, score_from_metrics,
)
from dfthcsos.example_submission.angle_k_reference_circuit import (
    build_angle_k_family, write_kmx_family,
)


def rescale_words(words, source_bits: int, target_bits: int,
                  rounding: str = "nearest_even"):
    """Quotient/remainder reduction of turn words with explicit tie policy."""
    a = np.asarray(words, dtype=np.int64)
    if a.ndim != 2 or not 1 <= target_bits <= source_bits <= 60:
        raise ValueError("invalid word array or bit widths")
    if np.any(a < 0) or np.any(a >= 2 ** source_bits):
        raise ValueError("source word outside encoding")
    if rounding not in ("nearest_even", "nearest_up", "floor"):
        raise ValueError("unknown rounding")
    factor = 2 ** (source_bits - target_bits)
    quotient, remainder = np.divmod(a, factor)
    if factor == 1 or rounding == "floor":
        increment = np.zeros_like(quotient)
    elif rounding == "nearest_up":
        increment = remainder >= factor // 2
    else:
        half = factor // 2
        increment = (remainder > half) | (
            (remainder == half) & (np.divmod(quotient, 2)[1] == 1)
        )
    return np.divmod(quotient + increment, 2 ** target_bits)[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=Path("sample_submission/dfthcsos/submission.npz"))
    p.add_argument("--widths", type=int, nargs="+", default=[12, 11, 10, 9])
    p.add_argument("--roundings", nargs="+", default=["nearest_even", "floor"],
                   choices=["nearest_even", "nearest_up", "floor"])
    p.add_argument("--batch-sizes", nargs="+", type=int,
                   help="optional explicit batch sizes; otherwise largest fitting J")
    p.add_argument("--build", action="store_true", help="build new KMB family for metric-passing candidates")
    p.add_argument("--skip-numeric", action="store_true",
                   help="structural calculation only, without accuracy claims")
    p.add_argument("--out-dir", type=Path, default=Path("/tmp/vqcc_chem004"))
    p.add_argument("--report", type=Path, default=Path("/tmp/vqcc_chem004.json"))
    args = p.parse_args()
    if args.report.exists():
        p.error(f"refusing to overwrite {args.report}")
    if args.build and args.skip_numeric:
        p.error("cannot build without official numerical metric check")

    with np.load(args.source, allow_pickle=False) as npz:
        if "angle_words" not in npz or "tree_edges" not in npz:
            p.error("reference NPZ lacks angle_words or tree_edges")
        words = np.asarray(npz["angle_words"], dtype=np.int64)
        fixed = {k: np.asarray(npz[k]) for k in npz.files if k != "angle_words"}
    source_bits = 12
    if words.ndim != 2 or np.any(words < 0) or np.any(words >= 2 ** source_bits):
        p.error("reference words must be a 2D table of unsigned 12-bit integers")

    inputs = None if args.skip_numeric else load_inputs(args.source)
    n = (words.shape[0] - 1).bit_length()
    records = []
    for brot in sorted(set(args.widths), reverse=True):
        if not 1 <= brot <= source_bits:
            p.error(f"invalid width {brot}")
        maximum_J = (128 - (2 * n - 1)) // brot
        batches = args.batch_sizes or [maximum_J]
        for rounding in args.roundings:
            current = rescale_words(words, source_bits, brot, rounding)
            metrics = None
            numerical = "NOT_RUN"
            try:
                if inputs is not None:
                    metrics = evaluate_words(inputs, current, fixed["tree_edges"], brot)
                    numerical = "PASS" if passes_accuracy(metrics) else "FAIL"
            except (ValueError, FloatingPointError, ArithmeticError) as ex:
                numerical = "ERROR: " + str(ex)
            for J in batches:
                if J < 1:
                    p.error("J must be positive")
                qubit_bound = 2 * n - 1 + brot * J
                row = {
                    "brot": brot, "J": J, "rounding": rounding,
                    "num_circuits": ceil(words.shape[1] / J),
                    "qubit_upper_bound": qubit_bound,
                    "fits_cap_128": qubit_bound <= 128,
                    "numeric_status": numerical,
                    "metrics": metrics, "built": False,
                    "official_kickmix_verification": "NOT_RUN",
                }
                if args.build and numerical == "PASS" and qubit_bound <= 128:
                    try:
                        circuits = build_angle_k_family(current, brot, J)
                        toffoli = 2 * sum(c.operation_statistics().num_toffoli_like for c in circuits)
                        resources = resource_costs(inputs, circuits, brot, toffoli)
                        rejected = rejection_reason(metrics, resources)
                        if rejected:
                            row["resource_rejection"] = rejected
                        else:
                            folder = args.out_dir / f"brot{brot}_J{J}_{rounding}"
                            if folder.exists():
                                raise FileExistsError(f"refusing to overwrite {folder}")
                            folder.mkdir(parents=True)
                            np.savez(folder / "submission.npz", **fixed, angle_words=current)
                            write_kmx_family(circuits, folder, format="kmb")
                            row["built"] = True
                            row["candidate_folder"] = str(folder)
                            row["num_oracle_toffoli_fwd_reverse"] = toffoli
                            row["resources_proxy"] = resources
                            row["predicted_score_if_verified"] = score_from_metrics(metrics, resources)
                    except (ValueError, OSError, RuntimeError, OverflowError) as ex:
                        row["build_error"] = str(ex)
                records.append(row)
                print(json.dumps(row, sort_keys=True, default=float), flush=True)
    result = {"experiment": "004", "source": str(args.source),
              "source_shape": list(words.shape),
              "numeric_checked": not args.skip_numeric,
              "reference_FCIDUMP_required": not args.skip_numeric,
              "full_official_kickmix_verified": False, "candidates": records}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, default=float) + "\n", encoding="utf-8")
    print(f"Saved receipt: {args.report}")


if __name__ == "__main__":
    main()
