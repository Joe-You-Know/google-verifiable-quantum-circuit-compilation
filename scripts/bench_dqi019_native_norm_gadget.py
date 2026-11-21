#!/usr/bin/env python3
"""Experiment 019: native Kickmix controlled GF(2^12) quotient comparison.

The candidate is the exact fixed gate word from the earlier standalone
six-bit norm-inverse experiment, losslessly compressed in
research/experiment_019_native_gadget.lzma.b64.
No synchronized EEA source is modified by this audit.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import lzma
from pathlib import Path
import sys

import numpy as np
import kickmix as km

ROOT = Path(__file__).resolve().parents[1]
BLOB = ROOT / "research" / "experiment_019_native_gadget.lzma.b64"
SHA256 = "b8e52afde6080e93f674ca2ca8bbdc98abf614799ea803c1c8e6e61e9f89466c"
sys.path.insert(0, str(ROOT / "scripts"))
from bench_dqi016_qday_rom_quotient import bool_bits, read_values

def native_gate_word():
    raw = lzma.decompress(base64.b64decode(BLOB.read_text().strip()))
    assert len(raw) == 11394, f"wrong gate byte count: {len(raw)}"
    assert hashlib.sha256(raw).hexdigest() == SHA256, "gate word hash mismatch"
    steps = []
    cursor = 0
    while cursor < len(raw):
        tag = raw[cursor]
        if tag == 1:
            assert cursor + 3 <= len(raw)
            indices = tuple(raw[cursor + 1:cursor + 3])
            cursor += 3
        elif tag == 2:
            assert cursor + 4 <= len(raw)
            indices = tuple(raw[cursor + 1:cursor + 4])
            cursor += 4
        else:
            raise AssertionError(f"invalid gate tag {tag} at byte {cursor}")
        assert all(x < 81 for x in indices)
        assert len(set(indices)) == len(indices), "gate controls/target overlap"
        steps.append((tag, *indices))
    assert len(steps) == 3708
    assert sum(op[0] == 1 for op in steps) == 3438
    assert sum(op[0] == 2 for op in steps) == 270
    return steps

def build_candidate():
    builder = km.CircuitBuilder()
    a = builder.create_quantum_register(12, "numerator")
    d = builder.create_quantum_register(12, "denominator")
    out = builder.create_quantum_register(12, "accumulator")
    ctrl = builder.create_quantum_register(1, "control")[0]
    scratch = builder.alloc_qubits(44)
    qubits = list(a) + list(d) + list(out) + [ctrl] + list(scratch)
    assert len(qubits) == 81
    for op in native_gate_word():
        if op[0] == 1:
            builder.cx(qubits[op[1]], qubits[op[2]])
        else:
            builder.ccx(qubits[op[1]], qubits[op[2]], qubits[op[3]])
    builder.free(scratch)
    return builder.finish_circuit(), (a,d,out,ctrl)

def build_original():
    builder = km.CircuitBuilder()
    a = builder.create_quantum_register(12, "numerator")
    d = builder.create_quantum_register(12, "denominator")
    out = builder.create_quantum_register(12, "accumulator")
    ctrl = builder.create_quantum_register(1, "control")[0]
    gf = km.GF2Field(12)
    ratio, scaffold = builder.init_gf2_div_with_scaffold(a, d, field=gf)
    builder.gf2_iadd(ratio, target=out, field=gf, control=ctrl)
    builder.del_gf2_div_with_scaffold(
        a, d, target=ratio, scaffold=scaffold, field=gf)
    builder.free(scaffold + ratio)
    return builder.finish_circuit(), (a,d,out,ctrl)

def make_cases(seed):
    rng = np.random.default_rng(seed)
    cases = [(0,0,0,0),(0,0,0,1),(1,0,57,1),
             (4095,0,125,1),(4095,4095,4095,1),
             (123,456,789,0),(123,456,789,1)]
    for d in range(4096):
        cases.append((1,d,(d * 37 + 217) & 4095,1))
    for a in range(4096):
        cases.append((a,1,(a * 19 + 117) & 4095,a & 1))
    for _ in range(1024):
        cases.append((int(rng.integers(4096)),int(rng.integers(4096)),
                      int(rng.integers(4096)),int(rng.integers(2))))
    return cases

def simulate(circuit, registers, cases, seed):
    a,d,out,ctrl = registers
    field = km.GF2Field(12)
    # A single Kickmix qubit index corresponds to a single original source occurrence.
    named = {int(q.id) for reg in (a,d,out) for q in reg}
    named.add(int(ctrl.id))
    scratch = km.array([km.q(i) for i in range(circuit.num_qubits)
                        if i not in named])
    tested = 0
    for start in range(0,len(cases),128):
        block = np.asarray(cases[start:start+128],dtype=np.int64)
        n,den,t,c = (block[:,i] for i in range(4))
        sim = km.Simulator(batch_size=len(block),seed=seed+start,
                           debug_print=False,counting_operations=False)
        sim.use_same_registers_as(circuit)
        for reg,values,width in ((a,n,12),(d,den,12),(out,t,12)):
            sim.write_across_shots(reg,bool_bits(values,width))
        sim.write_across_shots(km.array([ctrl]),bool_bits(c,1))
        sim.do(circuit)
        rn,rd,rt,rc = (read_values(sim.read_across_shots(r))
                       for r in (a,d,out,km.array([ctrl])))
        expected = np.asarray([
            int(t[i]) ^ (field.mul(int(n[i]), field.pow(int(den[i]),4094))
                          if c[i] and den[i] else 0)
            for i in range(len(block))],dtype=np.int64)
        for label,got,want in (("numerator",rn,n),("denominator",rd,den),
                               ("accumulator",rt,expected),("control",rc,c)):
            if not np.array_equal(got,want):
                idx = int(np.flatnonzero(got != want)[0])
                raise AssertionError(
                    f"{label} mismatch at global case {start+idx}: got {got[idx]}, expected {want[idx]}")
        if len(scratch) and np.any(sim.read_across_shots(scratch)):
            raise AssertionError(f"nonzero scratch in block starting {start}")
        tested += len(block)
    return {"basis_cases":tested,"status":"PASS",
            "preserved_numerator_denominator_control":True,
            "target_XOR_correct":True,"all_work_qubits_restored":True}

def resources(circuit):
    stats = circuit.operation_statistics()
    return {"num_qubits":int(circuit.num_qubits),
            "static_toffoli_like":int(stats.num_toffoli_like),
            "num_ops":len(circuit),
            "extra_work_qubits":int(circuit.num_qubits)-37}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir",type=Path,default=Path("/tmp/vqcc_dqi019_native"))
    parser.add_argument("--seed",type=int,default=20261120)
    parser.add_argument("--skip-simulation",action="store_true")
    args = parser.parse_args()
    args.outdir.mkdir(parents=True,exist_ok=True)
    field=km.GF2Field(12)
    assert field.mul(0x800,2) == 0x53, (
        "Kickmix GF4096 reduction polynomial changed from 0x1053")
    original, oregs = build_original()
    candidate, cregs = build_candidate()
    original.to_file(str(args.outdir / "original_held_109q.kmb"),format="kmb")
    candidate.to_file(str(args.outdir / "norm_inverse_candidate_81q.kmb"),format="kmb")
    old, new = resources(original),resources(candidate)
    assert old["num_qubits"] == 109 and old["static_toffoli_like"] == 390, (
        "Original Kickmix benchmark deviated from recorded 109/390: " + str(old))
    assert new["num_qubits"] == 81 and new["static_toffoli_like"] == 270, (
        "Candidate native compilation deviated from generated 81/270: " + str(new))
    results={
        "experiment":"019",
        "field":"GF(2^12), Kickmix default polynomial 0x1053",
        "reference_source":"verifiers/dqi/dqi_reference_circuit.py: quotient_div",
        "gate_blob_sha256":SHA256,
        "comparator":"same Kickmix CircuitBuilder, finish_circuit, operation_statistics",
        "original_held_scaffold":old,
        "candidate_six_bit_norm_inverse":new,
        "qubit_delta":new["num_qubits"]-old["num_qubits"],
        "toffoli_like_delta":new["static_toffoli_like"]-old["static_toffoli_like"],
        "eea_replaced":False,
        "full_dqi_phase_verifier":"NOT_RUN",
    }
    if not args.skip_simulation:
        cases=make_cases(args.seed)
        results["candidate_validation"]=simulate(candidate,cregs,cases,args.seed)
        results["original_validation"]=simulate(original,oregs,cases,args.seed)
    else:
        results["candidate_validation"]="NOT_RUN"
        results["original_validation"]="NOT_RUN"
    path=args.outdir/"experiment_019_native_report.json"
    path.write_text(json.dumps(results,indent=2)+"\n")
    print(json.dumps(results,indent=2),flush=True)

if __name__=="__main__":
    main()
