#!/usr/bin/env python3
"""DQI Experiment 005: record audited static resource baseline.

By default, only report on-disk file identity and size. Supplying --load
constructs the full (>600 MiB serialized) circuit and may require several
GiB of RAM. It does NOT run the official probabilistic DQI verifier.
No attempted optimization or correctness claim is made by this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--circuit", type=Path, default=Path("sample_submission/dqi.kmb"))
    p.add_argument("--load", action="store_true",
                   help="opt-in: load giant circuit and inspect register/cost metadata")
    p.add_argument("--report", type=Path, default=Path("/tmp/vqcc_dqi005_baseline.json"))
    args = p.parse_args()
    if not args.circuit.is_file():
        p.error(f"missing baseline circuit: {args.circuit}")
    if args.report.exists():
        p.error(f"refusing to overwrite report {args.report}")
    evidence = {
        "experiment": "005",
        "task": "DQI Reed-Solomon MBUC syndrome decoder",
        "circuit_source": str(args.circuit),
        "file_size_bytes": args.circuit.stat().st_size,
        "file_sha256": file_sha256(args.circuit),
        "verified_against_official_dqi_verifier": False,
        "scored_resource_improvement": "NOT_ESTABLISHED",
        "large_load_requested": args.load,
    }

    if args.load:
        sys.path[:0] = [str(ROOT / "verifiers"), str(ROOT / "kickmix")]
        import kickmix as km
        from dqi.verify_submission_dqi import ProblemSpecDQI, validate_registers
        circuit = km.Circuit.from_file(args.circuit, format=args.circuit.suffix[1:])
        spec = ProblemSpecDQI.benchmark_instance()
        validate_registers(circuit, spec)
        statistics = circuit.operation_statistics()
        evidence.update({
            "register_contract": "PASS",
            "benchmark_spec": {
                "m": spec.m, "n": spec.n, "degree": spec.degree, "r": spec.r,
            },
            "num_qubits": circuit.num_qubits,
            "num_classical_bits": circuit.num_bits,
            "num_ops": len(circuit),
            "reaction_depth": circuit.reaction_depth(),
            "static_toffoli_like": int(statistics.num_toffoli_like),
            "static_operations": dict(statistics),
            "note": "Static cost only. DQI score uses mean per-shot T and Clopper-Pearson R.",
        })

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2), flush=True)


if __name__ == "__main__":
    main()
