#!/usr/bin/env python3
"""Experiment 026c: first-party DQI verifier for independent small decoder.

Exact native n6,m15 GF12 syndrome-source quantum circuit:
- canonical rank-adaptive locator;
- quantum source-only evaluator polynomial;
- Chien original field-root witnesses and derivative;
- native Forney quotient only where the inverse exists;
- phase from original classical error masks;
- full original source and ancilla cleanup.

No competitor circuit or lower-dimensional DQI class is imported.
The comparison to Experiment023 small benchmark is *resource context*:
a PASS only establishes full small-DQI correctness for this circuit.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import kickmix as km

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"verifiers"),str(ROOT/"scripts")]
from research.dqi026_independent_small_decoder import (
    build_small_independent_dqi)
from dqi.verify_submission_dqi import (
    ProblemSpecDQI,FieldTables,
    default_num_accepted_values,sample_shots,verify,
)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n",type=int,default=6)
    p.add_argument("--m",type=int,default=15)
    p.add_argument("--shots",type=int,default=512)
    p.add_argument("--seed",type=int,default=20261121)
    p.add_argument("--log2-delta",type=float,default=-16)
    p.add_argument("--out",type=Path,
                   default=Path("/tmp/dqi026_small_full_phase.json"))
    a=p.parse_args()
    if a.n!=6 or not 6<=a.m<=15 or a.shots%128:
        p.error("n=6, m=6..15 and shots divisible by 128 are required")

    print("COMPILE_SOURCE_ONLY_SMALL_DQI",json.dumps({
        "n":a.n,"m":a.m,"degree":12}),flush=True)
    circuit=build_small_independent_dqi(n=a.n,m=a.m,degree=12)
    stats=circuit.operation_statistics()
    print("NATIVE_SOURCE_RESOURCES",json.dumps({
        "Q":int(circuit.num_qubits),
        "T_static":int(stats.num_toffoli_like),
        "ops":len(circuit),
        "reaction_depth":circuit.reaction_depth(),
        "relative_baseline_023_small_Q":306,
        "relative_baseline_023_small_static_T":111353,
    }),flush=True)

    gf=km.GF2Field(12)
    spec=ProblemSpecDQI(
        m=a.m,n=a.n,degree=12,
        r=default_num_accepted_values(12),num_shots=a.shots)
    shots=sample_shots(
        spec,FieldTables(gf),np.random.default_rng(a.seed),
        a.shots)
    observed=verify(
        circuit,spec,shots=shots,seed=a.seed,
        batch_size=128,log2_delta=a.log2_delta,
        max_workers=1)
    report={
        "experiment":"026c",
        "implementation":"original source Hankel locator and quantum Forney",
        "no_persistent_polynomial_history":True,
        "no_persistent_quotient_history":True,
        "small_input_distribution":"first_party_sample_shots",
        "result":observed,
        "control_023_small_native_Q":306,
        "control_023_small_static_T":111353,
        "full_70x4095_decoder":"NOT_BUILT",
        "Kaggle_submission":"NOT_MADE",
        "correctness":"PASS" if observed["value_errors"]==0 and
                       observed["phase_errors"]==0 else "FAIL"
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("DQI026_SMALL_PHASE",json.dumps({
        k:observed[k] for k in (
            "status","num_qubits","max_toffoli_count",
            "toffoli_count","num_ops",
            "verified_shots","value_errors","phase_errors",
            "score","circuit_sha256"
        )}),flush=True)
    if report["correctness"]!="PASS":
        raise AssertionError("independent source circuit phase disagreement")


if __name__=="__main__":main()
