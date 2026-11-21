#!/usr/bin/env python3
"""Experiment 014B: Euclidean source-shear over GF(2^b)[X].

Adaptation of Joseph Fredrickson, Extended Euclidean Modular Inversion
as a Primitive Constructive Law (July 23, 2026), Theorem 4.1.

Retain polynomial quotient Q and remainder N, with two source
coefficient-polynomial lanes for the original pair (M,a).
Since the coefficient field has characteristic 2,
    N = L + Q*R
    c_N = c_L + Q*c_R.
Both updates are exact and reconstructible from the retained source.
Swapping lanes preserves the projected determinant numerically in
characteristic 2 (the integer paper's signed orientation flip becomes
an independent occurrence label, not a field value).

This test uses GF2Field.pow solely to implement field coefficient
division as a *verification model*, not as a claim that a cheap
reversible quantum inverse primitive has been constructed.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
import argparse

import kickmix as km


def normalize(A):
    a=list(A)
    while a and not a[-1]:
        a.pop()
    return a


def plus(A,B):
    out=[0]*max(len(A),len(B))
    for k,v in enumerate(A):out[k]^=v
    for k,v in enumerate(B):out[k]^=v
    return normalize(out)


def product(A,B,gf):
    if not A or not B:
        return []
    out=[0]*(len(A)+len(B)-1)
    for i,a in enumerate(A):
        for j,b in enumerate(B):
            out[i+j]^=gf.mul(a,b)
    return normalize(out)


def polynomial_qr(A,B,gf):
    A,B=normalize(A),normalize(B)
    if not B:
        raise ValueError("zero polynomial divisor has no inverse quotient")
    remainder=A[:]
    quotient=[0]*max(0,len(A)-len(B)+1)
    inverse_lead=gf.pow(B[-1],(1<<gf.degree)-2)
    while len(remainder)>=len(B):
        shift=len(remainder)-len(B)
        scalar=gf.mul(remainder[-1],inverse_lead)
        quotient[shift]^=scalar
        for j,b in enumerate(B):
            remainder[shift+j]^=gf.mul(scalar,b)
        remainder=normalize(remainder)
    quotient=normalize(quotient)
    if plus(product(quotient,B,gf),remainder)!=A:
        raise AssertionError("quotient + remainder does not reconstruct source")
    if len(remainder)>=len(B):
        raise AssertionError("remainder did not descend in polynomial degree")
    return quotient,remainder


def combine(c,M,a,gf):
    return plus(product(c[0],M,gf),product(c[1],a,gf))


def det(cA,cB,gf):
    return plus(product(cA[0],cB[1],gf),
                product(cA[1],cB[0],gf))


def source_eea(M,a,gf):
    M,a=normalize(M),normalize(a)
    if not M or not a:
        raise ValueError("positive degree source test needs two nonzero polynomials")
    L,R=M,a
    cL,cR=([1],[]),([],[1])
    if det(cL,cR,gf)!=[1]:
        raise AssertionError("initial source determinant not unit")
    count=0
    while R:
        Q,N=polynomial_qr(L,R,gf)
        cN=(plus(cL[0],product(Q,cR[0],gf)),
            plus(cL[1],product(Q,cR[1],gf)))
        if combine(cN,M,a,gf)!=N:
            raise AssertionError(f"quotient shear lost source at step {count}")
        if plus(product(Q,R,gf),N)!=L:
            raise AssertionError("retained QR did not reconstruct previous carrier")
        if det(cR,cN,gf)!=[1]:
            raise AssertionError("source determinant not preserved in GF2 field")
        L,R,cL,cR=R,N,cR,cN
        count+=1
        if count>len(M)+len(a)+5:
            raise AssertionError("nonterminating EEA traversal")
    if combine(cL,M,a,gf)!=L:
        raise AssertionError("terminal source identity not reconstructed")
    return {"steps":count, "terminal_polynomial":L,
            "is_unit_closure": len(L)==1 and L[0]!=0,
            "source_left":cL[0],"source_right":cL[1]}


def test_cases(degree:int,cases:int,seed:int):
    gf=km.GF2Field(degree)
    rng=random.Random(seed)
    maxval=(1<<degree)-1
    example=None
    maxsteps=0
    witnessed_quotients=0
    for k in range(cases):
        la=rng.randrange(1,7)
        lb=rng.randrange(1,la+1)
        A=[rng.randrange(maxval+1) for _ in range(la)]
        B=[rng.randrange(maxval+1) for _ in range(lb)]
        A[-1]=rng.randrange(1,maxval+1)
        B[-1]=rng.randrange(1,maxval+1)
        result=source_eea(A,B,gf)
        maxsteps=max(maxsteps,result["steps"])
        witnessed_quotients+=result["steps"]
        if example is None: example={"M":A,"a":B,**result}
    return {"degree":degree,"cases":cases,"max_steps":maxsteps,
            "source_QR_steps_tested":witnessed_quotients,
            "first_example":example,"status":"PASS",
            "claim_scope":"polynomial GF source transport, not reversible Kickmix cost or circuit correctness"}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--degree",type=int,nargs="+",default=[4,12])
    p.add_argument("--cases",type=int,default=500)
    p.add_argument("--seed",type=int,default=20261120)
    p.add_argument("--report",type=Path,default=Path("/tmp/vqcc_dqi014b_qr.json"))
    args=p.parse_args()
    if args.report.exists():
        p.error("refusing to overwrite report")
    res=[test_cases(k,args.cases,args.seed) for k in args.degree]
    data={"experiment":"014B","method":"exact source-QR polynomial EEA checks",
          "paper":"Extended Euclidean Modular Inversion as a Primitive Constructive Law, Theorem 4.1",
          "datasets":res,"reversible_quantum_circuit":"NOT_RUN",
          "qubit_savings":"NOT_ESTABLISHED"}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,indent=2))


if __name__=="__main__":
    main()
