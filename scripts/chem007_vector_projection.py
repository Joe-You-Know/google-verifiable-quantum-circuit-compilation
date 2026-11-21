#!/usr/bin/env python3
"""Experiment 007: source-relative Givens vector-aware low-width projection.

Hypothesis: independently quantizing each angle discards the fact that all
75 rotations jointly construct a single source vector. At fixed target word
width, use reverse-coordinate optimization to choose words that best
reconstruct the *original 12-bit source vector* in Euclidean squared error.

This is a deterministic, quantified source-reconstruction test, NOT a
certificate of chemical accuracy. Only the original DFTHC-SOS metric
verifier can accept the new angle words, using the locally retained FCIDUMP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def decode_vectors(words: np.ndarray, tree_edges: np.ndarray,
                   bits: int) -> np.ndarray:
    """Use the verifier's published Givens rotation convention."""
    w = np.asarray(words, dtype=np.int64)
    tree = np.asarray(tree_edges, dtype=np.int64)
    if w.ndim != 2 or tree.shape != (w.shape[1], 2):
        raise ValueError("words or tree shape mismatch")
    if not (1 <= bits <= 60) or np.any(w < 0) or np.any(w >= (1 << bits)):
        raise ValueError("invalid word representation")
    n = int(tree.max()) + 1
    if n < 2 or np.any(tree < 0):
        raise ValueError("tree indices must be nonnegative")
    v = np.zeros((len(w), n), dtype=np.float64)
    v[:, 0] = 1.0
    for k, (p, c) in enumerate(tree):
        theta = np.pi * w[:, k].astype(np.float64) / (1 << (bits - 1))
        cs, sn = np.cos(theta), np.sin(theta)
        vp = v[:, p].copy()
        vc = v[:, c].copy()
        v[:, p] = cs * vp - sn * vc
        v[:, c] = sn * vp + cs * vc
    return v


def quotient_remainder_nearest(source_words: np.ndarray,
                               source_bits: int, target_bits: int) -> np.ndarray:
    """Round source integer turns using explicit quotient and remainder."""
    if not 1 <= target_bits <= source_bits <= 60:
        raise ValueError("invalid bit widths")
    divisor = 1 << (source_bits - target_bits)
    q, r = np.divmod(np.asarray(source_words, dtype=np.int64), divisor)
    if np.any(q < 0) or np.any(q * divisor + r >= 1 << source_bits):
        raise ValueError("out-of-range source words")
    if divisor > 1:
        half = divisor // 2
        q += (r > half) | ((r == half) & (np.divmod(q, 2)[1] == 1))
    return np.divmod(q, 1 << target_bits)[1]


def reverse_source_projection(source_words: np.ndarray,
                              tree_edges: np.ndarray,
                              source_bits: int,
                              target_bits: int,
                              passes: int = 2) -> tuple[np.ndarray, dict]:
    if passes < 0:
        raise ValueError("passes must be nonnegative")
    source = np.asarray(source_words, dtype=np.int64)
    tree = np.asarray(tree_edges, dtype=np.int64)
    target = decode_vectors(source, tree, source_bits)
    words = quotient_remainder_nearest(source, source_bits, target_bits)
    baseline = decode_vectors(words, tree, target_bits)
    errors_initial = np.sum((baseline - target) ** 2, axis=1)
    sequence = [{
        "step": 0, "sum_squared_vector_error": float(errors_initial.sum()),
        "maximum_squared_vector_error": float(errors_initial.max()),
        "mean_squared_vector_error": float(errors_initial.mean()),
    }]
    bit_scale = 1 << (target_bits - 1)
    period = 1 << target_bits
    for iteration in range(passes):
        # Retain only the original pair-coordinate producer for each
        # angle, not the entire (rows,angles,orbitals) history.
        state = np.zeros_like(target)
        state[:, 0] = 1.0
        pre_p = np.empty_like(words, dtype=np.float64)
        pre_c = np.empty_like(words, dtype=np.float64)
        for k, (p, c) in enumerate(tree):
            pre_p[:, k] = state[:, p]
            pre_c[:, k] = state[:, c]
            theta = np.pi * words[:, k] / bit_scale
            cs, sn = np.cos(theta), np.sin(theta)
            vp, vc = state[:, p].copy(), state[:, c].copy()
            state[:, p] = cs * vp - sn * vc
            state[:, c] = sn * vp + cs * vc

        reverse_target = target.copy()
        for k in reversed(range(len(tree))):
            p, c = tree[k]
            a = pre_p[:, k] * reverse_target[:, p] + pre_c[:, k] * reverse_target[:, c]
            b = pre_p[:, k] * reverse_target[:, c] - pre_c[:, k] * reverse_target[:, p]
            # Choose the closest admissible target angle to the exact
            # optimum: maximize A*cos(theta)+B*sin(theta).
            theta_star = np.arctan2(b, a)
            new_index = np.rint(theta_star * bit_scale / np.pi).astype(np.int64)
            candidate = np.divmod(new_index, period)[1]
            meaningful = np.hypot(a, b) > 1e-13
            words[:, k] = np.where(meaningful, candidate, words[:, k])
            chosen = np.pi * words[:, k] / bit_scale
            cs, sn = np.cos(chosen), np.sin(chosen)
            tp, tc = reverse_target[:, p].copy(), reverse_target[:, c].copy()
            reverse_target[:, p] = cs * tp + sn * tc
            reverse_target[:, c] = -sn * tp + cs * tc

        optimized = decode_vectors(words, tree, target_bits)
        errors = np.sum((optimized - target) ** 2, axis=1)
        sequence.append({
            "step": iteration + 1,
            "sum_squared_vector_error": float(errors.sum()),
            "maximum_squared_vector_error": float(errors.max()),
            "mean_squared_vector_error": float(errors.mean()),
            "improved_rows_vs_nearest": int(np.count_nonzero(errors < errors_initial - 1e-12)),
            "worse_rows_vs_nearest": int(np.count_nonzero(errors > errors_initial + 1e-10)),
        })

    final_errors = np.sum((decode_vectors(words, tree, target_bits) - target) ** 2, axis=1)
    return words, {
        "experiment": "007",
        "source_bits": source_bits,
        "target_bits": target_bits,
        "passes": passes,
        "source_rows": len(words),
        "angles_per_row": words.shape[1],
        "initial_squared_error_total": float(errors_initial.sum()),
        "final_squared_error_total": float(final_errors.sum()),
        "relative_reconstruction_error_reduction": (
            float(1 - final_errors.sum() / errors_initial.sum()) if errors_initial.sum() else 0.0),
        "per_pass": sequence,
        "source_vector_target": "original integer angle words decoded with original tree",
        "official_chemistry_verifier": "NOT_RUN",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("sample_submission/dfthcsos/submission.npz"))
    parser.add_argument("--source-bits", type=int, default=12)
    parser.add_argument("--target-bits", type=int, default=11)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--report", type=Path, default=Path("/tmp/vqcc_chem007.json"))
    parser.add_argument("--output-words", type=Path,
                        default=Path("/tmp/vqcc_chem007_words.npy"))
    args = parser.parse_args()
    if args.output_words.exists() or args.report.exists():
        parser.error("refusing to overwrite candidate source or report")
    with np.load(args.source, allow_pickle=False) as src:
        words = np.asarray(src["angle_words"], dtype=np.int64)
        edges = np.asarray(src["tree_edges"], dtype=np.int64)
    result_words, results = reverse_source_projection(
        words, edges, args.source_bits, args.target_bits, args.passes)
    result_sha256 = hashlib.sha256(result_words.tobytes()).hexdigest()
    results["candidate_word_sha256"] = result_sha256
    results["source_npz_sha256"] = hashlib.sha256(args.source.read_bytes()).hexdigest()
    args.output_words.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output_words, result_words, allow_pickle=False)
    results["candidate_word_file"] = str(args.output_words)
    args.report.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
