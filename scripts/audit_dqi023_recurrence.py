#!/usr/bin/env python3
"""Experiment 023b: independent causal recurrence of syndrome error support.

This is a CLASSICAL source-identity/provenance experiment, not a quantum
circuit, a scoreboard calculation or a copied implementation. It derives
the linear recurrence from the supplied DQI syndrome contract:

  S_i = XOR_j e_j * x_j^(i+1), with x_j = alpha^j.

The error locator L(z)=PRODUCT_j (1 + x_j*z) implies
  XOR_{h=0..k} L_h*S_{i-h} = 0 for i >= k.

Construct the shortest recurrence (Berlekamp-Massey updates), then an
evaluator O(z) = truncated L(z) * syndrome-series. At a root z=1/x_j,
the original source error value is O(z)/L'(z), with no assumed
conventional integer remainder. All zero denominators have explicit
nonconstruction branches. Compare against independent verifier shots.

This proves a bounded *classical* source face on valid <=n/2 error inputs.
It DOES NOT prove a reversible/clean-work quantum decoder, nor that the
bound remains valid for arbitrary 70-word input syndrome superpositions.
"""
from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path
import sys

import numpy as np
import kickmix as km
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"verifiers"))
from dqi.verify_submission_dqi import (
    FieldTables, ProblemSpecDQI,
    default_num_accepted_values,sample_shots,
)


def field_inverse(field, value:int):
    if value == 0:raise ZeroDivisionError("No constructed inverse at zero")
    return int(field.pow(int(value),(1<<field.degree)-2))


def field_product(field,a,b):
    return int(field.mul(int(a),int(b)))


def discrepancy_recurrence(syndromes,field):
    """Exact GF2 field recurrence, preserving each distinct source update."""
    n=len(syndromes)
    C=[1]+[0]*n
    B=[1]+[0]*n
    L=0
    shift=1
    prev_d=1
    ledger=[]
    for step in range(n):
        discrepancy=int(syndromes[step])
        for j in range(1,L+1):
            discrepancy ^= field_product(field,C[j],syndromes[step-j])
        rec={
            "index":step,"L_before":L,
            "discrepancy_nonzero":bool(discrepancy),
            "shift_before":shift,
            "created_inverse":bool(discrepancy),
        }
        if discrepancy == 0:
            shift+=1
            rec["action"]="no_update_witnessed_zero"
        else:
            ratio=field_product(field,discrepancy,
                                field_inverse(field,prev_d))
            old=C[:]
            for k in range(n+1-shift):
                if B[k]:
                    C[k+shift]^=field_product(field,ratio,B[k])
            if 2*L<=step:
                L=step+1-L
                B=old
                prev_d=discrepancy
                shift=1
                rec["action"]="retained_previous_locator"
            else:
                shift+=1
                rec["action"]="coefficient_update_only"
        rec["L_after"]=L
        ledger.append(rec)
    # Verify final source recurrence in exactly its valid frame.
    for idx in range(L,n):
        residual=0
        for j in range(L+1):
            residual ^= field_product(field,C[j],syndromes[idx-j])
        if residual!=0:
            raise AssertionError(f"recurrence failed at witness {idx}")
    return C[:L+1],ledger


def eval_poly(poly,z,field):
    value=0
    for c in reversed(poly):
        value=field_product(field,value,z)^int(c)
    return value


def evaluator_from_source(syndromes,L,field):
    """Truncated polynomial producer, not an independent inverse."""
    omega=[0]*max(0,len(L)-1)
    for h in range(len(omega)):
        accum=0
        for k in range(h+1):
            accum ^= field_product(field,L[k],syndromes[h-k])
        omega[h]=accum
    return omega


def derivative_char2(poly):
    return [poly[i] if i%2==1 else 0 for i in range(1,len(poly))]


def decode_by_source_recurrence(syndromes, m, gf, field_tables):
    locator,ledger=discrepancy_recurrence(syndromes,gf)
    evaluator=evaluator_from_source(syndromes,locator,gf)
    derivative=derivative_char2(locator)
    nonzero={}
    for position in range(m):
        # alpha^position inverted, using already authenticated field table.
        x_inverse=int(field_tables.antilog[(field_tables.order-position) % field_tables.order])
        if eval_poly(locator,x_inverse,gf)!=0:
            continue
        d=eval_poly(derivative,x_inverse,gf)
        if not d:
            raise ArithmeticError("locator root with absent derivative: unresolved construction")
        numerator=eval_poly(evaluator,x_inverse,gf)
        value=field_product(gf,numerator,field_inverse(gf,d))
        if value:
            nonzero[position]=value
    return nonzero,locator,evaluator,ledger


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n",type=int,default=6)
    p.add_argument("--m",type=int,default=15)
    p.add_argument("--shots",type=int,default=128)
    p.add_argument("--seed",type=int,default=20261121)
    p.add_argument("--out",type=Path,default=Path("/tmp/dqi023_bm_witness.json"))
    a=p.parse_args()
    if a.n<2 or a.m<a.n or a.m>4095: p.error("2<=n<=m<=4095 required")
    field=km.GF2Field(12)
    spec=ProblemSpecDQI(m=a.m,n=a.n,degree=12,
        r=default_num_accepted_values(12),num_shots=a.shots)
    table=FieldTables(field)
    source,mask,oracle=sample_shots(
        spec,table,np.random.default_rng(a.seed),a.shots)
    summary=collections.Counter()
    first_failures=[]
    max_L=0
    first_examples=[]
    for shot in range(a.shots):
        reconstructed,locator,evaluator,ledger=decode_by_source_recurrence(
            [int(x) for x in source[shot]],a.m,field,table)
        L=len(locator)-1
        max_L=max(max_L,L)
        summary[L]+=1
        predicted_phase=bool(sum(
            (int(v)&int(mask[shot,pos])).bit_count()
            for pos,v in reconstructed.items())&1)
        if predicted_phase != bool(oracle[shot]):
            first_failures.append({"shot":shot,"L":L,
                "expected_phase":bool(oracle[shot]),"got":predicted_phase,
                "decoded_weight":len(reconstructed)})
        if len(first_examples)<3:
            first_examples.append({
                "shot":shot,"L":L,"decoded_weight":len(reconstructed),
                "locator_length":len(locator),
                "evaluator_length":len(evaluator),
                "produced_inverses":sum(int(x["created_inverse"]) for x in ledger),
                "no_update_witnesses":sum(x["action"]=="no_update_witnessed_zero"
                                            for x in ledger)
            })
    record={
       "experiment":"023b","method":"independent GF2 syndrome recurrence",
       "n":a.n,"m":a.m,"degree":12,"shots":a.shots,
       "source":"official verifier generated syndrome and phase samples only; no competitor code",
       "source_phase_matches":not bool(first_failures),
       "phase_errors":len(first_failures),
       "first_failures":first_failures[:6],
       "max_source_recurrence_degree":max_L,
       "correctable_weight_bound":a.n//2,
       "degree_distribution":dict(sorted(summary.items())),
       "examples":first_examples,
       "source_bound_applies_only_to_valid_error_distribution":True,
       "arbitrary_quantum_syndrome_states_verified":False,
       "reversible_quantum_implementation":"NOT_BUILT",
       "clean_work_and_kaggle_verifier":"NOT_RUN"
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    print("RECURRENCE_SOURCE_AUDIT",json.dumps({
        k:record[k] for k in ("n","m","shots","source_phase_matches",
                              "phase_errors","max_source_recurrence_degree",
                              "degree_distribution")}),flush=True)
    if first_failures:
        raise AssertionError(str(first_failures[:2]))


if __name__=="__main__":main()
