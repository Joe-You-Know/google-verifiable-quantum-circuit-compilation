"""Independent basis-state tests for target/control commutation optimization."""

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from causal_commuting_frontier_kmx import optimize_text


def classical_run(code: str, basis: tuple[int, ...]) -> tuple[int, ...]:
    """An independent interpreter, not derived from frontier bookkeeping."""
    s = list(basis)
    for line in code.splitlines():
        terms = line.split()
        if not terms:
            continue
        kind, *registers = terms
        if kind not in ("X", "CX", "CCX"):
            raise ValueError(kind)
        wires = [int(q[1:]) for q in registers]
        enabled = 1
        for control in wires[:-1]:
            enabled &= s[control]
        s[wires[-1]] ^= enabled
    return tuple(s)


class CommutingFrontierTests(unittest.TestCase):
    def test_shared_target(self):
        original = "CCX q0 q1 q2\nCX q3 q2\nCCX q0 q1 q2\n"
        optimized, receipt = optimize_text(original)
        self.assertEqual(optimized, "CX q3 q2\n")
        self.assertEqual(receipt["removed_gates"], {"CCX": 2})

    def test_shared_control(self):
        original = "CCX q0 q1 q2\nCX q0 q3\nCCX q0 q1 q2\n"
        self.assertEqual(optimize_text(original)[0], "CX q0 q3\n")

    def test_true_control_dependencies_block(self):
        for middle in ("CX q2 q3", "CX q3 q0", "X q1", "CCX q2 q3 q4"):
            original = f"CCX q0 q1 q2\n{middle}\nCCX q0 q1 q2\n"
            self.assertEqual(optimize_text(original)[0], original)

    def test_phase_measurement_and_unknown_are_barriers(self):
        for middle in ("CZ q0 q1", "HMR q1 b0", "R q2",
                       "X q0 if b0", 'REGISTER r0 "x"'):
            original = f"CCX q0 q1 q2\n{middle}\nCCX q0 q1 q2\n"
            self.assertEqual(optimize_text(original)[0], original)

    def test_3200_exhaustive_truth_tables(self):
        rng = random.Random(20261120)
        for trial in range(100):
            original = "\n".join(
                " ".join([kind] + [
                    f"q{wire}" for wire in rng.sample(
                        range(5), {"X": 1, "CX": 2, "CCX": 3}[kind])
                ])
                for kind in (rng.choice(("X", "CX", "CCX")) for _ in range(60))
            ) + "\n"
            optimized, receipt = optimize_text(original)
            self.assertEqual(receipt["total_removed_gates"], 2 * receipt["pairs_removed"])
            for word in range(32):
                basis = tuple((word >> i) & 1 for i in range(5))
                self.assertEqual(
                    classical_run(original, basis),
                    classical_run(optimized, basis),
                    f"trial {trial}, input {word}",
                )


if __name__ == "__main__":
    unittest.main()
