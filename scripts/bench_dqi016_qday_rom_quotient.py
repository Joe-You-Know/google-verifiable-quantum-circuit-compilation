#!/usr/bin/env python3
"""DQI experiment 016: QDay-style source-ROM quotient-to-accumulator synthesis.

The original QDay work constructs a finite mapping CLASSICALLY and then
compiles it as controlled quantum operations. Apply that exact strategy
to the DQI coefficient quotient, but do NOT replace a coherently used
quotient with an output-class label.

For a fixed nonzero denominator d, multiplication by inv(d) is LINEAR
on GF(2)^b, so construct a reversible controlled linear map:
  target ^= control * (numerator / denominator).

The denominator comparison is computed and uncomputed once per d.
Both input fields and the incoming target survive. A zero denominator
produces no update, exactly like the original Kickmix GF2 helper.

The test distinguishes:
  - source-level mathematical equivalence;
  - actual Kickmix simulator basis-state equivalence;
  - measured Q, Toffolis, and ops;
  - whole DQI verifier (NOT RUN).
This is a bounded full-domain ROM, O(2^b*b^2). It is not presumed
competitive with b=12's native arithmetic without measured evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import kickmix as km


def terms_for_denominator(field, d: int, degree: int) -> list[tuple[int,int]]:
    """Ordered (numerator bit, destination bit) XOR-term witnesses."""
    if d <= 0 or d >= 1 << degree:
        raise ValueError("nonzero denominator outside carrier")
    reciprocal=field.pow(d,(1 << degree)-2)
    terms=[]
    for source_bit in range(degree):
        image=field.mul(1 << source_bit,reciprocal)
        for target_bit in range(degree):
            if (image >> target_bit) & 1:
                terms.append((source_bit,target_bit))
    return terms


def source_rom_ratio(field,numerator:int,denominator:int,control:int,degree:int)->int:
    """Independent finite-source semantic evaluator, with explicit zero case."""
    if not control or denominator == 0:
        return 0
    outcome = 0
    bits=tuple((numerator >> j)&1 for j in range(degree))
    for source_bit,target_bit in terms_for_denominator(field,denominator,degree):
        if bits[source_bit]:
            outcome ^= 1 << target_bit
    return outcome


def build_gadget(degree:int,mode:str):
    b=km.CircuitBuilder()
    numerator=b.create_quantum_register(degree,"numerator")
    denominator=b.create_quantum_register(degree,"denominator")
    target=b.create_quantum_register(degree,"accumulator")
    control=b.create_quantum_register(1,"control")[0]
    field=km.GF2Field(degree)
    reference_terms=0
    if mode=="qday_denominator_rom":
        equality=b.alloc_qubits(1)[0]
        for d in range(1,1 << degree):
            b.flip_if_equal(denominator,d,target=equality,control=control)
            coeffs=terms_for_denominator(field,d,degree)
            reference_terms+=len(coeffs)
            for source_bit,target_bit in coeffs:
                b.ccx(equality,numerator[source_bit],target[target_bit])
            b.flip_if_equal(denominator,d,target=equality,control=control)
        b.free(equality)
    elif mode=="native_held_scaffold":
        ratio,scaffold=b.init_gf2_div_with_scaffold(
            numerator,denominator,field=field)
        b.gf2_iadd(ratio,target=target,field=field,control=control)
        b.del_gf2_div_with_scaffold(
            numerator,denominator,target=ratio,scaffold=scaffold,field=field)
        b.free(scaffold+ratio)
    else:
        raise ValueError("unrecognized mode")
    circuit=b.finish_circuit()
    stat=circuit.operation_statistics()
    return circuit, (numerator,denominator,target,control), {
        "degree":degree,
        "mode":mode,
        "num_qubits":int(circuit.num_qubits),
        "extra_qubits":int(circuit.num_qubits)-(3*degree+1),
        "static_toffoli_like":int(stat.num_toffoli_like),
        "num_ops":len(circuit),
        "nonzero_denominator_cases":(1<<degree)-1 if mode=="qday_denominator_rom" else None,
        "controlled_linear_xor_terms":reference_terms if mode=="qday_denominator_rom" else None,
        "source_QR_identity":"target XOR (control ? numerator/denominator : 0); zero denominator returns 0",
        "full_DQI_phase_verifier":"NOT_RUN",
    }


def bool_bits(values,width):
    values=np.asarray(values,dtype=np.int64)
    return ((values[:,None] >> np.arange(width,dtype=np.int64)) & 1).astype(bool).T


def read_values(bitarray):
    array=np.asarray(bitarray,dtype=np.uint64)
    return np.sum(array*(1<<np.arange(len(array),dtype=np.uint64))[:,None],axis=0).astype(np.int64)


def verify_basis(circuit, registers, degree, cases, seed, exhaustive=False):
    numerator,denominator,target,control=registers
    field=km.GF2Field(degree)
    if exhaustive:
        domain=1 << degree
        a=np.arange(domain,dtype=np.int64)
        # All (a,b,c) with multiple incoming targets to check XOR,
        # plus original control false and zero denominator.
        values=[(n,d,t,c) for n in range(domain)
                for d in range(domain) for c in (0,1)
                for t in (0,1,(1<<degree)-1)]
        cases=len(values)
    else:
        rng=np.random.default_rng(seed)
        domain=1 << degree
        values=[(int(rng.integers(domain)),int(rng.integers(domain)),
                 int(rng.integers(domain)),int(rng.integers(2)))
                for _ in range(cases)]
        # deterministic witnesses to cover zero denominator and both controls
        values[:4]=[(0,0,0,0),(1,0,0,1),
                    (domain-1,1,domain-1,1),
                    (domain-1,domain-1,domain-1,0)]
    named_slots={int(q.id) for block in (numerator,denominator,target) for q in block}
    named_slots.add(int(control.id))
    ancilla=km.array([km.q(i) for i in range(circuit.num_qubits)
                     if i not in named_slots])
    errors=0
    for start in range(0,len(values),128):
        block=values[start:start+128]
        arr=np.array(block,dtype=np.int64)
        n,d,t,c=(arr[:,k] for k in range(4))
        sim=km.Simulator(batch_size=len(block),debug_print=False,
                         counting_operations=False,seed=seed+start)
        sim.use_same_registers_as(circuit)
        for reg,vals,width in ((numerator,n,degree),(denominator,d,degree),
                               (target,t,degree)):
            sim.write_across_shots(reg,bool_bits(vals,width))
        sim.write_across_shots(km.array([control]),bool_bits(c,1))
        sim.do(circuit)
        rn,rd,rt,rc=(
            read_values(sim.read_across_shots(reg)) for reg
            in (numerator,denominator,target,km.array([control]))
        )
        for i,case in enumerate(block):
            ni,di,ti,ci=map(int,case)
            correct=int(ti ^ source_rom_ratio(field,ni,di,ci,degree))
            if (rn[i],rd[i],rt[i],rc[i]) != (ni,di,correct,ci):
                raise AssertionError(
                    f"case {start+i}: got {(rn[i],rd[i],rt[i],rc[i])}, "
                    f"expected {(ni,di,correct,ci)}"
                )
        if len(ancilla):
            garbage=sim.read_across_shots(ancilla)
            if np.any(garbage):
                raise AssertionError(f"case block starting {start}: workspace not clean")
    return {"basis_cases":len(values),"status":"PASS",
            "control_and_inputs_retained":True,
            "workspace_clean":True,
            "full_DQI_phase_verifier":"NOT_RUN"}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--degrees",type=int,nargs="+",default=[4,6])
    p.add_argument("--verification-cases",type=int,default=512)
    p.add_argument("--exhaustive-up-to",type=int,default=4)
    p.add_argument("--seed",type=int,default=20261120)
    p.add_argument("--report",type=Path,default=Path("/tmp/vqcc_dqi016.json"))
    args=p.parse_args()
    if args.report.exists(): p.error("refusing to overwrite report")
    out=[]
    for degree in args.degrees:
        field=km.GF2Field(degree)
        for n in range(1<<degree):
            for d in range(1<<degree):
                for c in (0,1):
                    out1=source_rom_ratio(field,n,d,c,degree)
                    out2=field.mul(n,field.pow(d,(1<<degree)-2)) if d and c else 0
                    if out1 != out2:raise AssertionError("classical ROM law failed")
        for mode in ("native_held_scaffold","qday_denominator_rom"):
            circuit,registers,stats=build_gadget(degree,mode)
            stats["verified"]=verify_basis(
                circuit,registers,degree,args.verification_cases,args.seed,
                exhaustive=degree<=args.exhaustive_up_to
            )
            out.append(stats)
            print(json.dumps(stats,sort_keys=True),flush=True)
    result={"experiment":"016","methods":out,
            "claim":"Source ROM mapping and exact builder basis simulation; no full DQI replacement.",
            "expected_asymptotics":"QROM exponential in degree; b12 may be prohibitively expensive.",
            "source":"user QDay ROM approach applied to GF(2^degree) conditional quotient"}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
