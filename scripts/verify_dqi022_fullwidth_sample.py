#!/usr/bin/env python3
"""Full-dimension DQI sample for independently derived serial Forney phase.

Use 70 syndrome/4095 positions and the native reference verifier API. This is
a falsification screen with deliberately reduced confidence; it MUST NOT be
reported as the competition's official 102400-shot verification.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import kickmix as km

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"scripts"),str(ROOT/"verifiers")]
from research.dqi022_serial_forney import (
    build_serial_forney_circuit, build_sparse_serial_forney_circuit
)
from dqi.verify_submission_dqi import (
    ProblemSpecDQI, default_num_accepted_values, verify)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--shots",type=int,default=512)
    p.add_argument("--variant",choices=("serial","combined"),default="serial")
    p.add_argument("--batch-size",type=int,default=128)
    p.add_argument("--log2-delta",type=float,default=-16)
    p.add_argument("--seed",type=int,default=20261121)
    p.add_argument("--out",type=Path,
                   default=Path("/tmp/dqi022_fullwidth_sample.json"))
    a=p.parse_args()
    if a.shots<=0 or a.shots%a.batch_size:
        p.error("shots must be positive and divisible by batch-size")
    print("BUILDING 70x4095",a.variant,"FORNEY CANDIDATE",flush=True)
    ctor=(build_serial_forney_circuit if a.variant=="serial"
          else build_sparse_serial_forney_circuit)
    circuit=ctor(4095,70,12)
    static=circuit.operation_statistics()
    print("COMPILED",json.dumps({
        "Q":circuit.num_qubits,
        "T_static":static.num_toffoli_like,
        "operations":len(circuit)}),flush=True)
    spec=ProblemSpecDQI(
        m=4095,n=70,degree=12,
        r=default_num_accepted_values(12),num_shots=a.shots)
    v=verify(circuit,spec,seed=a.seed,batch_size=a.batch_size,
             log2_delta=a.log2_delta,max_workers=1)
    if v["value_errors"] or v["phase_errors"]:
        raise AssertionError("observed errors: "+str({
            "value":v["value_errors"],"phase":v["phase_errors"]}))
    report={
       "experiment":"022b" if a.variant=="serial" else "022c",
       "variant":a.variant,
       "status":v["status"],
       "native_dimensions":{"m":4095,"n":70,"degree":12},
       "verification_scope":"Full-dimension, reduced-shot development sample",
       "required_competition_102400_shots":"NOT_RUN",
       "user_experiment020_source_unchanged":True,
       "verified_shots":v["verified_shots"],
       "seed":a.seed,"log2_delta":a.log2_delta,
       "value_errors":v["value_errors"],
       "phase_errors":v["phase_errors"],
       "num_qubits":v["num_qubits"],
       "static_toffoli_like":v["max_toffoli_count"],
       "mean_toffoli_like":v["toffoli_count"],
       "num_ops":v["num_ops"],
       "reaction_depth":v["reaction_depth"],
       "development_score":v["score"],
       "circuit_sha256":v["circuit_sha256"]
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("FULL_DIMENSION_PHASE_SAMPLE",json.dumps(report),flush=True)


if __name__=="__main__":
    main()
