#!/usr/bin/env python3
"""Experiment 018: compile exact 12->6-bit quadratic field norm circuit.

Uses Experiment 017's exhaustive source identity and subfield basis.
Compares direct CCX terms against one shared AND per source monomial.

Both constructions realize norm6 ^= coords(B * B^(2^6)) exactly,
preserve all 12 source denominator qubits, clean internal ancilla,
and remain coherent on superpositions by linear extension.

This is only the NORM of a future full quantum quotient circuit,
NOT the 6-bit inversion lookup or DQI's quotient update.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import kickmix as km

from dqi017_norm_subfield_quotient import (
    subfield_basis,derive_norm_quadratic,norm
)
from bench_dqi016_qday_rom_quotient import bool_bits,read_values


def make_norm_circuit(mode:str):
    field=km.GF2Field(12)
    basis,coord,unpack=subfield_basis(field)
    linear,pairs=derive_norm_quadratic(field,coord)
    builder=km.CircuitBuilder()
    source=builder.create_quantum_register(12,"source")
    output=builder.create_quantum_register(6,"norm6")
    flag=builder.alloc_qubits(1)[0] if mode=="shared" else None

    for i,mask in enumerate(linear):
        for bit in range(6):
            if (mask>>bit)&1:
                builder.cx(source[i],output[bit])
    for i,j,mask in pairs:
        k=mask.bit_count()
        if mode=="direct" or k==1:
            for bit in range(6):
                if (mask>>bit)&1:
                    builder.ccx(source[i],source[j],output[bit])
        elif mode=="shared":
            builder.ccx(source[i],source[j],flag)
            for bit in range(6):
                if (mask>>bit)&1:
                    builder.cx(flag,output[bit])
            builder.ccx(source[i],source[j],flag)
        else:
            raise ValueError(f"unknown circuit mode {mode!r}")
    if flag is not None:builder.free(flag)
    c=builder.finish_circuit()
    s=c.operation_statistics()
    return c,source,output,coord, {
        "experiment":"018", "mode":mode, "num_qubits":c.num_qubits,
        "source_qubits":12,"norm_output_qubits":6,
        "extra_temp_slots":int(c.num_qubits)-18,
        "static_toffoli_like":int(s.num_toffoli_like),
        "ops":len(c),"source_cross_terms":len(pairs),
        "whole_quotient_circuit":"NOT_CONSTRUCTED",
    }


def sim_check(circuit,src,out,coords,seed):
    gf=km.GF2Field(12)
    rng=np.random.default_rng(seed)
    source_values=list(range(4096))+[int(x) for x in rng.integers(4096,size=512)]
    target_values=[0]*4096+[int(x) for x in rng.integers(64,size=512)]
    qslots={int(x.id) for x in src}
    qslots.update(int(x.id) for x in out)
    scratch=km.array([km.q(i) for i in range(circuit.num_qubits) if i not in qslots])
    for start in range(0,len(source_values),256):
        sl=slice(start,start+256)
        source=np.asarray(source_values[sl],dtype=np.int64)
        initial=np.asarray(target_values[sl],dtype=np.int64)
        sim=km.Simulator(batch_size=len(source),seed=seed+start,
                         debug_print=False,counting_operations=False)
        sim.use_same_registers_as(circuit)
        sim.write_across_shots(src,bool_bits(source,12))
        sim.write_across_shots(out,bool_bits(initial,6))
        sim.do(circuit)
        a=read_values(sim.read_across_shots(src))
        b=read_values(sim.read_across_shots(out))
        expected=np.asarray([int(initial[i]) ^ coords[norm(gf,int(v))]
                             for i,v in enumerate(source)],dtype=np.int64)
        if not np.array_equal(a,source):
            raise AssertionError(f"source corrupted near case {start}")
        if not np.array_equal(b,expected):
            bad=np.nonzero(b!=expected)[0][0]
            raise AssertionError(f"norm mismatch at case {start+bad}: "
                                 f"{b[bad]} vs {expected[bad]}")
        if len(scratch) and np.any(sim.read_across_shots(scratch)):
            raise AssertionError(f"scratch nonzero at block {start}")
    return {"basis_cases":len(source_values),"status":"PASS",
            "source_preserved":True,"target_XOR_semantics":True,
            "work_registers_zero":True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed",type=int,default=20261120)
    p.add_argument("--report",type=Path,default=Path("/tmp/vqcc_dqi018_norm.json"))
    args=p.parse_args()
    if args.report.exists():p.error("refusing to overwrite file")
    rows=[]
    for mode in ("direct","shared"):
        circuit,src,out,coords,rec=make_norm_circuit(mode)
        rec["simulator"]=sim_check(circuit,src,out,coords,args.seed)
        rows.append(rec)
        print(json.dumps(rec,sort_keys=True),flush=True)
    data={"experiment":"018","results":rows,
          "significance":"First reversible construction in norm-based 12-bit quotient factorization; does not claim complete DQI improvement."}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
