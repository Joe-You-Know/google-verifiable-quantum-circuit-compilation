"""Independent exhaustive truth-table regression for conservative KMX rewrites."""

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from causal_frontier_kmx import gate_signature, optimize_text


def classical_run(code: str, bits: tuple[int, ...]) -> tuple[int, ...]:
    """Separate basis-state interpreter; does not use the optimizer's frontier."""
    state = list(bits)
    for line in code.splitlines():
        s = line.split()
        if not s:
            continue
        kind, *wires = s
        if kind not in ("X", "CX", "CCX"):
            raise ValueError(f"unknown test operation: {kind}")
        positions = [int(x[1:]) for x in wires]
        if kind == "X":
            state[positions[0]] ^= 1
        elif kind == "CX":
            if state[positions[0]]:
                state[positions[1]] ^= 1
        elif state[positions[0]] and state[positions[1]]:
            state[positions[2]] ^= 1
    return tuple(state)


class FrontierTests(unittest.TestCase):
    def test_adjacent(self):
        result, r = optimize_text("CX q0 q1\nCX q0 q1\n")
        self.assertEqual(result, "")
        self.assertEqual(r["removed_gates"], {"CX": 2})

    def test_commute_across_disjoint_gate(self):
        result, r = optimize_text("CX q0 q1\nX q2\nCX q0 q1\n")
        self.assertEqual(result, "X q2\n")
        self.assertEqual(r["pairs_removed"], 1)

    def test_shared_wire_prevents_omission(self):
        code = "CX q0 q1\nX q0\nCX q0 q1\n"
        self.assertEqual(optimize_text(code)[0], code)

    def test_unknown_and_measurement_are_global_barriers(self):
        for barrier in ("HMR q0 b0", "CZ q2 q3 if b0", "R q0", 'REGISTER r0 "test"', "? q2"):
            code = f"CX q0 q1\n{barrier}\nCX q0 q1\n"
            self.assertEqual(optimize_text(code)[0], code)

    def test_cannot_cancel_conditioned_gate(self):
        code = "CX q0 q1 if b0\nCX q0 q1 if b0\n"
        self.assertIsNone(gate_signature(code.splitlines()[0]))
        self.assertEqual(optimize_text(code)[0], code)

    def test_nested_removals_restore_frontier(self):
        code = "X q0\nCX q0 q1\nCX q0 q1\nX q0\n"
        result, ledger = optimize_text(code)
        self.assertEqual(result, "")
        self.assertEqual(ledger["total_removed_gates"], 4)

    def test_preserve_nonremoved_bytes_and_newlines(self):
        code = '  REGISTER r0 "selection"\r\nX q0\r\n'
        self.assertEqual(optimize_text(code)[0], code)

    def test_exhaustive_random_classical_truth_tables(self):
        rng = random.Random(20261120)
        for trial in range(60):
            ops = []
            for _ in range(60):
                kind = rng.choice(("X", "CX", "CCX"))
                arity = {"X": 1, "CX": 2, "CCX": 3}[kind]
                wires = rng.sample(range(5), arity)
                ops.append(kind + " " + " ".join(f"q{n}" for n in wires))
            original = "\n".join(ops) + "\n"
            optimized, ledger = optimize_text(original)
            self.assertEqual(ledger["total_removed_gates"], 2 * ledger["pairs_removed"])
            for word in range(32):
                bits = tuple((word >> j) & 1 for j in range(5))
                self.assertEqual(classical_run(original, bits), classical_run(optimized, bits),
                                 f"trial {trial}, input {word}")


if __name__ == "__main__":
    unittest.main()
