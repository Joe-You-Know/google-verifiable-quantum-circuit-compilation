#!/usr/bin/env python3
"""Independent randomized audit of X/CX/CCX segments in Kickmix .kmx files.

Does not simulate phase or measurement operations. Requires exact preservation
of every unsupported instruction and its relative position. This is not an
official Kickmix verifier and does not establish whole-circuit validity.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from causal_commuting_frontier_kmx import optimize_text, candidate


def partition(code: str):
    spans, barriers, current = [], [], []
    for line in code.splitlines():
        sig = candidate(line)
        if sig is None:
            spans.append(current)
            current = []
            barriers.append(line)
        else:
            current.append(sig)
    spans.append(current)
    return spans, barriers


def interpret(span, initial):
    state = list(initial)
    for gate in span:
        wires = [int(w[1:]) for w in gate[1:]]
        enable = 1
        for control in wires[:-1]:
            enable &= state[control]
        state[wires[-1]] ^= enable
    return tuple(state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20261120)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("samples must be at least one")
    paths = sorted(args.directory.glob("angle_k_*.kmx"))
    if not paths:
        parser.error("no angle_k_*.kmx files found")

    rng = random.Random(args.seed)
    total_changed = total_checks = 0
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as file:
            original = file.read()
        optimized, report = optimize_text(original)
        spans1, barriers1 = partition(original)
        spans2, barriers2 = partition(optimized)
        if barriers1 != barriers2 or len(spans1) != len(spans2):
            raise AssertionError(f"barrier mismatch: {path}")
        changed = 0
        for before, after in zip(spans1, spans2):
            if before == after:
                continue
            changed += 1
            support = {int(q[1:]) for gate in before for q in gate[1:]}
            qubits = max(support) + 1
            for _ in range(args.samples):
                state = [rng.getrandbits(1) for _ in range(qubits)]
                if interpret(before, state) != interpret(after, state):
                    raise AssertionError(f"basis-state counterexample: {path}")
                total_checks += 1
        total_changed += changed
        print(json.dumps({
            "file": path.name,
            "status": "PASS",
            "changed_segments": changed,
            "removed_gates": report["removed_gates"],
        }))

    print(json.dumps({
        "status": "PASS",
        "file_count": len(paths),
        "changed_segments": total_changed,
        "basis_state_checks": total_checks,
        "samples_per_changed_segment": args.samples,
        "seed": args.seed,
        "scope": "classical reversible segments only; not official Kickmix verifier",
    }, indent=2))


if __name__ == "__main__":
    main()
