#!/usr/bin/env python3
"""Experiment 023e: independent reversible GF(2^12) recurrence source lift.

Exact source carrier F, normalized four-coefficient locator C:
    F_new = F_old + D(C_old)/b,
    C_new = C_old + F_new * K.

Here K=(0,1,0,0), b=D(K)=S_2!=0 and S=(3,1,2,7) are
declared fixed source constants only for this isolated proof gadget.
Native GF(2^12) multiplication determines a CNOT-only linear map.
Forward and exact inverse have no scratch qubits and no phase.
This demonstrates a lawful reversible *one step* carrying the quotient.
Dynamic K, dynamic b, multiple steps and full DQI are not yet built.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import kickmix as km

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"scripts")]
from bench_dqi016_qday_rom_quotient import bool_bits,read_values

SOURCE=[3,1,2,7]
K=[0,1,0,0]


def constants(gf):
    b=int(gf.mul(1,SOURCE[2]))
    if b==0: raise AssertionError("absent denominator invalidates this source chart")
    ib=int(gf.pow(b,(1<<gf.degree)-2))
    weights=[int(gf.mul(int(SOURCE[3-i]),ib)) for i in range(4)]
    return b,weights


def append_source_quotient(builder, C, F, gf, weights):
    # Each original C_i source is kept separate. This is exactly a
    # field-linear XOR of columns, not a numeric accumulator overwrite.
    for i in range(4):
        for source_bit in range(gf.degree):
            column=int(gf.mul(1<<source_bit,weights[i]))
            for output_bit in range(gf.degree):
                if (column>>output_bit)&1:
                    builder.cx(C[i][source_bit],F[output_bit])


def build(roundtrip=False,degree=12):
    b=km.CircuitBuilder()
    C=[b.create_quantum_register(degree,name=f"C{i}") for i in range(4)]
    F=b.create_quantum_register(degree,name="F")
    gf=km.GF2Field(degree)
    denominator,weights=constants(gf)
    append_source_quotient(b,C,F,gf,weights)
    b.cx(F,C[1])
    if roundtrip:
        b.cx(F,C[1])
        append_source_quotient(b,C,F,gf,weights)
    circuit=b.finish_circuit()
    return circuit,C,F,denominator,weights


def one_input_expected(gf,C,f,denom):
    d=0
    for i in range(4):
        d^=int(gf.mul(int(C[i]),int(SOURCE[3-i])))
    inv=int(gf.pow(denom,(1<<gf.degree)-2))
    q=int(gf.mul(d,inv))
    fnew=int(f)^q
    out=list(C)
    out[1]^=fnew
    return out,fnew


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=Path("/tmp/dqi023_reversible_shear.json"))
    p.add_argument("--seed",type=int,default=20261121)
    a=p.parse_args()
    gf=km.GF2Field(12)
    rng=np.random.default_rng(a.seed)
    # Exhaustively vary the source field coefficient t in the 4096-way
    # collision family, then add 4096 independent arbitrary source tuples.
    source=[]
    for t in range(1<<12):
        source.append(([1,t,5,9],0))
    for _ in range(1<<12):
        source.append((
            [int(rng.integers(1<<12)) for _ in range(4)],
            int(rng.integers(1<<12))))
    reports=[]
    for mode in ("forward","roundtrip"):
        c,C,F,denom,weights=build(roundtrip=mode=="roundtrip")
        qcount=c.num_qubits
        if qcount!=60:raise AssertionError("extra quantum state constructed")
        result_set=set()
        errors=0
        phase_errors=0
        for begin in range(0,len(source),128):
            cases=source[begin:begin+128]
            batch=len(cases)
            sim=km.Simulator(batch_size=batch,debug_print=False,
                counting_operations=False,seed=a.seed+begin)
            sim.use_same_registers_as(c)
            v=np.array([case[0] for case in cases],dtype=np.int64)
            initf=np.array([case[1] for case in cases],dtype=np.int64)
            for i in range(4):
                sim.write_across_shots(C[i],bool_bits(v[:,i],12))
            sim.write_across_shots(F,bool_bits(initf,12))
            sim.do(c)
            outC=np.column_stack([
                read_values(sim.read_across_shots(C[i]))
                for i in range(4)])
            outF=read_values(sim.read_across_shots(F))
            phase_errors+=int(np.count_nonzero(sim.read_phase_flipped_across_shots()))
            for index,(oldC,oldF) in enumerate(cases):
                expectedC,expectedF=one_input_expected(
                    gf,oldC,oldF,denom)
                if mode=="roundtrip":
                    expectedC,expectedF=oldC,oldF
                gotC=[int(x) for x in outC[index]]
                gotF=int(outF[index])
                if (gotC,gotF)!=(expectedC,expectedF):
                    errors+=1
                if mode=="forward" and begin+index<(1<<12):
                    result_set.add((*gotC,gotF))
            del sim
        results={"mode":mode,"Q":qcount,
                 "T_static":int(c.operation_statistics().num_toffoli_like),
                 "operations":len(c),
                 "input_cases":len(source),
                 "value_errors":errors,"phase_errors":phase_errors,
                 "normalized_source_witnesses_kept_distinct":
                     len(result_set) if mode=="forward" else None,
                 "status":"PASS" if not errors and not phase_errors else "FAIL"}
        assert results["status"]=="PASS",results
        if mode=="forward":
            assert len(result_set)==(1<<12)
        reports.append(results)
        print("REVERSIBLE_SHEAR",json.dumps(results),flush=True)
    packet={
      "experiment":"023e","status":"PASS",
      "scope":"One fixed-source reversible GF(2^12) recurrence step",
      "source_constants":{"syndrome":SOURCE,"K":K,
          "denominator":denom,"linear_weights":weights},
      "checks":reports,"fully_dynamic_quantum_BM":"NOT_BUILT",
      "full_DQI_and_kaggle":"NOT_RUN"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(packet,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
