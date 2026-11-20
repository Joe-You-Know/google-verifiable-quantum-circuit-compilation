#!/usr/bin/env python3
"""Experiment 015: compare native GF quotient gadget resource patterns.

All variants apply the GF(2^degree) ratio to an accumulator. The first
two preserve the DQI source's conditional quotient behavior; the third
is UNCONDITIONAL and is only a resource lower-bound probe, not a valid
drop-in replacement while source control is required.

- held_scaffold: original reference's MBUC-friendly quotient producer;
- recomputed_division: quotient obtained without retained inverse scaffold;
- unconditional_direct_xor: direct quotient XOR with no conditional control.

Original paper correspondence: Euclidean source-preserving quotient
shear. This script does not prove equivalent whole DQI circuits, merely
isolates the measured source object.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import kickmix as km


def build(degree, pattern):
    b=km.CircuitBuilder()
    numerator=b.create_quantum_register(degree,"numerator")
    denominator=b.create_quantum_register(degree,"denominator")
    target=b.create_quantum_register(degree,"accumulator")
    control=b.create_quantum_register(1,"control")[0]
    gf=km.GF2Field(degree)
    if pattern=="held_scaffold":
        ratio,scaffold=b.init_gf2_div_with_scaffold(numerator,denominator,field=gf)
        b.gf2_iadd(ratio,target=target,field=gf,control=control)
        b.del_gf2_div_with_scaffold(
            numerator,denominator,target=ratio,scaffold=scaffold,field=gf)
        b.free(scaffold+ratio)
    elif pattern=="recomputed_division":
        ratio=b.init_gf2_div(numerator,denominator,field=gf)
        b.gf2_iadd(ratio,target=target,field=gf,control=control)
        b.del_gf2_div(numerator,denominator,target=ratio,field=gf)
        b.free(ratio)
    elif pattern=="unconditional_direct_xor":
        b.ixor_gf2_div(numerator,denominator,target=target,field=gf)
    else:
        raise ValueError("unknown pattern")
    c=b.finish_circuit()
    stats=c.operation_statistics()
    return {
        "field_degree":degree,
        "pattern":pattern,
        "num_qubits":int(c.num_qubits),
        "input_and_output_qubits":degree*3+1,
        "max_additional_qubits":int(c.num_qubits)-(degree*3+1),
        "static_toffoli_like":int(stats.num_toffoli_like),
        "ops":len(c),
        "conditional_on_control":pattern!="unconditional_direct_xor",
        "target_behavior":"target XOR= quotient of numerator/denominator",
        "whole_DQI_verifier":"NOT_RUN",
        "valid_DQI_replacement":"NOT_ESTABLISHED",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--degree",type=int,nargs="+",default=[4,12])
    p.add_argument("--report",type=Path,default=Path("/tmp/vqcc_dqi015_quotient_modes.json"))
    args=p.parse_args()
    if args.report.exists():
        p.error("refusing to overwrite report")
    rows=[]
    for degree in args.degree:
        for method in ("held_scaffold","recomputed_division","unconditional_direct_xor"):
            row=build(degree,method)
            rows.append(row)
            print(json.dumps(row,sort_keys=True),flush=True)
    output={"experiment":"015","results":rows,
            "remark":"Direct XOR is not controlled and cannot replace the original source call without separately proving a controlled transformation."}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
