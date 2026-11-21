#!/usr/bin/env python3
"""Run unmodified official Invsqrt verifier on generated precision candidates.

This runner deliberately uses a 32-shot smoke check, NOT the full benchmark.
Report both passes and failures; never silently discard failed candidates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("precision_report", type=Path)
    p.add_argument("--output", type=Path, default=Path("/tmp/vqcc_precision_smoke.json"))
    a = p.parse_args()
    if a.output.exists():
        p.error("refusing to overwrite an existing smoke report")
    source = json.loads(a.precision_report.read_text(encoding="utf-8"))
    results = []
    for candidate in source["candidates"]:
        item = {
            "candidate": candidate["name"],
            "precision": candidate["precision"],
            "sample_status": candidate["sample"]["status"],
            "full_domain_status": candidate.get("full", {}).get("status", "NOT_RUN"),
            "full_domain_checked": candidate.get("full", {}).get("entire_domain_checked", False),
            "static_toffoli_like": candidate.get("static_toffoli_like"),
            "num_qubits": candidate.get("num_qubits"),
        }
        circuit_file = candidate.get("circuit_path")
        if not circuit_file:
            item["smoke_status"] = "NOT_BUILT"
            results.append(item)
            continue
        if candidate.get("full", {}).get("entire_domain_checked") is not True:
            item["smoke_status"] = "SKIPPED_NO_FULL_DOMAIN_NUMERICAL_PASS"
            results.append(item)
            continue
        cmd = [
            sys.executable,
            str(ROOT / "verifiers/invsqrt/verify_submission_invsqrt.py"),
            circuit_file,
            "--max-x", "16",
            "--shots-per-x", "2",
            "--batch-size", "16",
            "--max-workers", "1",
            "--seed", "20261120",
        ]
        attempt = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 check=False, timeout=300)
        try:
            parsed = json.loads(attempt.stdout)
        except json.JSONDecodeError:
            parsed = {"status": "ERROR", "stdout_tail": attempt.stdout[-1000:]}
        item["smoke_status"] = parsed.get("status", "ERROR")
        item["smoke_exit_code"] = attempt.returncode
        item["smoke_score"] = parsed.get("score")
        item["smoke_toffoli_count"] = parsed.get("toffoli_count")
        item["smoke_num_qubits"] = parsed.get("num_qubits")
        item["smoke_circuit_sha256"] = parsed.get("circuit_sha256")
        item["smoke_error"] = parsed.get("error") or (attempt.stderr[-1000:] if attempt.returncode else None)
        results.append(item)
        print(json.dumps(item, sort_keys=True), flush=True)
    receipt = {
        "experiment": "003",
        "simulation": "supplied unmodified Invsqrt verifier",
        "settings": {
            "max_x": 16, "shots_per_x": 2,
            "batch_size": 16, "max_workers": 1, "seed": 20261120,
        },
        "full_official_benchmark": False,
        "results": results,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Saved official 32-shot smoke-test receipt: {a.output}")


if __name__ == "__main__":
    main()
