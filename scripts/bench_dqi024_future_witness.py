#!/usr/bin/env python3
"""Experiment 024b: quantum two-step external witness recovery.

Tests an *original, retained quantum source register* W that equals the
initial first polynomial's coefficient C0[1] on witnessed inputs.
The native reversible controlled recovery acts only when B1!=0 and
K1[1]!=0. Missing slope or denominator leaves the first carrier retained.
Wrong W does not silently erase it.

The external W register costs quantum storage unless it is proven to be
an existing retained source in the eventual DQI. Thus exact recovery
alone does NOT demonstrate memory reduction.
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
sys.path[:0]=[str(ROOT),str(ROOT/"scripts")]
from bench_dqi016_qday_rom_quotient import bool_bits,read_values
from scripts.bench_dqi024_quantum_carrier import source_cases
from research.dqi024_quantum_carrier import (
    build_dynamic_quantum_steps,classical_two,discrepancy_value)


def make_cases(gf,n,seed):
    cases=source_cases(gf.degree,2,n,seed)
    rng=np.random.default_rng(seed+29)
    field_max=1<<gf.degree
    tally={}
    for idx,case in enumerate(cases):
        kind=idx%8
        case["F"]=[0,0]
        if kind in (1,3,4,5,6,7):
            # Make the source slope 1, guaranteeing a distinct witness.
            case["K"][0][1]=1
        if kind==2:
            # Demonstrate a nonzero quotient with absent witness slope.
            case["K"][0][1]=0
            case["K"][0][0]=1
            case["K"][0][2]=0
            case["K"][0][3]=0
        if kind==0:
            # no quotient is constructed: explicit absent denominator
            case["B"][0]=0
        elif kind==4:
            # even erroneous W should be ignored when first b absent
            case["B"][0]=0
        else:
            b=discrepancy_value(
                gf,case["K"][0],case["S"],0)
            if not b:
                # S[3] was sampled nonzero: toggling K0 creates
                # an independently witnessed nonzero source denominator.
                case["K"][0][0]^=1
                b=discrepancy_value(gf,case["K"][0],case["S"],0)
            assert b
            case["B"][0]=b
        correct_w=int(case["C"][1])
        if kind in (3,4,7):
            w=correct_w^1
            label=("wrong_witness_nonzero_slope" if kind!=4
                   else "wrong_witness_absent_first_b")
        elif kind==2:
            w=correct_w
            label="missing_witness_slope"
        elif case["B"][0]==0:
            w=correct_w
            label="absent_first_b"
        else:
            w=correct_w
            label="valid_witness"
        case["W"]=w
        case["witness_label"]=label
        tally[label]=tally.get(label,0)+1
    return cases,tally


def recovered_value(gf,case,C_out,F_out):
    f1=int(F_out[0])
    if not case["B"][0] or not case["K"][0][1]:
        return f1
    relation=case["W"] ^ int(C_out[1])
    if case["B"][1]:
        relation ^= int(gf.mul(int(F_out[1]),int(case["K"][1][1])))
    inv=int(gf.pow(int(case["K"][0][1]),
                   (1<<gf.degree)-2))
    return f1^int(gf.mul(relation,inv))


def native_check(degree,roundtrip,cases,seed,witness_source):
    gf=km.GF2Field(degree)
    circuit,regs=build_dynamic_quantum_steps(
        degree=degree,steps=2,roundtrip=roundtrip,
        recover_first=("syndrome0" if witness_source=="syndrome0"
                       else True))
    named=[q for reg in [*regs["C"],*regs["S"],regs["W"]]
             for q in reg]
    named.extend(q for group in regs["K"] for reg in group for q in reg)
    named.extend(q for reg in [*regs["B"],*regs["F"]] for q in reg)
    nameds={int(q.id) for q in named}
    scratch=km.array([km.q(i) for i in range(circuit.num_qubits)
                      if i not in nameds])
    r={
       "degree":degree,"roundtrip":roundtrip,
       "witness_source":witness_source,
       "Q":circuit.num_qubits,
       "T_static":int(circuit.operation_statistics().num_toffoli_like),
       "operations":len(circuit),
       "cases":len(cases),"value_errors":0,"phase_errors":0,
       "source_K_S_B_W_changes":0,"dirty_scratch":0,
       "valid_witness_carrier_not_zero":0,
       "unresolved_nonzero_carrier_count":0,
       "wrong_witness_residual_detected":0,
       "absent_denominator_identity_cases":0,
    }
    for offset in range(0,len(cases),32):
        chunk=cases[offset:offset+32]
        arrays={}
        for name in ("C","S","K","B","F"):
            arrays[name]=np.array([x[name] for x in chunk],dtype=np.int64)
        w=np.array([x["W"] for x in chunk],dtype=np.int64)
        sim=km.Simulator(batch_size=len(chunk),debug_print=False,
                         counting_operations=False,seed=seed+offset)
        sim.use_same_registers_as(circuit)
        for i,reg in enumerate(regs["C"]):
            sim.write_across_shots(reg,bool_bits(arrays["C"][:,i],degree))
        for i,reg in enumerate(regs["S"]):
            sim.write_across_shots(reg,bool_bits(arrays["S"][:,i],degree))
        sim.write_across_shots(regs["W"],bool_bits(w,degree))
        for j in range(2):
            for name in ("B","F"):
                sim.write_across_shots(regs[name][j],
                    bool_bits(arrays[name][:,j],degree))
            for i,reg in enumerate(regs["K"][j]):
                sim.write_across_shots(reg,
                    bool_bits(arrays["K"][:,j,i],degree))
        sim.do(circuit)
        observed={
            "C":np.column_stack([read_values(
                sim.read_across_shots(reg)) for reg in regs["C"]]),
            "S":np.column_stack([read_values(
                sim.read_across_shots(reg)) for reg in regs["S"]]),
            "F":np.column_stack([read_values(
                sim.read_across_shots(reg)) for reg in regs["F"]]),
            "B":np.column_stack([read_values(
                sim.read_across_shots(reg)) for reg in regs["B"]]),
            "K":np.stack([np.column_stack([read_values(
                sim.read_across_shots(reg)) for reg in regs["K"][j]])
                for j in range(2)],axis=1),
            "W":read_values(sim.read_across_shots(regs["W"])),
        }
        r["phase_errors"]+=int(np.count_nonzero(
             sim.read_phase_flipped_across_shots()))
        if len(scratch):
            r["dirty_scratch"]+=int(np.count_nonzero(
                np.any(sim.read_across_shots(scratch),axis=0)))
        for t,case in enumerate(chunk):
            cc,ff=classical_two(gf,case["C"],case["K"],case["S"],
                               case["B"],case["F"])
            ff[0]=recovered_value(gf,case,cc,ff)
            if roundtrip:
                cc=case["C"]
                ff=case["F"]
            actualc=[int(v) for v in observed["C"][t]]
            actualf=[int(v) for v in observed["F"][t]]
            if actualc!=cc or actualf!=ff:
                r["value_errors"]+=1
            for field in ("S","B","K"):
                if not np.array_equal(observed[field][t],
                                     arrays[field][t]):
                    r["source_K_S_B_W_changes"]+=1
            if int(observed["W"][t])!=case["W"]:
                r["source_K_S_B_W_changes"]+=1

            if not roundtrip:
                label=case["witness_label"]
                if label=="valid_witness" and actualf[0]!=0:
                    r["valid_witness_carrier_not_zero"]+=1
                if label=="missing_witness_slope" and actualf[0]!=0:
                    r["unresolved_nonzero_carrier_count"]+=1
                if label=="wrong_witness_nonzero_slope" and actualf[0]!=0:
                    r["wrong_witness_residual_detected"]+=1
                if case["B"][0]==0:
                    assert actualf[0]==0
                    r["absent_denominator_identity_cases"]+=1
        del sim
    r["status"]="PASS" if not any(r[k] for k in (
        "value_errors","phase_errors","source_K_S_B_W_changes",
        "dirty_scratch","valid_witness_carrier_not_zero"
    )) else "FAIL"
    assert r["status"]=="PASS",r
    return r


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--degree",type=int,choices=(4,12),default=4)
    p.add_argument("--cases",type=int,default=128)
    p.add_argument("--witness-source",choices=("external","syndrome0"),
                   default="external")
    p.add_argument("--seed",type=int,default=20261121)
    p.add_argument("--out",type=Path,default=Path("/tmp/dqi024_recovery.json"))
    a=p.parse_args()
    gf=km.GF2Field(a.degree)
    cases,tally=make_cases(gf,a.cases,a.seed)
    if a.witness_source=="syndrome0":
        # Prepare a constrained source family. This is an explicit INPUT
        # promise for this experiment, not a generic DQI guarantee.
        for case in cases:
            case["W"]=case["S"][0]
            if "wrong_witness" in case["witness_label"]:
                case["C"][1]=case["W"]^1
            else:
                case["C"][1]=case["W"]
    results=[]
    for roundtrip in (False,True):
        result=native_check(a.degree,roundtrip,cases,a.seed,
                            a.witness_source)
        results.append(result)
        print("RECOVERY_NATIVE",json.dumps(result),flush=True)
        gc.collect()
    if results[0]["unresolved_nonzero_carrier_count"]==0:
        raise AssertionError("missing-slope branch was not distinguished")
    if results[0]["wrong_witness_residual_detected"]==0:
        raise AssertionError("false witness source inconsistency went undetected")
    r={
        "experiment":"024b","status":"PASS","field_degree":a.degree,
        "input_witness_conditions":tally,
        "witness_source":a.witness_source,
        "native_recovery":results,
        "law":"W+C2[1]+z2*F2*K2[1]=z1*F1*K1[1]",
        "branch_status":{
           "B1_zero":"carrier already zero for initial F1=0",
           "B1_nonzero_K1_coefficient_nonzero_W_correct":
               "carrier uncomputed",
           "B1_nonzero_K1_coefficient_zero":
               "carrier remains unresolved",
           "B1_nonzero_W_wrong":
               "residual source mismatch; do not free"
        },
        "witness_originally_retained":True,
        "physical_extra_W_qubits":(
            0 if a.witness_source=="syndrome0" else a.degree),
        "source_promise_C_initial_1_equals_S0":(
            a.witness_source=="syndrome0"),
        "end_to_end_ancilla_savings":"NOT_DEMONSTRATED",
        "full_DQI":"NOT_BUILT",
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
