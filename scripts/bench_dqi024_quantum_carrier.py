#!/usr/bin/env python3
"""Native Kickmix test of Experiment024 quantum-valued K and b source shears.

Exercise b=0 and b!=0 with separate source occurrence witnesses, including
b=D(K,S) and intentionally inconsistent (B,K,S) source triples. The latter
checks the total reversible gate contract, not the recurrence model.
Two complete steps are tested both forward and in inverse order, including
clean scratch, unchanged K/S/B and source C/F restoration.
"""
from __future__ import annotations
import argparse
import gc
import json
import pathlib
import sys
import traceback

import numpy as np
import kickmix as km

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"scripts")]
from bench_dqi016_qday_rom_quotient import bool_bits,read_values
from research.dqi024_quantum_carrier import (
    build_dynamic_quantum_steps,classical_two,
    discrepancy_value,classical_witness_check)


def source_cases(degree,steps,n,seed):
    gf=km.GF2Field(degree)
    rng=np.random.default_rng(seed)
    domain=1<<degree
    cases=[]
    for index in range(n):
        S=[int(rng.integers(1,domain)) for _ in range(5)]
        C=[int(rng.integers(0,domain)) for _ in range(4)]
        K=[]; B=[]; F=[]; tags=[]
        for j in range(steps):
            f=int(rng.integers(0,domain))
            k=[int(rng.integers(0,domain)) for _ in range(4)]
            if index%4==0:
                b=0
                tag="absent_denominator_unconstrained"
            elif index%4==1:
                # Nonzero quantum K with exact source witness B=D(K,S)=0.
                t=0
                for i in range(3):
                    t^=int(gf.mul(k[i],S[j+3-i]))
                k[3]=int(gf.mul(t,int(gf.pow(S[j],domain-2))))
                assert discrepancy_value(gf,k,S,j)==0
                b=0
                tag="absent_denominator_witnessed"
            elif index%4==2:
                b=discrepancy_value(gf,k,S,j)
                if not b:
                    k[0]^=1
                    b=discrepancy_value(gf,k,S,j)
                assert b
                tag="nonzero_denominator_witnessed"
            else:
                b=int(rng.integers(1,domain))
                tag="nonzero_denominator_independent"
            K.append(k)
            B.append(b)
            F.append(f)
            tags.append(tag)
        cases.append({"C":C,"S":S,"K":K,"B":B,"F":F,"tags":tags})
    return cases


def run_native(degree,steps,n,seed,roundtrip):
    gf=km.GF2Field(degree)
    c,regs=build_dynamic_quantum_steps(
        degree=degree,steps=steps,roundtrip=roundtrip)
    cases=source_cases(degree,steps,n,seed)
    source_wires=[
        q for group in (regs["C"],regs["S"])
        for reg in group for q in reg
    ]
    source_wires.extend(q for group in regs["K"]
                        for reg in group for q in reg)
    source_wires.extend(q for group in (regs["B"],regs["F"])
                        for reg in group for q in reg)
    source_ids={int(q.id) for q in source_wires}
    scratch=km.array([km.q(i) for i in range(c.num_qubits)
                      if i not in source_ids])
    examined=0
    value_errors=0
    phase_errors=0
    dirty_workspace=0
    immutable_errors=0
    absent_errors=0
    first_failures=[]
    for start in range(0,n,32):
        chunk=cases[start:start+32]
        arr=np.array([x["C"] for x in chunk],dtype=np.int64)
        sarr=np.array([x["S"] for x in chunk],dtype=np.int64)
        karr=np.array([x["K"] for x in chunk],dtype=np.int64)
        barr=np.array([x["B"] for x in chunk],dtype=np.int64)
        farr=np.array([x["F"] for x in chunk],dtype=np.int64)
        sim=km.Simulator(batch_size=len(chunk),debug_print=False,
                         counting_operations=False,seed=seed+start)
        sim.use_same_registers_as(c)
        for i,r in enumerate(regs["C"]):
            sim.write_across_shots(r,bool_bits(arr[:,i],degree))
        for i,r in enumerate(regs["S"]):
            sim.write_across_shots(r,bool_bits(sarr[:,i],degree))
        for j in range(steps):
            sim.write_across_shots(regs["B"][j],
                                   bool_bits(barr[:,j],degree))
            sim.write_across_shots(regs["F"][j],
                                   bool_bits(farr[:,j],degree))
            for i,r in enumerate(regs["K"][j]):
                sim.write_across_shots(r,bool_bits(karr[:,j,i],degree))
        sim.do(c)
        observedC=np.column_stack([
            read_values(sim.read_across_shots(r)) for r in regs["C"]])
        observedF=np.column_stack([
            read_values(sim.read_across_shots(r)) for r in regs["F"]])
        observedS=np.column_stack([
            read_values(sim.read_across_shots(r)) for r in regs["S"]])
        observedB=np.column_stack([
            read_values(sim.read_across_shots(r)) for r in regs["B"]])
        observedK=np.stack([
            np.column_stack([read_values(sim.read_across_shots(reg))
                              for reg in regs["K"][j]])
            for j in range(steps)],axis=1)
        phase_errors+=int(np.count_nonzero(
            sim.read_phase_flipped_across_shots()))
        if len(scratch):
            dirty_workspace+=int(np.count_nonzero(
                np.any(sim.read_across_shots(scratch),axis=0)))
        for ix,case in enumerate(chunk):
            expectedC,expectedF=classical_two(
                gf,case["C"],case["K"],case["S"],case["B"],case["F"])
            if roundtrip:
                expectedC,expectedF=case["C"],case["F"]
            gotC=[int(x) for x in observedC[ix]]
            gotF=[int(x) for x in observedF[ix]]
            if (gotC,gotF)!=(expectedC,expectedF):
                value_errors+=1
                if len(first_failures)<4:
                    first_failures.append({"index":start+ix,
                      "tags":case["tags"],"inputs":case,
                      "expected":(expectedC,expectedF),
                      "observed":(gotC,gotF)})
            if (not np.array_equal(observedS[ix],sarr[ix])
                or not np.array_equal(observedB[ix],barr[ix])
                or not np.array_equal(observedK[ix],karr[ix])):
                immutable_errors+=1
            if steps==1 and case["B"][0]==0:
                if gotC!=case["C"] or gotF!=case["F"]:
                    absent_errors+=1
            examined+=1
        del sim
    packet={
      "degree":degree,"steps":steps,"roundtrip":roundtrip,
      "qubits":c.num_qubits,
      "static_toffoli_like":int(c.operation_statistics().num_toffoli_like),
      "native_operations":len(c),
      "basis_cases":examined,
      "value_errors":value_errors,
      "phase_errors":phase_errors,
      "immutable_K_S_B_changes":immutable_errors,
      "dirty_workspace_cases":dirty_workspace,
      "absent_branch_changes":absent_errors,
      "absent_b_count":sum(sum(x["B"][j]==0
                              for j in range(steps)) for x in cases),
      "witness_consistent_b_count":sum(sum(
         x["B"][j]==discrepancy_value(gf,x["K"][j],x["S"],j)
         for j in range(steps)) for x in cases),
      "first_failures":first_failures,
      "status":"PASS" if not any((value_errors,phase_errors,
           immutable_errors,dirty_workspace,absent_errors)) else "FAIL",
    }
    assert packet["status"]=="PASS",packet
    return packet


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--degree",type=int,choices=(4,12),default=4)
    p.add_argument("--cases",type=int,default=128)
    p.add_argument("--seed",type=int,default=20261121)
    p.add_argument("--out",type=pathlib.Path,
                   default=pathlib.Path("/tmp/dqi024_dynamic.json"))
    a=p.parse_args()
    results=[]
    for steps in (1,2):
        for roundtrip in (False,True):
            r=run_native(a.degree,steps,a.cases,a.seed,roundtrip)
            results.append(r)
            print("DYNAMIC_NATIVE",json.dumps(r),flush=True)
            gc.collect()
    gf=km.GF2Field(a.degree)
    witness=classical_witness_check(gf)
    print("TWO_STEP_WITNESS",json.dumps(witness),flush=True)
    assert witness["complete_output_distinct"]==(1<<a.degree)
    assert witness["after_forgetting_first_carrier_distinct"]==1
    packet={
        "experiment":"024","status":"PASS",
        "quantum_registers":["C","K","S","B","F"],
        "field_degree":a.degree,
        "native_tests":results,"future_constraint_test":witness,
        "recurrence_relation_DK_equals_b_is_test_input_constraint":True,
        "fully_dynamic_dqi_decoder":"NOT_BUILT",
        "witness_register_in_accepted_DQI":"NOT_IDENTIFIED",
        "competing_public_circuits_copied":False,
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(packet,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
