#!/usr/bin/env python3
"""Experiment 023c: full basis-source comparison on arbitrary syndrome inputs.

The DQI verifier's sampled phase law is defined on <=n/2-error syndromes.
A reversible circuit, however, exists on arbitrary quantum syndrome input.
This falsification test generates arbitrary 12-bit syndrome vectors including
unreachable patterns and compares our exact 022c control to narrowed variants,
while checking full syndrome restoration and zero work on each separately.
No statement of arbitrary-domain equivalence is inferred from successful
ordinary verifier shots alone.
"""
from __future__ import annotations
import argparse
import gc
import json
from pathlib import Path
import sys
import numpy as np
import kickmix as km

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"verifiers")]
from dqi.verify_submission_dqi import (
    ProblemSpecDQI,default_num_accepted_values,
    validate_registers,to_bits)
from research.dqi023_metadata_width import build_width_mode_circuit


def test_one_mode(n,m,degree,mode,source,mask,seed):
    c=build_width_mode_circuit(m,n,degree,mode)
    spec=ProblemSpecDQI(m=m,n=n,degree=degree,
         r=default_num_accepted_values(degree),num_shots=len(source))
    syndromes,mbuc,junk=validate_registers(c,spec)
    arrS=km.array(syndromes)
    arrE=km.array(mbuc)
    phases=[]
    dirty=0
    changed=0
    for k in range(0,len(source),64):
        source_chunk=source[k:k+64]
        mask_chunk=mask[k:k+64]
        bs=len(source_chunk)
        sim=km.Simulator(batch_size=bs,debug_print=False,
             counting_operations=False,seed=seed+k)
        sim.use_same_registers_as(c)
        bsS=to_bits(source_chunk,degree)
        bsE=to_bits(mask_chunk,degree)
        sim.write_across_shots(arrS,bsS)
        sim.write_across_shots(arrE,bsE)
        sim.do(c)
        phases.extend(bool(x) for x in sim.read_phase_flipped_across_shots())
        changed+=int(np.count_nonzero(np.any(
            sim.read_across_shots(arrS)^bsS,axis=0)))
        if len(junk):
            dirty+=int(np.count_nonzero(np.any(
                sim.read_across_shots(junk),axis=0)))
        del sim
    out={"mode":mode,"Q":int(c.num_qubits),
         "T_static":int(c.operation_statistics().num_toffoli_like),
         "operations":len(c),"syndrome_changed_shots":changed,
         "nonzero_workspace_shots":dirty,
         "arbitrary_syndrome_cases":len(source)}
    del c
    gc.collect()
    return out,np.array(phases,dtype=bool)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n",type=int,default=6)
    p.add_argument("--m",type=int,default=15)
    p.add_argument("--degree",type=int,default=12)
    p.add_argument("--shots",type=int,default=256)
    p.add_argument("--seed",type=int,default=20261121)
    p.add_argument("--out",type=Path,default=Path("/tmp/dqi023_arbitrary.json"))
    a=p.parse_args()
    if a.shots%64 or a.degree!=12: p.error("shots must be divisible by 64; degree=12")
    rng=np.random.default_rng(a.seed)
    source=rng.integers(0,1<<12,size=(a.shots,a.n),dtype=np.int64)
    mask=rng.integers(0,1<<12,size=(a.shots,a.m),dtype=np.int64)
    # Forced source-specific counterexamples; not all necessarily decodable.
    source[0,:]=0
    source[1,:]=(1<<12)-1
    source[2,:]=0; source[2,-1]=1
    source[3,:]=0; source[3,0]=1
    source[4,:]=np.arange(a.n,dtype=np.int64)
    records=[]
    known_ref_phase=None
    for mode in ("baseline","both_pairs","all_narrow"):
        obs,phase=test_one_mode(a.n,a.m,a.degree,mode,source,mask,a.seed)
        if known_ref_phase is None:
            known_ref_phase=phase
            obs["phase_vs_baseline"]=0
        else:
            obs["phase_vs_baseline"]=int(np.count_nonzero(phase^known_ref_phase))
            obs["first_phase_mismatch_indices"]=np.flatnonzero(
                phase^known_ref_phase)[:16].tolist()
        obs["full_basis_check_status"]=(
            "EQUIVALENT_ON_TESTED_INPUTS"
            if not obs["syndrome_changed_shots"]
            and not obs["nonzero_workspace_shots"]
            and not obs["phase_vs_baseline"]
            else "COUNTEREXAMPLE_OBSERVED")
        records.append(obs)
        print("ARBITRARY_SYNDROME",json.dumps(obs),flush=True)
    report={"experiment":"023c","n":a.n,"m":a.m,
       "arbitrary_syndrome_shots":a.shots,
       "input_distribution":"uniform independent GF(2^12) with forced zero/far-bit patterns",
       "full_domain_exhaustive":False,
       "accepted_error_source_assumed":False,
       "cases":records,
       "correctness_status":"FALSIFICATION_DIAGNOSTIC_NOT_PROOF"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
