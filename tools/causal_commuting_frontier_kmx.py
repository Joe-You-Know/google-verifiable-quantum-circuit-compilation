#!/usr/bin/env python3
"""Conservative overlapping-support omission for Kickmix text circuits.

Each X, CX or CCX toggles its target conditioned on zero, one or two controls.
Two such gates commute if neither target is a control of the other. Identical
involutions may cancel across only gates which commute with the candidate.

Unknown syntax, register metadata, measurements, phase, and conditioned gates
are global barriers. Never overwrite the original source circuit.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

_ARITY = {"X": 1, "CX": 2, "CCX": 3}
_QUBIT = re.compile(r"q(?:0|[1-9][0-9]*)\Z")


def candidate(line: str) -> tuple[str, ...] | None:
    terms = line.split()
    if not terms:
        return None
    arity = _ARITY.get(terms[0])
    if arity is None or len(terms) != arity + 1:
        return None
    if len(set(terms[1:])) != arity or not all(_QUBIT.fullmatch(w) for w in terms[1:]):
        return None
    return tuple(terms)


def optimize_text(source: str) -> tuple[str, dict]:
    """Apply source-witnessed pair omissions, failing closed at unknown syntax.

    For a candidate U with controls C and target t, an intervening V blocks
    movement of U if V writes any member of C or reads t as a control.
    Last target-write and last control-read events are retained even when
    a previously identified pair has been deleted. This can suppress
    additional cancellations but cannot authorize an invalid one.
    """
    lines = source.splitlines(keepends=True)
    out = list(lines)
    last_target: dict[str, int] = {}
    last_control: dict[str, int] = {}
    last_same: dict[tuple[str, ...], int | None] = {}
    prev_same: dict[int, int | None] = {}
    count: Counter[str] = Counter()
    certificates = []
    candidates = 0
    barriers = 0

    for i, line in enumerate(lines):
        sig = candidate(line)
        if sig is None:
            last_target.clear()
            last_control.clear()
            last_same.clear()
            barriers += 1
            continue

        candidates += 1
        target = sig[-1]
        controls = sig[1:-1]
        previous = last_same.get(sig)
        conflicting = [last_control.get(target, -1)]
        conflicting.extend(last_target.get(control, -1) for control in controls)

        if previous is not None and all(position < previous for position in conflicting):
            out[previous] = ""
            out[i] = ""
            count[sig[0]] += 2
            certificates.append({
                "gate": " ".join(sig),
                "source_lines": [previous + 1, i + 1],
                "reason": "intervening reversible gates neither write controls nor read target",
            })
            last_same[sig] = prev_same[previous]
            continue

        prev_same[i] = previous
        last_same[sig] = i
        last_target[target] = i
        for control in controls:
            last_control[control] = i

    optimized = "".join(line for line in out if line)
    return optimized, {
        "method": "commuting-target-control-frontier-v2",
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "optimized_sha256": hashlib.sha256(optimized.encode("utf-8")).hexdigest(),
        "candidate_gates": candidates,
        "barrier_lines": barriers,
        "removed_gates": dict(sorted(count.items())),
        "total_removed_gates": sum(count.values()),
        "pairs_removed": len(certificates),
        "certificates": certificates,
        "verification": "symbolic commuting-toggle proof; official Kickmix verifier NOT run",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.source.suffix != ".kmx" or args.output.suffix != ".kmx":
        parser.error("source and output must have .kmx extensions")
    if args.source.resolve() == args.output.resolve() or args.output.exists():
        parser.error("output must be new and different from the source")
    if args.report and (args.report.exists() or args.report.resolve() in
                        {args.source.resolve(), args.output.resolve()}):
        parser.error("report path must be new and distinct")

    with args.source.open("r", encoding="utf-8", newline="") as file:
        source = file.read()
    optimized, report = optimize_text(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        file.write(optimized)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "certificates"}, indent=2))


if __name__ == "__main__":
    main()
