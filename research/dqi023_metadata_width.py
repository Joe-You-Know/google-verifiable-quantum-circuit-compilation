"""Experiment 023 — provenance-preserving metadata-width hypotheses.

Source is exclusively our own Experiment 022c. No competitor circuits.
The *only* change is the width of the EEA polynomial-degree/carry registers
at source construction. Tested variants distinguish the two paired source
counts (A,B) and (a,b) from the quotient accumulator n_q.

Original five registers all have m.bit_length()+1 bits; m=n+3.
This extra bit may be required by a transient addition even when individual
polynomial degree registers never exceed the 73-position bounds.
Do not interpret reduced Q as proof until the original DQI phase verifier
checks same shots, and explicit source-domain obligations are established.
"""
from __future__ import annotations

import kickmix as km

from research.dqi022_serial_forney import SparseSerialForneyDecoder
from research.dqi020_experimental_decoder import default_n_iters

WIDTH_MODES = (
    "baseline",
    "poly_pair",
    "aux_pair",
    "both_pairs",
    "all_narrow",
)


def selected_widths(n: int, mode: str):
    if mode not in WIDTH_MODES:
        raise ValueError(f"unknown metadata-width mode {mode!r}")
    m = n + 3
    narrow = m.bit_length()
    wide = narrow + 1
    # A/B and a/b are swapped only with their equal-width partner.
    n_AB = narrow if mode in ("poly_pair", "both_pairs", "all_narrow") else wide
    n_ab = narrow if mode in ("aux_pair", "both_pairs", "all_narrow") else wide
    n_q = narrow if mode == "all_narrow" else wide
    assert (1 << narrow) > n + 1
    return {"n_A":n_AB,"n_B":n_AB,"n_a":n_ab,"n_b":n_ab,"n_q":n_q,
            "counter":2,"halting":default_n_iters(n).bit_length()}


class WidthAuditDecoder(SparseSerialForneyDecoder):
    def __init__(self, n_syndromes, field, *,
                 quotient_mode="norm_inverse", width_mode="baseline"):
        super().__init__(n_syndromes, field, quotient_mode=quotient_mode)
        self.width_mode = width_mode

    def build_syndrome_decoding_mbuc(self, builder, *, syndromes,
                                     error_mbuc, n_iters):
        """Exact copy of Experiment020's *outer* construction with typed widths."""
        gf = self.field
        n = self.n_syndromes
        degree = gf.degree
        if len(syndromes) != n:
            raise ValueError("wrong syndrome register count")
        if not (n <= len(error_mbuc) <= (1 << degree) - 1):
            raise ValueError("invalid codeword position count")
        if any(len(s) != degree for s in syndromes):
            raise ValueError("syndrome element degree mismatch")
        if any(len(e) != degree for e in error_mbuc):
            raise ValueError("mask element degree mismatch")
        m = n + 3
        widths = selected_widths(n,self.width_mode)
        reg_a = [builder.alloc_qubits(degree) if i < 3 else syndromes[i - 3]
                 for i in range(m)]
        reg_b = [builder.alloc_qubits(degree) for _ in range(m)]
        n_A = builder.alloc_qubits(widths["n_A"])
        n_B = builder.alloc_qubits(widths["n_B"])
        n_a = builder.alloc_qubits(widths["n_a"])
        n_b = builder.alloc_qubits(widths["n_b"])
        n_q = builder.alloc_qubits(widths["n_q"])
        flag = builder.alloc_qubits(1)[0]
        counter = builder.alloc_qubits(2)
        halting_counter = builder.alloc_qubits(n_iters.bit_length())
        eea = (reg_a,reg_b,n_A,n_B,n_a,n_b,n_q,flag,counter,halting_counter)

        init_ones=km.array([reg_a[0][0],reg_b[m-1][0],n_a[0],flag])
        builder.x(init_ones)
        builder.gf2_iadd(n,target=n_A)
        builder.gf2_iadd(n+1,target=n_B)
        with builder.mark("initial_shift"):
            self._initial_shift_loop(builder,reg_a,n_A,is_adjoint=False)
        with builder.mark("forward_eea"):
            self._synchronized_eea(builder,*eea,n_iters=n_iters,is_adjoint=False)
        with builder.mark("chien_forney_mbuc"):
            self._chien_search_and_forney_mbuc(builder,reg_b,error_mbuc,n_b,n_B)
        with builder.mark("reverse_eea"):
            self._synchronized_eea(builder,*eea,n_iters=n_iters,is_adjoint=True)
        with builder.mark("uncompute_initial_shift"):
            self._initial_shift_loop(builder,reg_a,n_A,is_adjoint=True)
        builder.gf2_iadd(n+1,target=n_B)
        builder.gf2_iadd(n,target=n_A)
        builder.x(init_ones)
        for reg in (halting_counter,counter,flag,n_q,n_b,n_a,n_B,n_A,
                    *reg_a[:3],*reg_b):
            builder.free(reg)


def build_width_mode_circuit(m:int,n:int,degree:int,mode:str):
    if degree != 12:raise ValueError("Experiment020 authenticated degree=12 only")
    b=km.CircuitBuilder()
    syndromes=[b.create_quantum_register(degree,name=f"S{i}")
               for i in range(n)]
    masks=[b.create_classical_register(degree,name=f"E{j}")
           for j in range(m)]
    WidthAuditDecoder(n,km.GF2Field(degree),quotient_mode="norm_inverse",
                      width_mode=mode).build_syndrome_decoding_mbuc(
        b,syndromes=syndromes,error_mbuc=masks,
        n_iters=default_n_iters(n))
    return b.finish_circuit()
