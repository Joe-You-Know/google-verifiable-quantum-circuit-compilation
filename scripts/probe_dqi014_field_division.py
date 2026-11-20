#!/usr/bin/env python3
"""DQI experiment 014: measure GF(2^b) coefficient quotient scaffold resources.

This is a read-only builder-resource probe. The exact reference quotient_div
does:
    ratio, scaffold = init_gf2_div_with_scaffold(b,a)
    controlled XOR ratio into q_i
    del_gf2_div_with_scaffold(b,a,...)
    free(scaffold+ratio)
It is a helper within the *polynomial* extended Euclidean traversal.

This probe checks ratio/scaffold widths, available native alternatives, and
their explicit resource costs at degree 4 and degree 12. It does NOT rewrite
the circuit or claim that conditional nonconstruction is already supported.
"""
import json
import inspect
import kickmix as km


def capture(width):
    b=km.CircuitBuilder()
    a=b.create_quantum_register(width,"denominator")
    c=b.create_quantum_register(width,"numerator")
    gf=km.GF2Field(width)
    q=b.alloc_qubits(width)
    names=[x for x in dir(b) if ("gf2" in x and
             any(y in x for y in ("div","inverse","mul")))]
    available={}
    for key in names:
        method=getattr(b,key)
        try: sig=str(inspect.signature(method))
        except (ValueError,TypeError):sig="native signature unavailable"
        doc=(getattr(method,"__doc__","") or "").splitlines()[:7]
        available[key]={"signature":sig,"doc_head":doc}
    ratio, scaffold=b.init_gf2_div_with_scaffold(c,a,field=gf)
    active=int(b.num_allocated_qubits)
    names_ratio=[int(x.id) for x in ratio]
    names_scaffold=[int(x.id) for x in scaffold]
    if len(set(names_ratio+names_scaffold)) != len(names_ratio)+len(names_scaffold):
        raise AssertionError("division ratio/scaffold share physical slot")
    b.gf2_iadd(ratio,target=q,field=gf)
    b.gf2_iadd(ratio,target=q,field=gf)
    b.del_gf2_div_with_scaffold(c,a,target=ratio,scaffold=scaffold,field=gf)
    b.free(scaffold+ratio)
    b.free(q)
    circuit=b.finish_circuit()
    stat=circuit.operation_statistics()
    return {
        "degree":width,
        "ratio_qubits":len(ratio),
        "scaffold_qubits":len(scaffold),
        "total_scaffold_and_ratio":len(ratio)+len(scaffold),
        "live_qubits_at_division_peak":active,
        "finished_circuit_num_qubits":int(circuit.num_qubits),
        "compiled_static_toffoli_like":int(stat.num_toffoli_like),
        "num_ops":len(circuit),
        "possible_native_alternatives":available,
        "source_contract":"quantum b/a to target q_i with exact ancilla cleanup",
        "actual_qubit_saving":"NOT ESTABLISHED",
        "original_DQI_phase_verifier":"NOT_RUN",
    }

for degree in (4,12):
    print(json.dumps(capture(degree),sort_keys=True),flush=True)
