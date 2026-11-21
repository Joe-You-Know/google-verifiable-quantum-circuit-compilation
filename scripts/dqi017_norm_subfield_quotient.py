#!/usr/bin/env python3
"""DQI experiment 017: exact GF(2^12)->GF(2^6) norm/inverse decomposition.

Instead of QDay-style lookup of all 4095 nonzero 12-bit denominators,
use the unique 64-element GF(2^6) subfield of GF(2^12).

For B != 0, define the Frobenius conjugate C=B^(2^6) and norm N=B*C.
N lies in GF(2^6). Then B^-1=C*N^-1, where the latter reciprocal can
be retrieved from a 64-row CLASSICAL source dictionary.

This tests EXACT finite-field equivalence and derives a six-bit norm
basis and quadratic norm word equation, including source monomial
counts. It does NOT construct or verify the reversible quantum circuit,
nor does it claim Q or T savings.

QDay application: move the public finite-source ROM down to the
smallest quotient carrier supported by an exact source factorization.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import random
import kickmix as km


def subfield_basis(field):
    q=1 << field.degree
    exp=1 << (field.degree//2)
    subfield=sorted(x for x in range(q) if field.pow(x,exp)==x)
    if len(subfield)!=exp:
        raise AssertionError(f"expected {exp} subfield values, found {len(subfield)}")
    bases=[]
    ledger={0:0}
    for x in subfield:
        if x in ledger: continue
        bit=len(bases)
        bases.append(x)
        ledger=dict(ledger)
        for value,label in list(ledger.items()):
            newvalue=value ^ x
            if newvalue in ledger:
                raise AssertionError("basis not independent")
            ledger[newvalue]=label|(1 << bit)
        if len(bases)==field.degree//2:break
    if len(ledger)!=len(subfield) or set(ledger)!=set(subfield):
        raise AssertionError("basis cannot reconstruct subfield")
    reconstruction=[0]*len(subfield)
    for fieldvalue,label in ledger.items():
        reconstruction[label]=fieldvalue
    if len(set(reconstruction))!=len(subfield):
        raise AssertionError("non-injective retained subfield basis labels")
    return bases,ledger,reconstruction


def norm(field,x):
    conjugate=field.pow(x,1 << (field.degree//2))
    return field.mul(x,conjugate)


def derive_norm_quadratic(field,coordinates):
    degree=field.degree
    linear=[coordinates[norm(field,1<<i)] for i in range(degree)]
    bilinear=[]
    for i in range(degree):
        for j in range(i+1,degree):
            coeff=coordinates[norm(field,(1<<i)^(1<<j))] ^ linear[i] ^ linear[j]
            if coeff:bilinear.append((i,j,coeff))
    return linear,bilinear


def eval_norm_qr(word,linear,bilinear):
    response=0
    for i,v in enumerate(linear):
        if (word >> i)&1:response^=v
    for i,j,v in bilinear:
        if ((word >> i)&1) and ((word >> j)&1):response^=v
    return response


def test_degree(degree,seed):
    if degree != 12:
        raise ValueError("the current field/subfield audit expects degree 12")
    field=km.GF2Field(degree)
    base,coords,unpack=subfield_basis(field)
    exponent=1 << (degree//2)
    linear,bilinear=derive_norm_quadratic(field,coords)
    all_norms=set()
    exact=0
    rng=random.Random(seed)
    inv_lookup=[coords[field.pow(value,exponent-2)] for value in unpack]
    for b in range(1<<degree):
        c=field.pow(b,exponent)
        n=field.mul(b,c)
        all_norms.add(n)
        if field.pow(n,exponent)!=n:
            raise AssertionError("norm not inside subfield")
        sixbit=coords[n]
        if sixbit!=eval_norm_qr(b,linear,bilinear):
            raise AssertionError(f"quadratic norm source failed at {b}")
        from_lookup=unpack[inv_lookup[sixbit]]
        inv_candidate=field.mul(c,from_lookup)
        inv_original=field.pow(b,(1 << degree)-2) if b else 0
        if inv_candidate!=inv_original:
            raise AssertionError(f"norm inversion failed at {b}")
        for a in (0,1,1<<rng.randrange(degree),rng.randrange(1<<degree)):
            updated=field.mul(a,inv_candidate)
            direct=field.mul(a,inv_original)
            if updated!=direct:
                raise AssertionError(f"quotient at {a},{b} does not match")
            exact+=1
    if len(all_norms)!=64:raise AssertionError("norm image not entire subfield")
    weight_counts={str(k):0 for k in range(7)}
    for _,_,coeff in bilinear:
        weight_counts[str(coeff.bit_count())]+=1
    approx_toftoli_if_direct=sum(v.bit_count() for _,_,v in bilinear)
    approx_toffoli_if_shared=sum(min(v.bit_count(),2) for _,_,v in bilinear)
    return {
        "field_degree":12,
        "subfield_degree":6,
        "nonzero_inverse_lookup_entries":63,
        "norm_image_values":len(all_norms),
        "basis_vectors_12bit":base,
        "linear_norm_terms":sum(x.bit_count() for x in linear),
        "nonzero_quadratic_norm_pairs":len(bilinear),
        "quadratic_coeff_popcount":approx_toftoli_if_direct,
        "estimated_norm_forward_toffoli_direct":approx_toftoli_if_direct,
        "estimated_norm_forward_toffoli_shared_AND":approx_toffoli_if_shared,
        "norm_quadratic_coefficient_weight_histogram":weight_counts,
        "all_denominator_values_checked":4096,
        "quotient_cases_checked":exact,
        "subfield_lookup_inversion":"PASS",
        "field_norm_and_quotient_identity":"PASS",
        "reversible_implementation":"NOT_CONSTRUCTED",
        "compiled_T_and_Q_savings":"NOT_ESTABLISHED",
        "caveat":"Toffoli counts are only arithmetic-source monomial estimates; source basis conversion, lookup, multiplication, cleanup, quantum controls are not included.",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed",type=int,default=20261120)
    p.add_argument("--report",type=Path,default=Path("/tmp/vqcc_dqi017_tower.json"))
    args=p.parse_args()
    if args.report.exists():p.error("refusing to overwrite receipt")
    data={"experiment":"017","method":"exhaustive GF4096 norm-subfield source ledger",
          "result":test_degree(12,args.seed)}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,indent=2))

if __name__=="__main__":main()
