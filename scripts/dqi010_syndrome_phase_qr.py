#!/usr/bin/env python3
"""Experiment 010: direct syndrome-to-phase identity via polynomial QR.

For GF(2^b) at nonzero positions x_j, S_i = sum_j e_j*x_j^(i+1).
For each classical bit-mask M_j, choose its unique trace dual d_j such
that trace(d_j*e) equals the bitwise GF2 dot product of M_j and e.

Construct the classical polynomial F_M(X) of degree < q-1 satisfying
F_M(x_j) = d_j/x_j. Let L(X) = product_(j:e_j!=0) (X+x_j) and find the
polynomial quotient and remainder F_M = Q*L + R.
For each error root, R(x_j) = F_M(x_j). Hence:
  trace(sum_i R_i*S_i) = sum_j bitdot(M_j,e_j) over GF2.

This is an exact **mathematical** alternative to per-root Forney
inversion on finite toy examples. It does not claim a cheaper reversible
circuit: obtaining R from a quantum locator may itself be expensive.

Only powers of a field element use multiplicative group periodicity;
quotient and remainder are explicitly tracked, never flattened into
a single untyped index.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "kickmix"), str(ROOT / "verifiers")]
import kickmix as km


def field_trace(gf, x: int) -> int:
    current = x
    value = 0
    for _ in range(gf.degree):
        value ^= current
        current = gf.mul(current, current)
    if value not in (0, 1):
        raise AssertionError(f"field trace is not in GF2: {value}")
    return int(value)


def dual_masks(gf) -> list[int]:
    q = 1 << gf.degree
    duals = []
    for mask in range(q):
        matches = []
        for d in range(q):
            if all(
                field_trace(gf, gf.mul(d, 1 << bit)) == ((mask >> bit) & 1)
                for bit in range(gf.degree)
            ):
                matches.append(d)
        if len(matches) != 1:
            raise AssertionError("trace pairing not nondegenerate")
        duals.append(matches[0])
    return duals


def x_positions(gf) -> list[int]:
    order = (1 << gf.degree) - 1
    return [int(gf.pow(gf.primitive_element, j)) for j in range(order)]


def polynomial_evaluate(gf, coefficients: list[int], x: int) -> int:
    result = 0
    for c in reversed(coefficients):
        result = gf.mul(result, x) ^ c
    return result


def polynomial_multiply_monic_linear(gf, poly: list[int], root: int) -> list[int]:
    out = [0] * (len(poly) + 1)
    for i, c in enumerate(poly):
        out[i] ^= gf.mul(c, root)
        out[i + 1] ^= c
    return out


def polynomial_quotient_remainder(gf, numerator: list[int],
                                  divisor: list[int]) -> tuple[list[int], list[int]]:
    """Exact polynomial QR over a finite field; divisor must be monic."""
    if not divisor or divisor[-1] != 1:
        raise ValueError("expected monic divisor")
    working = list(numerator)
    while working and working[-1] == 0:
        working.pop()
    if len(working) < len(divisor):
        return [], working
    quotient = [0] * (len(working) - len(divisor) + 1)
    while working and len(working) >= len(divisor):
        if working[-1] == 0:
            working.pop()
            continue
        offset = len(working) - len(divisor)
        coefficient = working[-1]
        quotient[offset] ^= coefficient
        for i, d in enumerate(divisor):
            working[offset + i] ^= gf.mul(coefficient, d)
        while working and working[-1] == 0:
            working.pop()
    return quotient, working


def interpolation_coefficients(gf, masks: list[int],
                               duals: list[int], xs: list[int]) -> list[int]:
    """Source-only multiplicative DFT of the public mask values."""
    order = len(xs)
    if len(masks) != order:
        raise ValueError("mask length mismatch")
    coeffs = []
    for i in range(order):
        value = 0
        for j, x in enumerate(xs):
            quotient, rem = divmod((i + 1) * j, order)
            # x_j**(-(i+1)) = alpha**(-j*(i+1)) for x_j = alpha**j.
            negative_exp = 0 if rem == 0 else order - rem
            multiplier = gf.pow(gf.primitive_element, negative_exp)
            value ^= gf.mul(duals[masks[j]], multiplier)
        coeffs.append(value)
    return coeffs


def syndrome_phase(gf, error: dict[int, int], masks: list[int],
                   duals: list[int], xs: list[int]) -> dict:
    order = len(xs)
    if len(masks) != order:
        raise ValueError("invalid mask length")
    support = sorted(error)
    if any(j < 0 or j >= order or e <= 0 or e >= (1 << gf.degree)
           for j, e in error.items()):
        raise ValueError("invalid error position or value")

    classical_coeffs = interpolation_coefficients(gf, masks, duals, xs)
    for j, x in enumerate(xs):
        inverse_x = gf.pow(x, order - 1)
        value = gf.mul(duals[masks[j]], inverse_x)
        if polynomial_evaluate(gf, classical_coeffs, x) != value:
            raise AssertionError(f"classical interpolation counterexample at j={j}")

    if not support:
        return {"phase_direct": 0, "phase_remainder": 0,
                "locator_degree": 0, "remainder_coefficients": []}

    locator = [1]
    for j in support:
        locator = polynomial_multiply_monic_linear(gf, locator, xs[j])
    quotient, remainder = polynomial_quotient_remainder(gf, classical_coeffs, locator)
    # Quotient witness: verify F = Q*L + R coefficient-by-coefficient.
    reconstructed = [0] * max(len(classical_coeffs), len(quotient) + len(locator) - 1)
    for i, coefficient in enumerate(quotient):
        for j, lc in enumerate(locator):
            reconstructed[i + j] ^= gf.mul(coefficient, lc)
    for i, rc in enumerate(remainder):
        reconstructed[i] ^= rc
    if reconstructed[:len(classical_coeffs)] != classical_coeffs or any(
        reconstructed[len(classical_coeffs):]
    ):
        raise AssertionError("polynomial quotient-remainder reconstruction failed")

    syndromes = []
    for i in range(len(support)):
        value = 0
        for j in support:
            value ^= gf.mul(error[j], gf.pow(xs[j], i + 1))
        syndromes.append(value)

    paired = 0
    for i, coefficient in enumerate(remainder):
        paired ^= gf.mul(coefficient, syndromes[i])
    phase_qr = field_trace(gf, paired)
    phase_original = 0
    for j, value in error.items():
        phase_original ^= (int(value & masks[j]).bit_count() & 1)

    return {
        "phase_direct": phase_original,
        "phase_remainder": phase_qr,
        "locator_degree": len(support),
        "remainder_coefficients": remainder,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--degree", type=int, default=4)
    p.add_argument("--cases", type=int, default=1000)
    p.add_argument("--max-weight", type=int, default=3)
    p.add_argument("--seed", type=int, default=20261120)
    p.add_argument("--report", type=Path, default=Path("/tmp/vqcc_dqi010.json"))
    args = p.parse_args()
    if args.report.exists():
        p.error("refusing to overwrite report")
    gf = km.GF2Field(args.degree)
    xs = x_positions(gf)
    duals = dual_masks(gf)
    rng = random.Random(args.seed)
    q = 1 << args.degree

    weights = {i: 0 for i in range(args.max_weight + 1)}
    for trial in range(args.cases):
        weight = trial % (args.max_weight + 1)
        positions = rng.sample(range(len(xs)), weight)
        error = {j: rng.randrange(1, q) for j in positions}
        masks = [rng.randrange(q) for _ in xs]
        result = syndrome_phase(gf, error, masks, duals, xs)
        if result["phase_direct"] != result["phase_remainder"]:
            raise AssertionError(f"phase counterexample at trial={trial}")
        weights[weight] += 1
    receipt = {
        "experiment": "010",
        "field_degree": args.degree,
        "num_positions": len(xs),
        "cases": args.cases,
        "weight_counts": weights,
        "seed": args.seed,
        "result": "PASS",
        "claim_scope": "toy finite-field algebra only; no reversible circuit or Kaggle cost claim",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
