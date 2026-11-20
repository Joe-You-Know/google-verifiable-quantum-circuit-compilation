#!/usr/bin/env python3
"""Experiment 004 stage B: score original and candidate chemistry families.

Calls the original unmodified dfthcsos.verify.verify() at every address;
defaults to the original 64 measurement shots per address. A source
numeric check alone never counts as circuit verification. All exceptions
are retained as candidate rejections in the JSON ledger.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "verifiers"), str(ROOT / "kickmix")]
from dfthcsos.verify import verify


def single(directory: Path, shots: int, seed: int | None):
    try:
        result = verify(directory, shots_per_address=shots, seed=seed)
        return {
            "name": directory.name,
            "status": "PASS",
            "score": result["score"],
            "toffoli_count": result["toffoli_count"],
            "num_qubits": result["num_qubits"],
            "brot": result["brot"],
            "batch_size": result["batch_size"],
            "num_circuits": result["num_circuits"],
            "verified_shots": result["verified_shots"],
            "submission_sha256": result["submission_sha256"],
            "metrics": result["metrics"],
            "resources": result["resources"],
        }
    except (AssertionError, ValueError, RuntimeError, OSError, KeyError, TypeError) as ex:
        return {"name": directory.name, "status": "FAIL",
                "error_type": type(ex).__name__, "error": str(ex)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path,
                        default=Path("sample_submission/dfthcsos"))
    parser.add_argument("--candidates", type=Path, default=Path("/tmp/vqcc_chem004_candidates"))
    parser.add_argument("--shots-per-address", type=int, default=64)
    parser.add_argument("--seed", type=int, help="optional explicit simulation seed")
    parser.add_argument("--report", type=Path, default=Path("/tmp/vqcc_chem004_verified.json"))
    args = parser.parse_args()
    if args.shots_per_address < 1:
        parser.error("shots-per-address must be positive")
    if args.report.exists():
        parser.error("refusing to overwrite report")
    if not args.baseline.is_dir():
        parser.error(f"baseline does not exist: {args.baseline}")

    directories = [args.baseline]
    if args.candidates.is_dir():
        directories.extend(sorted(x for x in args.candidates.iterdir()
                                  if x.is_dir() and (x / "submission.npz").is_file()))
    if len(directories) < 2:
        print("WARNING: no generated candidates; will still verify baseline", flush=True)

    outcomes = []
    for folder in directories:
        entry = single(folder, args.shots_per_address, args.seed)
        entry["source_directory"] = str(folder)
        outcomes.append(entry)
        print(json.dumps({key: value for key, value in entry.items()
                          if key not in ("metrics", "resources")}, sort_keys=True), flush=True)

    accepted = [x for x in outcomes if x["status"] == "PASS"]
    ranking = sorted(accepted, key=lambda x: x["score"])
    baseline_score = outcomes[0].get("score")
    summary = {
        "experiment": "004",
        "method": "unmodified official DFTHC-SOS verifier, user WSL local retained reference data",
        "shots_per_address": args.shots_per_address,
        "seed": args.seed,
        "candidate_statuses": outcomes,
        "best_pass": ranking[0]["name"] if ranking else None,
        "best_pass_score": ranking[0]["score"] if ranking else None,
        "baseline_score": baseline_score,
        "score_fractional_change_vs_baseline": (
            ranking[0]["score"] / baseline_score - 1
            if ranking and baseline_score else None
        ),
        "warning": "A PASS is scoped to the supplied official sampled verifier, not proof of all quantum branches.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(summary, indent=2, default=float) + "\n", encoding="utf-8")
    print(f"Saved: {args.report}")
    print(json.dumps({k: v for k, v in summary.items() if k != "candidate_statuses"}, indent=2))


if __name__ == "__main__":
    main()
