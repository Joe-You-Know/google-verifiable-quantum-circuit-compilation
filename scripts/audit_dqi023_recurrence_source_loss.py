#!/usr/bin/env python3
"""Experiment 023d — falsify a source-forgetting reversible recurrence update.

A naive Berlekamp-Massey correction that overwrites C with
  U(C) = C + quotient(D(C),b) * K
where D is the current linear discrepancy, K is a nonzero shifted
earlier locator, and b=D(K) is nonzero, is NOT injective.

For each distinct t in GF(2^b):
  D(C+tK)=D(C)+t*b
  U(C+tK)=C+tK + [D(C)/b+t]K =U(C).

This is an algebraic nonconstruction witness: removing the old discrepancy
also erases a distinguishable source degree of freedom, unless an independent
relationship or retained carrier restores it. The finite field is modeled
with its exact native multiplication; zero numerator is explicitly allowed.
No comparison score and no public opponent algorithm is copied.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import kickmix as km


def inverse_nonzero(gf, x):
    if not x:raise ZeroDivisionError("absent inverse: denominator is zero")
    return int(gf.pow(int(x),(1<<gf.degree)-2))


def field_dot(gf,coefficients,source):
    total=0
    N=len(source)-1
    for i,c in enumerate(coefficients):
        if i <= N and c:
            total^=int(gf.mul(int(c),int(source[N-i])))
    return total


def field_add_scaled(gf,v,scalar,K):
    return [int(a)^int(gf.mul(int(scalar),int(b)))
            for a,b in zip(v,K)]


def corrected(gf,C,K,source,denominator):
    delta=field_dot(gf,C,source)
    factor=int(gf.mul(delta,inverse_nonzero(gf,denominator)))
    return field_add_scaled(gf,C,factor,K),delta,factor


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--degree",type=int,default=12)
    p.add_argument("--out",type=Path,
                   default=Path("/tmp/dqi023_noninjectivity.json"))
    a=p.parse_args()
    gf=km.GF2Field(a.degree)
    domain=1<<a.degree
    # Degree ≤3, normalized constant coefficient 1 for every input.
    S=[3,1,2,7]
    C=[1,3,5,9]
    K=[0,1,0,0]
    b=field_dot(gf,K,S)
    if not b:raise AssertionError("chosen discrepancy carrier vanished")
    out0,d0,f0=corrected(gf,C,K,S,b)
    seen=set()
    collisions=0
    zero_discrepancy_cases=0
    for t in range(domain):
        Ct=field_add_scaled(gf,C,t,K)
        assert Ct[0]==1
        assert Ct[0]==C[0]
        source=tuple(Ct)
        assert source not in seen
        seen.add(source)
        out,d,f=corrected(gf,Ct,K,S,b)
        assert tuple(out)==tuple(out0), (t,out,out0)
        collisions+=1
        zero_discrepancy_cases+=int(d==0)
    result={
        "experiment":"023d","status":"EXACT_NONINJECTIVITY_WITNESS",
        "degree":a.degree,"source_coefficients":C,
        "discrepancy_source":S,"shared_shifted_prior_source":K,
        "source_denominator_b":b,
        "distinct_normalized_inputs":len(seen),
        "identical_derived_output_count":collisions,
        "zero_discrepancy_inputs":zero_discrepancy_cases,
        "field_output":out0,
        "mathematical_identity":"U(C+tK)=U(C) for every t when D(K)=b!=0",
        "consequence":"overwritten recurrence requires retained causal carrier or proven restricted subspace",
        "quantum_reversible_BM":"NOT_BUILT",
        "competition_score":"NOT_MEASURED"
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("NONINJECTIVITY",json.dumps(result),flush=True)


if __name__=="__main__":main()
