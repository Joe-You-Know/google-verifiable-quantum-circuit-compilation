#!/usr/bin/env python3
"""Targeted Kickmix simulator audit at difficult Invsqrt x values.

Reuses the unmodified official verifier's reference phase values, tolerance,
register validation and bit-packing. This is a targeted additional check,
NOT the official full-domain, 64-shots-per-x benchmark.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "verifiers"), str(ROOT / "kickmix")]

import numpy as np
import kickmix as km
from invsqrt.verify_submission_invsqrt import (
    ProblemSpecInvSqrt,
    validate_registers,
    reference_values,
    to_bits,
    from_bits,
    half_turns_to_units,
)

N_P = 10
MAX_X = 3 * (2**N_P - 2)**2


def inputs(focus: list[int], span: int, boundaries: bool) -> list[int]:
    values = set(range(1, 17))
    for n in focus:
        values.update(range(n - span, n + span + 1))
    if boundaries:
        for exponent in range(2 * N_P + 2):
            t = 1 << exponent
            values.update((t - 1, t, t + 1))
    return sorted(x for x in values if 1 <= x <= MAX_X)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("circuit", type=Path)
    p.add_argument("--focus-x", type=int, action="append", default=[])
    p.add_argument("--span", type=int, default=2)
    p.add_argument("--shots", type=int, default=64)
    p.add_argument("--seed", type=int, default=20261120)
    p.add_argument("--boundaries", action="store_true")
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    if args.span < 0 or args.shots < 1:
        p.error("--span must be nonnegative and --shots must be positive")
    if args.report and args.report.exists():
        p.error("refusing to overwrite report")

    circuit = km.Circuit.from_file(args.circuit, format=args.circuit.suffix.lstrip("."))
    spec = ProblemSpecInvSqrt.for_n_p(N_P)
    x_register, scratch = validate_registers(circuit, spec)
    chosen = inputs(args.focus_x, args.span, args.boundaries)
    if not chosen:
        p.error("no admissible input values")

    worst = (-1.0, None)
    total_shots = 0
    failures = []
    for index, x in enumerate(chosen):
        xs = np.full(args.shots, x, dtype=np.uint64)
        target, tolerance = reference_values(spec, np.array([x], dtype=np.uint64))
        sim = km.Simulator(batch_size=args.shots, debug_print=False,
                           counting_operations=True, seed=args.seed + index)
        sim.clear_for_shot()
        sim.write_across_shots(x_register, to_bits(xs, spec.width))
        sim.do(circuit)

        if not np.array_equal(from_bits(sim.read_across_shots(x_register)), xs):
            failures.append({"x": x, "error": "input register not restored"})
            continue
        if len(scratch) and sim.read_across_shots(scratch).any():
            failures.append({"x": x, "error": "scratch register nonzero"})
            continue

        theta = np.array([half_turns_to_units(sim.read_shot_phase(j))
                          for j in range(args.shots)], dtype=np.uint64)
        errors = (theta - target[0]).view(np.int64)
        used = np.abs(errors).view(np.uint64)
        allowed = tolerance[0]
        if (used > allowed).any():
            failures.append({
                "x": x,
                "error": "phase tolerance exceeded",
                "maximum_error_units": int(used.max()),
                "allowed_units": int(allowed),
            })
        ratio = float(used.max()) / int(allowed)
        if ratio > worst[0]:
            worst = (ratio, x)
        total_shots += args.shots

    report = {
        "scope": "targeted official-phase-function simulator check, NOT full official benchmark",
        "status": "FAIL" if failures else "PASS",
        "circuit": str(args.circuit),
        "circuit_file_sha256": hashlib.sha256(args.circuit.read_bytes()).hexdigest(),
        "tested_input_count": len(chosen),
        "tested_inputs": chosen,
        "shots_per_input": args.shots,
        "shots_evaluated": total_shots,
        "seed": args.seed,
        "worst_error_over_tolerance": worst[0],
        "worst_x": worst[1],
        "failures": failures,
    }
    print(json.dumps({k: v for k, v in report.items() if k != "tested_inputs"}, indent=2))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
