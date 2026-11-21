#!/usr/bin/env python3
"""Experiment 025: internal quantum source relation, adaptive slope, and Q reuse.

Only original named quantum syndromes and K polynomials are input. C and
the B source denominators are *constructed within* Kickmix from these
sources; no caller-supplied promised relation is needed.

Benchmark two identical quantum identity circuits:
  (A) retain the cleaned F1 through a meaningful 12-field-word future
      source product stage;
  (B) physically free the cleaned F1, allocate those same future words,
      uncompute them, reallocate F1, reconstruct its old value and reverse
      the complete source history.
Count native physical peak, not logical source labels.

Both are checked on the EXACT same arbitrary S,K source basis states,
including every sole nonzero K1 coefficient, null b1, nonzero K1 with
zero D(K1,S), and other independently generated patterns.
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
sys.path[:0]=[str(ROOT),str(ROOT/"scripts")]
from bench_dqi016_qday_rom_quotient import bool_bits
from research.dqi024_quantum_carrier import discrepancy_value
from research.dqi025_internal_witness_reuse import (
    build_internal_witness_circuit,
)


def generate_sources(degree, n, seed):
    gf=km.GF2Field(degree)
    upper=1<<degree
    rng=np.random.default_rng(seed)
    records=[]
    for t in range(n):
        S=[int(rng.integers(1,upper)) for _ in range(5)]
        K=[[int(rng.integers(upper)) for _ in range(4)]
           for _ in range(2)]
        tag=""
        if t%8==0:
            K[0]=[0,0,0,0]
            tag="zero_first_K_and_absent_first_b"
        elif 1<=t%8<=4:
            j=t%8-1
            K[0]=[0,0,0,0]
            K[0][j]=1
            S[3-j]=1
            tag=f"only_first_slope_{j}_nonzero"
        elif t%8==5:
            # Nonzero K1; force exact D1(K1,S)=0.
            K[0]=[1,0,0,0]
            K[0][1]=int(gf.mul(S[3],
                                 int(gf.pow(S[2],upper-2))))
            assert discrepancy_value(gf,K[0],S,0)==0
            tag="first_K_nonzero_but_first_b_absent"
        elif t%8==6:
            K[0]=[0,1,0,0]
            S[2]=1
            K[1]=[0,0,0,0]
            tag="first_b_nonzero_second_b_absent"
        else:
            tag="random_both_quantum_polynomials"
        b1=discrepancy_value(gf,K[0],S,0)
        b2=discrepancy_value(gf,K[1],S,1)
        expected_index=next(
            (i for i,x in enumerate(K[0]) if x),None
        ) if b1 else None
        if b1:
            assert expected_index is not None
        records.append({
            "S":S,"K":K,"b1":b1,"b2":b2,
            "selected_coefficient":expected_index,"tag":tag
        })
    return records


def verify_circuit(degree,cases,release_first,workspace_words,seed):
    c,reg=build_internal_witness_circuit(
        degree=degree,release_first=release_first,
        workspace_words=workspace_words)
    original_source_ids={
        int(q.id)
        for block in [*reg["S"],*(k for group in reg["K"] for k in group)]
        for q in block
    }
    scratch=km.array([km.q(i) for i in range(c.num_qubits)
                      if i not in original_source_ids])
    fields={
        "release_first":release_first,
        "Q":int(c.num_qubits),
        "T_static":int(c.operation_statistics().num_toffoli_like),
        "operations":len(c),
        "source_cases":len(cases),
        "source_qubits":len(original_source_ids),
        "source_changed":0,
        "unclean_workspace":0,
        "unexpected_phase":0,
        "original_F1_slots":list(reg["original_f1_physical_ids"]),
        "first_reallocated_future_word_slots":list(reg["first_future_word_ids"]),
        "reconstructed_F1_slots":list(reg["reallocated_f1_physical_ids"]),
        "F1_slots_reused_by_future_word":reg[
            "released_F1_slot_reused_by_future_word"
        ],
        "F1_slots_reused_by_reconstruction":reg[
            "physical_F1_ids_reused"
        ],
    }
    for offset in range(0,len(cases),32):
        chunk=cases[offset:offset+32]
        sv=np.array([x["S"] for x in chunk],dtype=np.int64)
        kv=np.array([x["K"] for x in chunk],dtype=np.int64)
        sim=km.Simulator(batch_size=len(chunk),debug_print=False,
                         counting_operations=False,seed=seed+offset)
        sim.use_same_registers_as(c)
        for i,sreg in enumerate(reg["S"]):
            sim.write_across_shots(sreg,bool_bits(sv[:,i],degree))
        for j in range(2):
            for i,kreg in enumerate(reg["K"][j]):
                sim.write_across_shots(kreg,bool_bits(kv[:,j,i],degree))
        sim.do(c)
        for i,sreg in enumerate(reg["S"]):
            fields["source_changed"]+=int(np.count_nonzero(
                np.any(sim.read_across_shots(sreg)^
                       bool_bits(sv[:,i],degree),axis=0)))
        for j in range(2):
            for i,kreg in enumerate(reg["K"][j]):
                fields["source_changed"]+=int(np.count_nonzero(
                    np.any(sim.read_across_shots(kreg)^
                           bool_bits(kv[:,j,i],degree),axis=0)))
        if len(scratch):
            fields["unclean_workspace"]+=int(np.count_nonzero(
                np.any(sim.read_across_shots(scratch),axis=0)))
        fields["unexpected_phase"]+=int(np.count_nonzero(
            sim.read_phase_flipped_across_shots()))
        del sim
    fields["status"]="PASS" if not any(fields[k] for k in (
        "source_changed","unclean_workspace","unexpected_phase"
    )) else "FAIL"
    assert fields["status"]=="PASS",fields
    return fields


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--degree",type=int,default=4,choices=(4,12))
    p.add_argument("--cases",type=int,default=128)
    p.add_argument("--workspace-words",type=int,default=12)
    p.add_argument("--seed",type=int,default=20261121)
    p.add_argument("--out",type=Path,
                   default=Path("/tmp/dqi025_internal_source.json"))
    a=p.parse_args()
    cases=generate_sources(a.degree,a.cases,a.seed)
    counts=Counter(item["tag"] for item in cases)
    selected=Counter(
        "absent" if item["selected_coefficient"] is None
        else str(item["selected_coefficient"])
        for item in cases)
    results=[]
    for release in (False,True):
        r=verify_circuit(a.degree,cases,release,
                         a.workspace_words,a.seed)
        results.append(r)
        print("NATIVE_INTERNAL_WITNESS",json.dumps(r),flush=True)
        gc.collect()
    control,candidate=results
    comparison={
        "control_Q":control["Q"],"released_Q":candidate["Q"],
        "physical_peak_Q_saved":control["Q"]-candidate["Q"],
        "T_static_difference":candidate["T_static"]-control["T_static"],
        "instructions_difference":candidate["operations"]-control["operations"],
        "released_F1_slot_reused_by_future_word":
            candidate["F1_slots_reused_by_future_word"],
        "original_named_sources_extra_witness_qubits":0,
        "exact_reversible_forward_and_reverse":True,
    }
    # Require meaningful measured physical improvement; a simple
    # equality of source labels is not an adequate resource result.
    assert comparison["physical_peak_Q_saved"]>0,comparison
    report={
        "experiment":"025",
        "source_relation":"C0[i] is constructed by CX(S[i],C[i]) for all four i",
        "denominator_relation":"B_j constructed by D_j(K_j,S)",
        "selector":"smallest original coefficient index i with K1[i]!=0",
        "source_domain":"ALL named S,K quantum basis inputs",
        "test_domain":"finite small or randomized native basis cases",
        "full_domain_exhaustive":False,
        "constructions":[control,candidate],
        "source_branch_types":dict(counts),
        "selected_slope_counts":dict(selected),
        "comparison":comparison,
        "full_DQI_decoder":"NOT_BUILT",
        "kaggle_submission":"NOT_MADE",
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("EXPERIMENT025_RESULT",json.dumps({
        "field_degree":a.degree,"test_cases":a.cases,
        "source_branch_types":dict(counts),
        "selected_slope_counts":dict(selected),
        "comparison":comparison
    }),flush=True)


if __name__=="__main__":
    main()
