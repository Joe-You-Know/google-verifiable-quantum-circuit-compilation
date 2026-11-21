#!/usr/bin/env python3
"""Experiment 026b: native rank-adaptive, original-source locator reconstruction.

The problem with Experiment 026a was not a phase or source-replay error:
lower-weight valid DQI syndromes have singular MAXIMUM-degree Hankel systems.
The source-conditional completion must accept the shortest witnessed
recurrence and reject missing constraints, not equate singularity to zero.

This native test creates and uncomputes candidate locator source polynomials
of degrees 0..max_degree, checks ALL syndrome equations and retains only a
few source-valid bits during selection. The same reversible circuit either:
  (1) exposes a coherent locator output register C+resolved for testing, or
  (2) uses it for a nontrivial phase and uncomputes ALL original scratch.
No per-step K polynomial history or quotient tape is retained.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gc
import json
from pathlib import Path
import sys

import numpy as np
import kickmix as km

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"scripts"),str(ROOT/"verifiers")]
from bench_dqi016_qday_rom_quotient import bool_bits,read_values
from research.dqi026_rank_adaptive import (
    build_rank_adaptive_locator,classical_minimal_locator)
from research.dqi026_hankel_locator import phase_usage
from dqi.verify_submission_dqi import (
    FieldTables,ProblemSpecDQI,default_num_accepted_values,sample_shots,
)
from audit_dqi023_recurrence import discrepancy_recurrence


def source_cases(degree,max_degree,num_random,num_official,seed):
    gf=km.GF2Field(degree)
    rng=np.random.default_rng(seed)
    q=1<<degree
    n=2*max_degree
    source=[]
    for ix in range(num_random):
        values=[int(x) for x in rng.integers(0,q,size=n)]
        if ix%8==0:values=[0]*n
        if ix%8==1:
            values=[0]*n;values[max_degree-1]=1
        if ix%8==2:values=[q-1]*n
        if ix%8==3:
            values=[0]*n;values[-1]=1
        source.append({"origin":"arbitrary_quantum_source",
                       "S":values})
    if num_official and degree==12:
        spec=ProblemSpecDQI(
            m=15,n=n,degree=12,r=default_num_accepted_values(12),
            num_shots=num_official)
        tables=FieldTables(gf)
        ss,_,_=sample_shots(
            spec,tables,rng,num_official)
        source.extend({
            "origin":"first_party_DQI_valid_error_source",
            "S":[int(x) for x in row]
        } for row in ss)
    return source


def native_test(degree,max_degree,cases,seed,probe):
    gf=km.GF2Field(degree)
    circuit,regs=build_rank_adaptive_locator(
        field_degree=degree,max_degree=max_degree,
        probe=probe)
    inputs={int(q.id) for block in regs["S"] for q in block}
    named=set(inputs)
    if probe:
        named.update(int(q.id)
                     for block in regs["locator"] for q in block)
        named.add(int(regs["resolved"].id))
    scratch=km.array([km.q(i) for i in range(circuit.num_qubits)
                      if i not in named])
    stats=circuit.operation_statistics()
    report={
        "degree":degree,"max_locator_degree":max_degree,
        "mode":"quantum_locator_probe" if probe else "phase_and_exact_reverse",
        "Q":int(circuit.num_qubits),
        "static_T":int(stats.num_toffoli_like),
        "ops":len(circuit),
        "original_named_source_Q":len(inputs),
        "histories_retained":{"polynomial_K":0,"field_quotient_F":0},
        "cases":len(cases),
        "original_source_changes":0,"scratch_not_zero":0,
        "phase_disagreements":0,
        "locator_value_disagreements":0,
        "resolved_flag_disagreements":0,
        "first_party_BM_coeff_disagreements":0,
        "first_party_valid_unresolved":0,
        "rank_counts":Counter(),
    }
    for start in range(0,len(cases),32):
        batch=cases[start:start+32]
        original=np.array([x["S"] for x in batch],dtype=np.int64)
        sim=km.Simulator(batch_size=len(batch),debug_print=False,
                         counting_operations=False,seed=seed+start)
        sim.use_same_registers_as(circuit)
        for i,reg in enumerate(regs["S"]):
            sim.write_across_shots(reg,bool_bits(original[:,i],degree))
        sim.do(circuit)
        for i,reg in enumerate(regs["S"]):
            report["original_source_changes"]+=int(np.count_nonzero(
                np.any(sim.read_across_shots(reg)^
                       bool_bits(original[:,i],degree),axis=0)))
        if len(scratch):
            report["scratch_not_zero"]+=int(np.count_nonzero(
                np.any(sim.read_across_shots(scratch),axis=0)))
        observed_phase=sim.read_phase_flipped_across_shots()
        if probe:
            locator=np.column_stack([
                read_values(sim.read_across_shots(reg))
                for reg in regs["locator"]])
            resolved=read_values(
                sim.read_across_shots(km.array([regs["resolved"]])))
        for ix,source in enumerate(batch):
            values=source["S"]
            v=classical_minimal_locator(gf,values,max_degree)
            report["rank_counts"][str(v["degree"]) if v["resolved"]
                                  else "unresolved"]+=1
            expected=bool(
                (int(v["coefficients"][0])&1)&(int(values[1])&1))
            if max_degree>1:
                expected^=bool(
                    ((int(v["coefficients"][1])>>1)&1)&
                    ((int(values[0])>>1)&1))
            if bool(observed_phase[ix]) != (
                    False if probe else expected):
                report["phase_disagreements"]+=1
            if probe:
                if [int(x) for x in locator[ix]] != v["coefficients"]:
                    report["locator_value_disagreements"]+=1
                if bool(resolved[ix])!=v["resolved"]:
                    report["resolved_flag_disagreements"]+=1
            if source["origin"]=="first_party_DQI_valid_error_source":
                if not v["resolved"]:
                    report["first_party_valid_unresolved"]+=1
                else:
                    true_c,ledger=discrepancy_recurrence(values,gf)
                    predicted=[1]+v["coefficients"][:len(true_c)-1]
                    if (v["degree"]!=len(true_c)-1
                            or predicted!=list(true_c)):
                        report["first_party_BM_coeff_disagreements"]+=1
        del sim
    report["rank_counts"]=dict(report["rank_counts"])
    report["status"]="PASS" if all(
        report[key]==0 for key in (
            "original_source_changes",
            "scratch_not_zero",
            "phase_disagreements",
            "locator_value_disagreements",
            "resolved_flag_disagreements",
            "first_party_BM_coeff_disagreements",
            "first_party_valid_unresolved")) else "FAIL"
    assert report["status"]=="PASS",report
    del circuit
    gc.collect()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--degree",type=int,choices=(4,12),default=4)
    p.add_argument("--max-degree",type=int,choices=(2,3),default=3)
    p.add_argument("--random",type=int,default=64)
    p.add_argument("--official",type=int,default=64)
    p.add_argument("--seed",type=int,default=20261121)
    p.add_argument("--out",type=Path,
                   default=Path("/tmp/dqi026_rank_adaptive.json"))
    a=p.parse_args()
    source=source_cases(
        a.degree,a.max_degree,a.random,
        a.official if a.degree==12 else 0,a.seed)
    entries=[]
    for probe in (True,False):
        r=native_test(a.degree,a.max_degree,source,a.seed,probe)
        entries.append(r)
        print("RANK_ADAPTIVE_NATIVE",json.dumps(r),flush=True)
    final={
        "experiment":"026b",
        "status":"PASS",
        "field_degree":a.degree,"max_degree":a.max_degree,
        "rank_control":"coherent smallest witnessed valid locator degree",
        "singular_larger_H":"not collapsed to absence of error",
        "source_K_polynomial_histories_retained":0,
        "source_quotient_histories_retained":0,
        "native":entries,
        "full_DQI":"NOT_BUILT",
        "large_degree_35_compiler":"NOT_FEASIBLE_WITH_FACTORIAL_DETERMINANTS",
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(final,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
