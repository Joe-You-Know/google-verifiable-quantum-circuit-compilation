#!/usr/bin/env python3
"""Experiment 020 — feature-flagged norm-inverse quotient in synchronized DQI EEA.

Runs source-identical original-versus-gated experimental decoder comparisons.
No production source modification. The disabled experimental copy must be
byte-for-byte identical to the official reference circuit at the small fixture.

Modes:
  --n 6 --m 15 [default] : compile and sampled official verifier API
  --n 70 --m 70 --compile-only : benchmark-width static resource comparison

The sampled verifier is only a development control. Its default experiment
confidence is deliberately less stringent than the competition benchmark.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np
import kickmix as km

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"scripts"),str(ROOT/"verifiers")]
from dqi.dqi_reference_circuit import build_reference_circuit as build_official
from research.dqi020_experimental_decoder import build_reference_circuit as build_exp
from dqi.verify_submission_dqi import (
    ProblemSpecDQI, FieldTables, default_num_accepted_values,
    sample_shots, verify
)

def digest(c):
    f=io.BytesIO()
    c.to_file(f,format="kmb")
    return hashlib.sha256(f.getvalue()).hexdigest()

def metrics(c):
    stats=c.operation_statistics()
    return {"qubits":int(c.num_qubits),
            "static_toffoli_like":int(stats.num_toffoli_like),
            "total_operations":len(c)}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n",type=int,default=6)
    ap.add_argument("--m",type=int,default=15)
    ap.add_argument("--degree",type=int,default=12)
    ap.add_argument("--shots",type=int,default=512)
    ap.add_argument("--batch-size",type=int,default=128)
    ap.add_argument("--log2-delta",type=float,default=-16.0)
    ap.add_argument("--seed",type=int,default=20261120)
    ap.add_argument("--compile-only",action="store_true")
    ap.add_argument("--resource-only",action="store_true",
                    help="Skip large kmb serialization/hashes, report native Q/T/ops only")
    ap.add_argument("--outdir",type=Path,default=Path("/tmp/vqcc_dqi020"))
    args=ap.parse_args()
    if args.degree!=12:ap.error("candidate is authenticated for degree 12 only")
    if args.compile_only:
        if not (2<=args.n<=args.m<=(1<<args.degree)-1):
            ap.error("compile-only requires 2<=n<=m<=4095")
    elif not (2<=args.n<args.m<=(1<<args.degree)-1):
        ap.error("sampled verifier requires 2<=n<m<=4095")
    if args.resource_only and not args.compile_only:
        ap.error("--resource-only requires --compile-only")
    if not args.compile_only and (args.shots<1 or args.shots%args.batch_size):
        ap.error("shots must be positive multiple of batch size")
    args.outdir.mkdir(parents=True,exist_ok=True)
    result={
        "experiment":"020",
        "parameters":{"n":args.n,"m":args.m,"degree":args.degree},
        "gadget_native_precondition":"Experiment 019 run 44843260760 PASS, 109/390 vs 81/270",
        "reference_decoder_unchanged":True,
        "experimental_feature_flag_only":True,
    }
    original=build_official(args.m,args.n,args.degree)
    result["original"]=metrics(original)
    if not args.resource_only:
        result["original"]["circuit_sha256"]=digest(original)
        original.to_file(str(args.outdir/"original.kmb"),format="kmb")
    print("ORIGINAL",json.dumps(result["original"]),flush=True)
    if args.n<=10 and args.m<=20 and not args.resource_only:
        disabled=build_exp(args.m,args.n,args.degree,quotient_mode="reference")
        check=digest(disabled)==result["original"]["circuit_sha256"]
        result["disabled_mode_byte_exact_reference"]=check
        if not check:
            raise AssertionError("experimental disabled-mode diverges from official source")
        del disabled
        gc.collect()
    else:
        result["disabled_mode_byte_exact_reference"]="NOT_TESTED_AT_THIS_WIDTH"
    if args.resource_only:
        # Avoid holding two enormous compiled circuit objects simultaneously.
        del original
        gc.collect()
    candidate=build_exp(args.m,args.n,args.degree,quotient_mode="norm_inverse")
    result["candidate"]=metrics(candidate)
    if not args.resource_only:
        result["candidate"]["circuit_sha256"]=digest(candidate)
        candidate.to_file(str(args.outdir/"norm_inverse.kmb"),format="kmb")
    print("CANDIDATE",json.dumps(result["candidate"]),flush=True)
    result["difference"]={key:result["candidate"][key]-result["original"][key]
        for key in ("qubits","static_toffoli_like","total_operations")}
    result["theoretical_local_28_qubit_change_not_assumed"]=True
    if not args.compile_only:
        spec=ProblemSpecDQI(m=args.m,n=args.n,degree=args.degree,
            r=default_num_accepted_values(args.degree),num_shots=args.shots)
        rng=np.random.default_rng(args.seed)
        shared_shots=sample_shots(spec,FieldTables(km.GF2Field(args.degree)),
                                  rng,args.shots)
        for name,circuit in (("original",original),("candidate",candidate)):
            audit=verify(circuit,spec,shots=shared_shots,seed=args.seed,
                batch_size=args.batch_size,log2_delta=args.log2_delta,max_workers=1)
            result[name+"_sampled_verifier"]={
                key:audit[key] for key in
                ("status","num_qubits","verified_shots","value_errors",
                 "phase_errors","toffoli_count","max_toffoli_count",
                 "effective_error_rate","score","log2_delta")}
            print(name.upper()+" VERIFIED",
                  json.dumps(result[name+"_sampled_verifier"]),flush=True)
        result["common_shots_for_both"]=True
        result["full_benchmark_verifier"]="NOT_RUN"
        result["verifier_scope"]=(
            "Official verifier API called with reduced n/m and log2_delta "
            "for isolated integration; not a 4095-position official submission")
    else:
        result["sampled_phase_verifier"]="NOT_RUN"
        result["full_benchmark_verifier"]="NOT_RUN"
    path=args.outdir/"experiment_020.json"
    path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("RESULT",json.dumps(result),flush=True)

if __name__=="__main__":
    main()
