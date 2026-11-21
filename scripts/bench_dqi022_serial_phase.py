#!/usr/bin/env python3
"""Experiment 022b: disprove or validate the serial one-bit Forney phase carrier.

The native reference is the original Kickmix field-product phase with all
located bits simultaneously constructed. The candidate is derived only from
GF(2) distributivity and creates each located source bit on demand.
No competition baseline files are altered.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np
import kickmix as km

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"scripts"),str(ROOT/"verifiers")]
from scripts.bench_dqi016_qday_rom_quotient import bool_bits, read_values
from research.dqi022_serial_forney import (
    serial_controlled_field_phase, build_serial_forney_circuit)
from research.dqi020_experimental_decoder import build_reference_circuit
from dqi.verify_submission_dqi import (
    ProblemSpecDQI, FieldTables, default_num_accepted_values,
    sample_shots, verify)


def circuit_digest(c):
    f=io.BytesIO()
    c.to_file(f,format="kmb")
    return hashlib.sha256(f.getvalue()).hexdigest()


def metric(c):
    return {"Q":int(c.num_qubits),
            "T_static":int(c.operation_statistics().num_toffoli_like),
            "operations":len(c)}


def build_phase_gadget(degree:int,mode:str):
    b=km.CircuitBuilder()
    a=b.create_quantum_register(degree,"omega")
    inv=b.create_quantum_register(degree,"inverse")
    flag=b.create_quantum_register(1,"flag")[0]
    mask=b.create_classical_register(degree,"mask")
    gf=km.GF2Field(degree)
    if mode=="original":
        located=b.alloc_qubits(degree)
        b.init_and(flag,a,located)
        b.gf2_phase_by_product(located,inv,mask=mask,field=gf)
        b.del_and(flag,a,located)
        b.free(located)
    elif mode=="serial":
        serial_controlled_field_phase(b,flag,a,inv,mask,gf)
    else:raise ValueError(mode)
    return b.finish_circuit(),(a,inv,flag,mask)


def phase_cases(degree,n,seed):
    domain=1<<degree
    if degree<=4:
        return [(a,b,c,h) for a in range(domain)
                for b in range(domain) for c in range(domain)
                for h in (0,1)]
    rng=np.random.default_rng(seed)
    cases=[(int(rng.integers(domain)),int(rng.integers(domain)),
            int(rng.integers(domain)),int(rng.integers(2)))
           for _ in range(n)]
    forced=[
        (0,0,0,0),(0,0,domain-1,1),(1,1,domain-1,1),
        (domain-1,domain-1,domain-1,1),
        (domain-1,domain-1,domain-1,0),
        (0,domain-1,domain-1,1),
        (domain-1,0,domain-1,1),
    ]
    return forced+cases


def native_basis_check(degree,mode,n,seed):
    circuit,registers=build_phase_gadget(degree,mode)
    omega,inverse,flag,mask=registers
    slots={int(q.id) for r in (omega,inverse) for q in r}
    slots.add(int(flag.id))
    work=km.array([km.q(i) for i in range(circuit.num_qubits)
                   if i not in slots])
    values=phase_cases(degree,n,seed)
    gf=km.GF2Field(degree)
    for start in range(0,len(values),128):
        pack=values[start:start+128]
        arr=np.array(pack,dtype=np.int64)
        sim=km.Simulator(batch_size=len(pack),debug_print=False,
                         counting_operations=False,seed=seed+start)
        sim.use_same_registers_as(circuit)
        sim.write_across_shots(omega,bool_bits(arr[:,0],degree))
        sim.write_across_shots(inverse,bool_bits(arr[:,1],degree))
        sim.write_across_shots(km.array([flag]),bool_bits(arr[:,3],1))
        sim.write_across_shots(mask,bool_bits(arr[:,2],degree))
        sim.do(circuit)
        phase=sim.read_phase_flipped_across_shots()
        original_omega=read_values(sim.read_across_shots(omega))
        original_inverse=read_values(sim.read_across_shots(inverse))
        original_flag=read_values(sim.read_across_shots(km.array([flag])))
        for i,(a,b,c,h) in enumerate(pack):
            expected=int(bool(h and ((gf.mul(a,b)&c).bit_count()&1)))
            if (int(phase[i]),int(original_omega[i]),
                int(original_inverse[i]),int(original_flag[i])) != (
                expected,a,b,h):
                raise AssertionError({"degree":degree,"mode":mode,"case":start+i,
                    "input":(a,b,c,h),"observed_phase":int(phase[i]),
                    "expected_phase":expected})
        if len(work) and np.any(sim.read_across_shots(work)):
            raise AssertionError(f"unreleased work for {mode} at {start}")
    return {"degree":degree,"mode":mode,
        "basis_cases":len(values),"status":"PASS",
        "correct_phase":True,"inputs_preserved":True,
        "scratch_zero":True,**metric(circuit)}


def native_dqi_check(n,m,shots,seed,confidence):
    if n>=m:raise ValueError("Official sampled verifier requires n<m")
    spec=ProblemSpecDQI(m=m,n=n,degree=12,
        r=default_num_accepted_values(12),num_shots=shots)
    shared=sample_shots(spec,FieldTables(km.GF2Field(12)),
                        np.random.default_rng(seed),shots)
    reports={}
    for mode in ("original","serial"):
        c=(build_reference_circuit(m,n,12,quotient_mode="norm_inverse")
           if mode=="original" else build_serial_forney_circuit(m,n,12))
        v=verify(c,spec,shots=shared,seed=seed,batch_size=128,
                 log2_delta=confidence,max_workers=1)
        reports[mode]={**metric(c),
            "verified_shots":v["verified_shots"],
            "status":v["status"],"value_errors":v["value_errors"],
            "phase_errors":v["phase_errors"],
            "mean_T":v["toffoli_count"],
            "score":v["score"],
            "circuit_sha256":v["circuit_sha256"]}
        print("DQI",mode,json.dumps(reports[mode]),flush=True)
        assert v["value_errors"]==0 and v["phase_errors"]==0
    return {"n":n,"m":m,"confidence_log2_delta":confidence,
        "shared_shots":True,
        "controls":reports,
        "difference":{key:reports["serial"][key]-reports["original"][key]
                      for key in ("Q","T_static","operations")},
        "status":"PASS"}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase-only",action="store_true")
    p.add_argument("--dqi-only",action="store_true")
    p.add_argument("--n",type=int,default=6)
    p.add_argument("--m",type=int,default=15)
    p.add_argument("--shots",type=int,default=512)
    p.add_argument("--seed",type=int,default=20261121)
    p.add_argument("--out",type=Path,default=Path("/tmp/dqi022_serial_phase.json"))
    a=p.parse_args()
    r={"experiment":"022b","mode":"own independent serial Forney phase",
       "competition_fullwidth_verifier":"NOT_RUN","reference_unchanged":True}
    if not a.dqi_only:
        r["gadget_basis"]=[
            native_basis_check(degree,mode,n=2048,seed=a.seed)
            for degree in (4,12)
            for mode in ("original","serial")
        ]
        print("GADGET",json.dumps(r["gadget_basis"]),flush=True)
    if not a.phase_only:
        r["dqi"]=native_dqi_check(a.n,a.m,a.shots,a.seed,-16)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    print("RECEIPT",str(a.out),flush=True)

if __name__=="__main__":main()
