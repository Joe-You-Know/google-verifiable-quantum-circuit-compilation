#!/usr/bin/env python3
"""Conservative source-preserving omission of reversible Kickmix text gates.

Only X, CX and CCX without conditions are candidates. Identical involutions
cancel when no intervening operation touches any of their qubits. Unknown
syntax, metadata, measurements and conditioned gates are global barriers.
The output is a new .kmx file. It is NOT an official verifier result.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

_GATE_ARITY = {"X": 1, "CX": 2, "CCX": 3}
_QUBIT = re.compile(r"q(?:0|[1-9][0-9]*)\Z")


def gate_signature(line: str) -> tuple[str, ...] | None:
    """Return an unconditional gate signature or None (fail closed)."""
    terms = line.split()
    if not terms:
        return None
    arity = _GATE_ARITY.get(terms[0])
    if arity is None or len(terms) != arity + 1:
        return None
    wires = terms[1:]
    if len(set(wires)) != len(wires) or not all(_QUBIT.fullmatch(q) for q in wires):
        return None
    return tuple(terms)


def optimize_text(source: str) -> tuple[str, dict]:
    """Return optimized .kmx text and an auditable deterministic report.

    Per-wire causal frontier: the last still-active gate touching each qubit.
    A repeated signature can cancel with its predecessor only when that
    predecessor is the last touching gate on *every* member of its support.
    Therefore all intervening operations commute with the pair, and the
    pair's product is the identity. A barrier clears all frontiers.
    """
    lines = source.splitlines(keepends=True)
    output: list[str | None] = []
    preceding: list[dict[str, int | None] | None] = []
    signatures: list[tuple[str, ...] | None] = []
    source_lines: list[int] = []
    frontier: dict[str, int | None] = {}
    omissions: Counter[str] = Counter()
    certificates = []
    barriers = 0
    gate_count = 0

    for number, line in enumerate(lines, start=1):
        sig = gate_signature(line)
        if sig is None:
            # Never commute across unrecognized semantics, measurement,
            # control, classical feedback, or register declarations.
            frontier.clear()
            barriers += 1
            output.append(line)
            preceding.append(None)
            signatures.append(None)
            source_lines.append(number)
            continue

        gate_count += 1
        wires = sig[1:]
        last = [frontier.get(q) for q in wires]
        prev_index = last[0]
        if (prev_index is not None and all(i == prev_index for i in last)
                and signatures[prev_index] == sig):
            record = preceding[prev_index]
            assert record is not None  # Only gates have predecessor records.
            output[prev_index] = None
            for q in wires:
                ancestor = record[q]
                if ancestor is None:
                    frontier.pop(q, None)
                else:
                    frontier[q] = ancestor
            omissions[sig[0]] += 2
            certificates.append({
                "gate": " ".join(sig),
                "source_lines": [source_lines[prev_index], number],
                "reason": "same involution; intermediate gates have disjoint support",
            })
            continue

        index = len(output)
        output.append(line)
        preceding.append({q: predecessor for q, predecessor in zip(wires, last)})
        signatures.append(sig)
        source_lines.append(number)
        for q in wires:
            frontier[q] = index

    optimized = "".join(line for line in output if line is not None)
    return optimized, {
        "method": "conservative-causal-frontier-v1",
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "optimized_sha256": hashlib.sha256(optimized.encode("utf-8")).hexdigest(),
        "input_candidate_gates": gate_count,
        "removed_gates": dict(sorted(omissions.items())),
        "total_removed_gates": sum(omissions.values()),
        "pairs_removed": len(certificates),
        "barrier_lines": barriers,
        "certificates": certificates,
        "verification": "symbolic commutation only; independent Kickmix verifier NOT run",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Original Kickmix .kmx text circuit")
    parser.add_argument("output", type=Path, help="New .kmx circuit, never overwrites input")
    parser.add_argument("--report", type=Path, help="Optional JSON source/cancellation ledger")
    args = parser.parse_args()
    if args.input.suffix != ".kmx" or args.output.suffix != ".kmx":
        parser.error("input and output must both have .kmx extensions")
    if args.input.resolve() == args.output.resolve():
        parser.error("output cannot overwrite input")
    if args.output.exists():
        parser.error("output exists; refusing to overwrite")
    if args.report is not None and (args.report.resolve() in
                                   {args.input.resolve(), args.output.resolve()} or args.report.exists()):
        parser.error("report path must be distinct and must not already exist")

    with args.input.open("r", encoding="utf-8", newline="") as f:
        source = f.read()
    optimized, report = optimize_text(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        f.write(optimized)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "certificates"}, indent=2))


if __name__ == "__main__":
    main()
