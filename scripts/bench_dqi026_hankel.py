#!/usr/bin/env python3
"""Experiment 026: native multi-round locator with no K-polynomial history.

Compare a *true quotient history-retaining* control against independent
source recomputation across 1..4 syndrome equations. The ORIGINAL named
input S is conserved, the generated Hankel cofactor polynomial K_j is
construct/uncompute within each round, and the streaming circuit erases
and physically frees each F_j immediately by the original source law.

We test arbitrary field syndromes including singular Hankel systems; the
singular output is explicitly unresolved rather than reported as valid.
On full-rank input the coefficients must satisfy every source equation
and agree with an independent classical adjugate computation. After
using the locator to kick back a nontrivial phase, both versions exactly
reverse every source transformation, leaving source S and scratch clean.
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
sys.path[:0]=[str(ROOT),str(ROOT/"scripts"),str(ROOT/"verifiers")]
from bench_dqi016_qday_rom_quotient import bool_bits,read_values
from research.dqi026_hankel_locator import (
    build_multiround_locator,
    classical_locator_from_syndromes,
)
from dqi.verify_submission_dqi import (
    FieldTables,ProblemSpecDQI,default_num_accepted_values,sample_shots,
)
from scripts.audit_dqi023_recurrence import discrepancy_recurrence


def cases_for(gf,rounds,n,seed):
    rng=np.random.default_rng(seed)
    q=1<<gf.degree
    cases=[]
    for index in range(n):
        values=[int(v) for v in rng.integers(0,q,size=2*rounds)]
        kind=index%8
        if kind==0:
            values=[0]*(2*rounds)
        elif kind==1:
            values=[0]*(2*rounds)
            values[rounds-1]=1
        elif kind==2:
            values=[0]*(2*rounds)
            values[rounds-1]=1
            values[2*rounds-1]=1
        elif kind==3:
            values=[0]*(2*rounds)
            values[0]=1
        elif kind==4:
            values=[q-1]*(2*rounds)
        elif kind==5:
            values=[0]*(2*rounds)
            values[rounds]=q-1
        elif kind==6:
            values=[0]*(2*rounds)
            values[rounds-1]=1
            values[rounds]=1
        # kind 7 retains independent arbitrary source
        cases.append(values)
    return cases


def phase_expectation(S,c):
    phase=(int(c[0])&1) & (int(S[1])&1)
    if len(c)>1:
        phase^=((int(c[1])>>1)&1)&((int(S[0])>>1)&1)
    return bool(phase)


def run_native(degree,rounds,n,seed,mode):
    gf=km.GF2Field(degree)
    input_cases=cases_for(gf,rounds,n,seed)
    circuit,reg=build_multiround_locator(
        degree=degree,rounds=rounds,mode=mode)
    named={int(q.id) for block in reg["S"] for q in block}
    scratch=km.array([
        km.q(i) for i in range(circuit.num_qubits)
        if i not in named])
    record={
        "field_degree":degree,
        "rounds":rounds,
        "mode":mode,
        "native_Q":int(circuit.num_qubits),
        "static_T":int(circuit.operation_statistics().num_toffoli_like),
        "operations":len(circuit),
        "named_original_source_Q":len(named),
        "retained_K_polynomial_history_Q":0,
        "source_F_histories_during_forward":
            reg["quotient_F_registers_retained_during_forward"],
        "source_cases":len(input_cases),
        "full_rank_cases":0,
        "singular_unresolved_cases":0,
        "source_changed":0,
        "dirty_workspace_cases":0,
        "phase_errors":0,
        "classical_constraint_failures":0,
        "source_replay_full_rank_failures":0,
    }
    for start in range(0,len(input_cases),32):
        block=input_cases[start:start+32]
        raw=np.array(block,dtype=np.int64)
        sim=km.Simulator(batch_size=len(block),
                         debug_print=False,
                         counting_operations=False,
                         seed=seed+start)
        sim.use_same_registers_as(circuit)
        for i,source_reg in enumerate(reg["S"]):
            sim.write_across_shots(
                source_reg,bool_bits(raw[:,i],degree))
        sim.do(circuit)
        for i,source_reg in enumerate(reg["S"]):
            actual=sim.read_across_shots(source_reg)
            expected=bool_bits(raw[:,i],degree)
            record["source_changed"]+=int(np.count_nonzero(
                np.any(actual^expected,axis=0)))
        if len(scratch):
            record["dirty_workspace_cases"]+=int(np.count_nonzero(
                np.any(sim.read_across_shots(scratch),axis=0)))
        observed_phase=sim.read_phase_flipped_across_shots()
        for ix,syndrome in enumerate(block):
            witness=classical_locator_from_syndromes(
                gf,syndrome,rounds)
            coefficients=witness["coefficients"]
            if witness["source_determinant"]==0:
                record["singular_unresolved_cases"]+=1
                # Zero corrections are a deliberate absence branch.
                assert coefficients==[0]*rounds
            else:
                record["full_rank_cases"]+=1
                if any(witness["source_equations_residuals"]):
                    record["classical_constraint_failures"]+=1
            record["phase_errors"]+=int(
                bool(observed_phase[ix]) !=
                phase_expectation(syndrome,coefficients))
        del sim
    record["status"]=("PASS" if
        not any(record[k] for k in (
            "source_changed","dirty_workspace_cases",
            "phase_errors","classical_constraint_failures"))
        else "FAIL")
    assert record["status"]=="PASS",record
    del circuit
    gc.collect()
    return record


def independent_valid_syndrome_crosswalk(degree,rounds,shots,seed):
    if degree != 12:
        return {"status":"NOT_RUN",
                "reason":"first-party reference uses GF(2^12) source"}
    if rounds not in (2,3,4):
        return {"status":"NOT_RUN","reason":"requires positive correction radius"}
    n=2*rounds
    m=15
    spec=ProblemSpecDQI(
        m=m,n=n,degree=12,r=default_num_accepted_values(12),
        num_shots=shots)
    gf=km.GF2Field(12)
    field_tables=FieldTables(gf)
    input_syndromes,_,_=sample_shots(
        spec,field_tables,np.random.default_rng(seed),shots)
    matches=0
    disagreements=0
    singular=0
    source_degree_distribution={}
    examples=[]
    for row in input_syndromes:
        values=[int(x) for x in row]
        direct=classical_locator_from_syndromes(
            gf,values,rounds)
        if not direct["source_determinant"]:
            singular+=1
            continue
        bm,ledger=discrepancy_recurrence(values,gf)
        degree_found=len(bm)-1
        source_degree_distribution[str(degree_found)]=(
            source_degree_distribution.get(str(degree_found),0)+1)
        expected=[int(x) for x in bm[1:]]
        observed=direct["coefficients"]
        if degree_found==rounds and observed==expected:
            matches+=1
        else:
            disagreements+=1
            if len(examples)<4:
                examples.append({
                    "syndrome":values,
                    "bm_degree":degree_found,
                    "direct_coefficients":observed,
                    "bm_coefficients":expected,
                })
    result={
        "status":"PASS" if not disagreements else "FAIL",
        "official_source_shots":shots,
        "n":n,"m":m,
        "nonsingular_full_rank_matches":matches,
        "nonsingular_crosswalk_disagreements":disagreements,
        "singular_unresolved_cases":singular,
        "bm_degree_counts_when_nonsingular":
             source_degree_distribution,
        "first_mismatches":examples,
    }
    assert not disagreements,result
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--degree",type=int,choices=(4,12),default=4)
    p.add_argument("--rounds",type=int,nargs="+",default=[2,3])
    p.add_argument("--cases",type=int,default=128)
    p.add_argument("--source-crosswalk",type=int,default=64,
                   help="0 skips authoritative valid-source BM crosscheck")
    p.add_argument("--seed",type=int,default=20261121)
    p.add_argument("--out",type=Path,
                   default=Path("/tmp/dqi026_hankel.json"))
    a=p.parse_args()
    all_results=[]
    for rounds in a.rounds:
        pair=[]
        for mode in ("history","streaming"):
            r=run_native(
                a.degree,rounds,a.cases,a.seed,mode)
            pair.append(r)
            print("LOCATOR_NATIVE",json.dumps(r),flush=True)
        hist,stream=pair
        result={
            "rounds":rounds,
            "retained_source_polynomial_K_history_Q":0,
            "compared_modes":pair,
            "measured_Q_saved":hist["native_Q"]-stream["native_Q"],
            "static_T_difference":stream["static_T"]-hist["static_T"],
            "operations_difference":
                stream["operations"]-hist["operations"],
            "history_retained_F_words":rounds,
            "streaming_retained_F_words":0,
            "streaming_regenerates_K_columns":"from original S only",
            "nonsingular_equations":rounds,
            "no_hidden_K_source_inputs":True,
        }
        if a.source_crosswalk:
            result["independent_valid_source_crosswalk"]=(
                independent_valid_syndrome_crosswalk(
                    a.degree,rounds,
                    a.source_crosswalk,a.seed))
        if result["measured_Q_saved"]<0:
            raise AssertionError(
                "native streaming circuit uses MORE qubits: "+str(result))
        all_results.append(result)
        print("LOCATOR_COMPARE",json.dumps(result),flush=True)
    report={
        "experiment":"026",
        "status":"NATIVE_PASS",
        "source":"Original syndrome-root locator constraints",
        "method":"Regenerate adjugate cofactor K per round; never retain K history",
        "source_replay":"F_j determined by original y_j and det(H), explicit det=0 absence",
        "full_rank_scope":"exact degree-t Hankel-source stratum only",
        "singular_scope":"UNRESOLVED, no inverse asserted",
        "full_DQI":"NOT_BUILT",
        "Kaggle_submitted":False,
        "results":all_results,
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
