#!/usr/bin/env python3
"""Experiment 007 stage B: chemical evaluation of joint angle quantization.

Requires local original FCIDUMP (gitignored). Compares the 11-bit
independent-nearest and 11-bit joint-vector-projection source words by
calling the original chemical numerical metric evaluator. Builds and
verifies a .kmb family only if the original acceptance metrics PASS.

No source or current Kaggle submission file is modified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "verifiers"), str(ROOT / "kickmix"), str(ROOT / "scripts")]

import numpy as np
from chem007_vector_projection import quotient_remainder_nearest
from dfthcsos.verify import load_inputs, evaluate_words, passes_accuracy, verify
from dfthcsos.example_submission.angle_k_reference_circuit import (
    build_angle_k_family, write_kmx_family,
)


def measure_table(inputs, words, tree_edges, bits):
    try:
        metrics = evaluate_words(inputs, words, tree_edges, bits)
    except (ValueError, RuntimeError, FloatingPointError, ArithmeticError) as ex:
        return {"status": "ERROR", "reason": f"{type(ex).__name__}: {ex}"}
    return {
        "status": "PASS" if passes_accuracy(metrics) else "FAIL",
        "metrics": metrics,
        "one_body_error_fraction": float(metrics["error_1"]) / 0.02,
        "two_body_error_fraction": float(metrics["error_2"]) / 0.02,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=Path("sample_submission/dfthcsos/submission.npz"))
    p.add_argument("--projected-words", type=Path, default=Path("/tmp/chem007_words11.npy"))
    p.add_argument("--brot", type=int, default=11)
    p.add_argument("--J", type=int, default=9)
    p.add_argument("--build-if-valid", action="store_true")
    p.add_argument("--out-dir", type=Path, default=Path("/tmp/vqcc_chem007_candidate"))
    p.add_argument("--report", type=Path, default=Path("/tmp/vqcc_chem007_metrics.json"))
    p.add_argument("--shots-per-address", type=int, default=64)
    args = p.parse_args()
    if args.report.exists():
        p.error("report exists; refusing to overwrite")
    if not args.projected_words.is_file():
        p.error(f"missing candidate table: {args.projected_words}")
    with np.load(args.source, allow_pickle=False) as src:
        original_words = np.asarray(src["angle_words"], dtype=np.int64)
        fixed = {k: np.asarray(src[k]) for k in src.files if k != "angle_words"}
    projected = np.load(args.projected_words, allow_pickle=False)
    if projected.shape != original_words.shape:
        p.error("candidate table shape mismatch")
    if np.any(projected < 0) or np.any(projected >= 1 << args.brot):
        p.error("candidate source words out of target precision range")
    inputs = load_inputs(args.source)
    independent = quotient_remainder_nearest(original_words, 12, args.brot)

    base = measure_table(inputs, independent, fixed["tree_edges"], args.brot)
    new = measure_table(inputs, projected, fixed["tree_edges"], args.brot)
    receipt = {
        "experiment": "007",
        "source": str(args.source),
        "source_preserved": True,
        "source_angles_preserved_as_target": True,
        "brot": args.brot,
        "J": args.J,
        "independently_nearest": base,
        "joint_projection": new,
        "built": False,
        "official_full_kickmix_verifier": "NOT_RUN",
    }
    if args.build_if_valid and new["status"] == "PASS":
        if args.out_dir.exists():
            p.error(f"candidate directory exists: {args.out_dir}")
        family = build_angle_k_family(projected, args.brot, args.J)
        if max(c.num_qubits for c in family) > 128:
            p.error("ANGLE family violates 128-qubit hard cap")
        args.out_dir.mkdir(parents=True)
        np.savez(args.out_dir / "submission.npz", **fixed, angle_words=projected)
        write_kmx_family(family, args.out_dir, format="kmb")
        receipt["built"] = True
        receipt["candidate_dir"] = str(args.out_dir)
        # Full original sampled address verifier, not a proxy.
        try:
            result = verify(args.out_dir, shots_per_address=args.shots_per_address)
            receipt["official_full_kickmix_verifier"] = {
                "status": "PASS",
                "score": result["score"],
                "verified_shots": result["verified_shots"],
                "toffoli_count": result["toffoli_count"],
                "num_qubits": result["num_qubits"],
                "submission_sha256": result["submission_sha256"],
            }
        except (AssertionError, RuntimeError, ValueError, OSError, TypeError) as ex:
            receipt["official_full_kickmix_verifier"] = {
                "status": "FAIL", "error_type": type(ex).__name__, "error": str(ex)
            }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(receipt, indent=2, default=float) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, default=float))


if __name__ == "__main__":
    main()
