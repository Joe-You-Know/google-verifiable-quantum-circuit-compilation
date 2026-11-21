#!/usr/bin/env python3
"""Experiment023 full official-confidence native DQI validation, own decoder only.

This is the exact supplied verifier API at n70 m4095 degree12, 102400 shots,
log2_delta -128 and one worker. It does not assemble a Kaggle ZIP or submit.
Save status, structural source widths, all numerical verifier fields, and
circuit SHA256; baseline Experiment020 and 022c remain untouched.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import kickmix as km

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"verifiers")]
from research.dqi023_metadata_width import (
    build_width_mode_circuit,selected_widths)
from dqi.verify_submission_dqi import (
    ProblemSpecDQI,default_num_accepted_values,verify)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=["both_pairs","all_narrow"],
                   default="all_narrow")
    p.add_argument("--shots",type=int,default=102400)
    p.add_argument("--batch-size",type=int,default=256)
    p.add_argument("--log2-delta",type=float,default=-128.0)
    p.add_argument("--max-workers",type=int,default=1)
    p.add_argument("--out",type=Path,default=Path("/tmp/dqi023_official_confidence.json"))
    a=p.parse_args()
    n,m,degree=70,4095,12
    print("BUILD_SOURCE",a.mode,selected_widths(n,a.mode),flush=True)
    circuit=build_width_mode_circuit(m,n,degree,a.mode)
    print("NATIVE_STATIC",json.dumps({
        "Q":circuit.num_qubits,
        "T_static":circuit.operation_statistics().num_toffoli_like,
        "operations":len(circuit)
    }),flush=True)
    spec=ProblemSpecDQI(m=m,n=n,degree=degree,
         r=default_num_accepted_values(degree),num_shots=a.shots)
    result=verify(circuit,spec,batch_size=a.batch_size,
                  log2_delta=a.log2_delta,max_workers=a.max_workers)
    if result["value_errors"] or result["phase_errors"]:
        raise AssertionError("nonzero phase/value errors observed")
    packet={"experiment":"023","kind":"full_official_confidence_native_DQI",
            "implementation":"own independently narrowed metadata 022c",
            "mode":a.mode,"widths":selected_widths(n,a.mode),
            "user_kaggle_submitted":False,"third_party_circuits_included":False,
            "verifier":result}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(packet,indent=2)+"\n",encoding="utf-8")
    print("FULL_OFFICIAL_VERIFIER",json.dumps({
        k:result[k] for k in (
        "status","score","num_qubits","max_toffoli_count",
        "toffoli_count","verified_shots","log2_delta",
        "value_errors","phase_errors","effective_error_rate",
        "repetition_factor","reaction_depth","num_ops",
        "circuit_sha256")}),flush=True)


if __name__=="__main__":main()
