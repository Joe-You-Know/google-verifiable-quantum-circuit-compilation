#!/usr/bin/env python3
"""Indexed constructive Q-squared accounting for the official DQI qubit factor.

Do not confuse a scoring identity with a change to the verifier:
    Q^2 = sum_{i=1}^Q [ (i-1) row positions + (i-1) column positions
                       + one shared corner ].
Every stage and its three distinct sources remain in a traceable ledger.
Removing an actual qubit requires a *new valid circuit*, not merely dropping
one ledger entry. No modulus or unindexed operator identities are used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def construct_rows(Q: int) -> list[dict]:
    if not isinstance(Q, int) or isinstance(Q, bool) or Q < 0:
        raise ValueError("Q must be a nonnegative whole number")
    records = []
    accrued = 0
    for i in range(1, Q + 1):
        row_new = i - 1
        col_new = i - 1
        corner_new = 1
        appended = row_new + col_new + corner_new
        accrued += appended
        records.append({
            "stage_index": i,
            "row_source": {"occurrence": f"row_{i}", "new_positions": row_new},
            "column_source": {"occurrence": f"column_{i}", "new_positions": col_new},
            "corner_source": {"occurrence": f"corner_{i}_{i}", "new_positions": corner_new},
            "new_positions": appended,
            "cumulative_positions": accrued,
            "construction_status": "accounted",  # not a physical gate construction
        })
    if accrued != Q * Q:
        raise AssertionError("independently checked square count disagrees")
    return records


def occurrence_pairs(Q: int):
    """Yield each distinct ordered cell once, by its first construction stage.

    Intended for small-Q independent checking, not full-circuit compilation.
    """
    for i in range(1, Q + 1):
        for j in range(1, i):
            yield (i, j, i, "new_row")
            yield (j, i, i, "new_column")
        yield (i, i, i, "shared_corner")


def indexed_qubit_penalty(Q: int, removed: int = 0) -> dict:
    """Retain stage identities and the last-stage increments.

    When Q -> Q-removed, the removed *terminal stage labels* have the exact
    combined count sum_{i=Q-removed+1}^Q (2*i-1). An arbitrary physical qubit
    deletion must be recompiled and the surviving Q reindexed.
    """
    if not isinstance(removed, int) or isinstance(removed, bool) or not 0 <= removed <= Q:
        raise ValueError("removed must be a whole number between 0 and Q")
    rows = construct_rows(Q)
    survivors = rows[:Q-removed]
    dropped = rows[Q-removed:]
    penalty = sum(row["new_positions"] for row in rows)
    retained = sum(row["new_positions"] for row in survivors)
    saving = sum(row["new_positions"] for row in dropped)
    if penalty != retained + saving:
        raise AssertionError("missing source occurrence in indexed penalty ledger")
    return {
        "Q": Q,
        "Q_squared_scored_factor": penalty,
        "Q_after_recompile": Q - removed,
        "Q_squared_after_recompile": retained,
        "scored_factor_reduction": saving,
        "removed_qubits_requested": removed,
        "marginal_terminal_stage": 2 * Q - 1 if Q else 0,
        "indexed_rows": rows,
        "scope": ("Arithmetic accounting only. No actual reduction in qubits is "
                  "established until a new circuit satisfies the official verifier."),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qubits", type=int, default=1893)
    parser.add_argument("--remove", type=int, default=1)
    parser.add_argument("--report", type=Path,
                        default=Path("/tmp/vqcc_dqi_constructive_q_square.json"))
    args = parser.parse_args()
    if args.report.exists():
        parser.error("refusing to overwrite existing report")
    try:
        result = indexed_qubit_penalty(args.qubits, args.remove)
    except ValueError as ex:
        parser.error(str(ex))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "indexed_rows"},
                     indent=2))
    print(f"Retained {len(result['indexed_rows'])} individually indexed row records "
          f"in {args.report}")


if __name__ == "__main__":
    main()
