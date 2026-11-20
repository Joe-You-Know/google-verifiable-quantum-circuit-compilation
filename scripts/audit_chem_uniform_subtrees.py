#!/usr/bin/env python3
"""Audit QROM whole-vector uniform-subtree omission, without modifying circuits.

The shipped builder checks delta[lo:hi] == delta[lo,0] (one scalar). The
correct vector-uniform witness is delta[lo:hi] == delta[lo:lo+1].
Counts predicted costly AND nodes for both exact decision trees.
No physics score or Kickmix equivalence is claimed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "kickmix"), str(ROOT / "verifiers")]
from dfthcsos.example_submission.angle_k_reference_circuit import batch_deltas


def tree_counts(delta: np.ndarray, *, corrected: bool) -> dict:
    rows = len(delta)
    bits = (rows - 1).bit_length()
    record = {"and_nodes": 0, "subtree_early_exits": 0, "uniform_missing": 0}

    def node(lo: int, hi: int):
        if lo >= rows:
            return
        valid = hi <= rows
        scalar_all = bool(np.all(delta[lo:hi] == delta[lo, 0])) if valid else False
        vector_all = bool(np.all(delta[lo:hi] == delta[lo:lo + 1])) if valid else False
        if valid and (hi - lo == 1 or (vector_all if corrected else scalar_all)):
            record["subtree_early_exits"] += 1
            return
        if valid and vector_all and not scalar_all:
            record["uniform_missing"] += 1
        mid = (lo + hi) // 2
        if rows <= mid:
            node(lo, mid)
        else:
            record["and_nodes"] += 1
            node(lo, mid)
            node(mid, hi)
    half = 1 << (bits - 1)
    node(0, half)
    node(half, 2 * half)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=Path("sample_submission/dfthcsos/submission.npz"))
    p.add_argument("--J", type=int, default=8)
    p.add_argument("--report", type=Path, default=Path("/tmp/vqcc_chem006_uniform.json"))
    args = p.parse_args()
    if args.report.exists():
        p.error("refusing to overwrite existing report")
    with np.load(args.source, allow_pickle=False) as npz:
        table = np.asarray(npz["angle_words"], dtype=np.int64)
    deltas = batch_deltas(table, args.J)
    records = []
    for i, delta in enumerate(deltas):
        old = tree_counts(delta, corrected=False)
        new = tree_counts(delta, corrected=True)
        if new["and_nodes"] > old["and_nodes"]:
            raise AssertionError("correction unexpectedly increases tree AND cost")
        r = {"circuit": f"angle_k_{i}", "old": old, "new": new,
             "AND_node_reduction": old["and_nodes"] - new["and_nodes"]}
        records.append(r)
        print(json.dumps(r), flush=True)
    summary = {
        "experiment": "006_preflight",
        "source": str(args.source),
        "rounding_changed": False,
        "source_words_changed": False,
        "exact_uniform_subtree_witnesses": sum(x["old"]["uniform_missing"] for x in records),
        "predicted_AND_node_reduction": sum(x["AND_node_reduction"] for x in records),
        "per_circuit": records,
        "full_Kickmix_equivalence": "NOT_TESTED",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_circuit"}, indent=2))


if __name__ == "__main__":
    main()
