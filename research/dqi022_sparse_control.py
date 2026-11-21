"""Experiment 022 — original, source-directed counter-conjunction lifetime reduction.

No competitor circuit is imported. This class inherits the independently verified
Experiment 020 decoder. Only the construction and release of the one-hot EEA
controls and the scope of the c3 conjunction are changed.

Proof obligation: for hc=h and counter bits a,b, the four ctrl values equal
(h*not(a)*not(b), h*a*not(b), h*not(a)*b, h*a*b).
A transient a*b is still constructed only for the halting-counter update.
"""
from __future__ import annotations

import kickmix as km
from research.dqi020_experimental_decoder import (
    ProosAndZalkaDecoder as Experiment020Decoder,
    default_n_iters,
)


class SparseControlDecoder(Experiment020Decoder):
    """Avoid maintaining is_c3 while its one-hot consequences are constructed."""

    @staticmethod
    def _counter_controls_sparse(builder, counter, is_hc_zero):
        ctrl = builder.alloc_qubits(4)
        c0, c1, c2, c3 = ctrl
        # Original h, a, b sources are not modified.
        # The third construction reuses the witnessed c1=h*a relationship
        # instead of separately holding the conjunction a*b.
        builder.init_and(is_hc_zero, counter[0], c1)
        builder.init_and(is_hc_zero, counter[1], c2)
        builder.init_and(c1, counter[1], c3)
        builder.cx(c3, c1)
        builder.cx(c3, c2)
        builder.cx(km.array([is_hc_zero, c1, c2, c3]), c0)
        return ctrl

    @staticmethod
    def _del_counter_controls_sparse(builder, counter, is_hc_zero, ctrl):
        c0, c1, c2, c3 = ctrl
        builder.cx(km.array([is_hc_zero, c1, c2, c3]), c0)
        builder.cx(c3, c2)
        builder.cx(c3, c1)
        builder.del_and(c1, counter[1], c3)
        builder.del_and(is_hc_zero, counter[1], c2)
        builder.del_and(is_hc_zero, counter[0], c1)
        builder.free(ctrl)

    def _update_halting_sparse(self, builder, n_A, n_B, n_b,
                               halting_counter, flag, counter, *, is_adjoint):
        # The original is_c3 is required by this source update. Its lifetime
        # is the halting step only; the separate one-hot decoder no longer
        # depends on it being stored across the EEA update.
        is_c3 = builder.alloc_qubits(1)[0]
        builder.init_and(counter[0], counter[1], is_c3)
        self._update_halting_counter(
            builder, n_A, n_B, n_b, halting_counter, flag, is_c3,
            is_adjoint=is_adjoint
        )
        builder.del_and(counter[0], counter[1], is_c3)
        builder.free(is_c3)

    def _synchronized_eea(self, builder, reg_a, reg_b,
                          n_A, n_B, n_a, n_b, n_q, flag, counter,
                          halting_counter, *, n_iters, is_adjoint):
        eea_step = builder.mark('eea_step')
        for it in (range(n_iters - 1, -1, -1) if is_adjoint
                   else range(n_iters)):
            with eea_step:
                if is_adjoint:
                    self._update_counter(builder, counter, flag,
                                         is_adjoint=True)
                    self._update_halting_sparse(
                        builder, n_A, n_B, n_b, halting_counter, flag,
                        counter, is_adjoint=True
                    )

                is_hc_zero = builder.alloc_qubits(1)[0]
                builder.flip_if_equal(halting_counter, 0,
                                      target=is_hc_zero)
                ctrl = self._counter_controls_sparse(
                    builder, counter, is_hc_zero
                )

                steps = [
                    lambda: self._update_flag(
                        builder, reg_b, n_A, n_B, n_a, n_b, n_q,
                        flag, ctrl
                    ),
                    lambda: self._multiply_and_add_or_sub(
                        builder, reg_a, reg_b, n_A, n_a, n_q,
                        ctrl, it, is_adjoint=is_adjoint
                    ),
                    lambda: self._shift_b_array_right(
                        builder, reg_b, n_B, n_b, flag, ctrl,
                        it, is_adjoint=is_adjoint
                    ),
                    lambda: self._update_metadata(
                        builder, n_B, n_b, n_q, flag, ctrl,
                        is_adjoint=is_adjoint
                    ),
                    lambda: self._swap_a_and_b(
                        builder, reg_a, reg_b, n_A, n_B, n_a, n_b,
                        flag, ctrl
                    )
                ]
                for step in reversed(steps) if is_adjoint else steps:
                    step()

                self._del_counter_controls_sparse(
                    builder, counter, is_hc_zero, ctrl
                )
                builder.flip_if_equal(halting_counter, 0,
                                      target=is_hc_zero)
                builder.free(is_hc_zero)

                if not is_adjoint:
                    self._update_halting_sparse(
                        builder, n_A, n_B, n_b, halting_counter, flag,
                        counter, is_adjoint=False
                    )
                    self._update_counter(builder, counter, flag,
                                         is_adjoint=False)


def build_sparse_control_circuit(m: int, n: int, degree: int):
    """Same register contract, full EEA schedule and phase API as Experiment 020."""
    if degree != 12:
        raise ValueError("Only Experiment 020 authenticated GF(2^12) is supported")
    builder = km.CircuitBuilder()
    syndromes = [builder.create_quantum_register(degree, name=f'S{i}')
                 for i in range(n)]
    error_mbuc = [builder.create_classical_register(degree, name=f'E{j}')
                  for j in range(m)]
    SparseControlDecoder(
        n, km.GF2Field(degree), quotient_mode='norm_inverse'
    ).build_syndrome_decoding_mbuc(
        builder, syndromes=syndromes, error_mbuc=error_mbuc,
        n_iters=default_n_iters(n)
    )
    return builder.finish_circuit()
