#!/usr/bin/env python3
"""Experiment023: native source-counter width falsification, not a score claim.

Run all candidates against shared original-spec sampled DQI shots. A candidate
that fails is recorded as a counterexample, not concealed or accepted. Small
baseline KMB must equal exact independent 022c source KMB.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import io
import json
from pathlib import Path
import sys
import traceback

import numpy as np
import kickmix as km

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"verifiers"),str(ROOT/"scripts")]
from research.dqi023_metadata_width import (
    WIDTH_MODES,selected_widths,build_width_mode_circuit)
from dqi.verify_submission_dqi import (
    ProblemSpecDQI,FieldTables,default_num_accepted_values,
    sample_shots,verify)


EXPECTED_BASELINE_SMALL_SHA="9d43e33992d75de05782ba65a04b2eef1b5c26680c1a55cfae4dbcbfdbc7d72f"


def sha_kmb(c):
    f=io.BytesIO()
    c.to_file(f,format="kmb")
    return hashlib.sha256(f.getvalue()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n",type=int,default=6)
    p.add_argument("--m",type=int,default=15)
    p.add_argument("--degree",type=int,default=12)
    p.add_argument("--modes",nargs="+",choices=WIDTH_MODES,
                   default=list(WIDTH_MODES))
    p.add_argument("--shots",type=int,default=512)
    p.add_argument("--seed",type=int,default=20261121)
    p.add_argument("--confidence",type=float,default=-16)
    p.add_argument("--out",type=Path,default=Path("/tmp/dqi023_width.json"))
    a=p.parse_args()
    if a.degree!=12 or not (2<=a.n<=a.m<=4095):
        p.error("n/m/degree outside native authenticated DQI range")
    if a.shots and (a.n>=a.m or a.shots%128):
        p.error("phase samples require n<m and shot count multiple of 128")
    shared=None
    if a.shots:
        spec=ProblemSpecDQI(m=a.m,n=a.n,degree=12,
            r=default_num_accepted_values(12),num_shots=a.shots)
        shared=sample_shots(spec,FieldTables(km.GF2Field(12)),
                            np.random.default_rng(a.seed),a.shots)
    results=[]
    for mode in a.modes:
        info={"mode":mode,"widths":selected_widths(a.n,mode),
              "native_build":"NOT_RUN","sampled_verifier":"NOT_RUN"}
        try:
            circuit=build_width_mode_circuit(a.m,a.n,12,mode)
            info["native_build"]="PASS"
            info["Q"]=int(circuit.num_qubits)
            info["T_static"]=int(circuit.operation_statistics().num_toffoli_like)
            info["operations"]=len(circuit)
            if a.shots:
                info["circuit_sha256"]=sha_kmb(circuit)
                if mode=="baseline" and (a.n,a.m)==(6,15):
                    if info["circuit_sha256"]!=EXPECTED_BASELINE_SMALL_SHA:
                        raise AssertionError(
                            "metadata copy baseline KMB NOT byte-exact 022c")
                    info["022c_byte_identical"]=True
                v=verify(circuit,spec,shots=shared,seed=a.seed,batch_size=128,
                         log2_delta=a.confidence,max_workers=1)
                info["sampled_verifier"]={k:v[k] for k in (
                    "status","num_qubits","verified_shots","value_errors",
                    "phase_errors","max_toffoli_count","toffoli_count",
                    "score","log2_delta","circuit_sha256")}
                info["valid_development_sample"]=(
                    v["status"]=="PASS" and not v["value_errors"]
                    and not v["phase_errors"])
                if mode=="baseline" and not info["valid_development_sample"]:
                    raise AssertionError("original controls failed")
            else:
                info["valid_development_sample"]="NOT_RUN"
        except Exception as exc:
            info["failure"]={"error_type":type(exc).__name__,
                "message":str(exc),"traceback_tail":traceback.format_exc()[-1500:]}
            if mode=="baseline":raise
        results.append(info)
        print("WIDTH_CASE",json.dumps(info),flush=True)
        if "circuit" in locals():
            del circuit
            gc.collect()
    base=next((i for i in results if i["mode"]=="baseline"),None)
    if base is None:base=next((i for i in results if i.get("native_build")=="PASS"),None)
    if base is not None:
        for i in results:
            if i.get("native_build")=="PASS":
                i["Q_vs_first_mode"]=i["Q"]-base["Q"]
                i["T_vs_first_mode"]=i["T_static"]-base["T_static"]
    record={
       "experiment":"023","n":a.n,"m":a.m,"degree":a.degree,
       "phase_shots":a.shots,"seed":a.seed,
       "confidence":a.confidence if a.shots else "NOT_RUN",
       "public_component_reuse":False,
       "correctness_gate":"sampled only, not full-confidence proof",
       "results":results,
       "candidate_outcomes":{x["mode"]:x.get("valid_development_sample", "NOT_RUN")
                              for x in results},
       "experiment_status":"DIAGNOSTIC_COMPLETED",
       "competition_102400_shot_verifier":"NOT_RUN"
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    print("REPORT",json.dumps({"path":str(a.out),
        "candidate_outcomes":record["candidate_outcomes"]}),flush=True)


if __name__=="__main__":main()
