"""Experiment 022b: serial source-directed Forney phase-carrier construction.

The exact verified Experiment 020 EEA is retained. A 12-bit vector of
located = is_sigma_zero AND omega is replaced by one reused quantum bit.

GF(2) distributivity determines the phase contribution bit by bit:
  popcount(mask & (located * inverse))
  = XOR_{i,j,k} [located_i & inverse_j & mask_k &
                 bit_k(field.mul(1<<i, 1<<j))]
No reciprocal or zero branch is invented. mask is an existing classical
register. Each phase is a CZ under that classical bit condition.
This trades more non-Toffoli instructions for a smaller simultaneous quantum
register, without a public competitor circuit.
"""
from __future__ import annotations
from typing import Sequence
import kickmix as km

from research.dqi020_experimental_decoder import (
    ProosAndZalkaDecoder as Experiment020Decoder,
    default_n_iters,
)


def phase_connection_map(field: km.GF2Field):
    degree = field.degree
    return tuple(
        tuple(
            tuple(j for j in range(degree)
                  if (field.mul(1 << i, 1 << j) >> bit) & 1)
            for bit in range(degree)
        )
        for i in range(degree)
    )


def serial_controlled_field_phase(builder, flag, omega, inverse, mask, field,
                                  *, carrier=None, plan=None):
    """Apply the original zero-gated field-product phase with one carrier bit."""
    plan = phase_connection_map(field) if plan is None else plan
    if carrier is None:
        carrier = builder.alloc_qubits(1)[0]
        owns_carrier = True
    else:
        owns_carrier = False

    assert len(omega) == len(inverse) == len(mask) == field.degree
    for i in range(field.degree):
        builder.init_and(flag, omega[i], carrier)
        for mask_bit, inverse_indices in enumerate(plan[i]):
            if not inverse_indices:
                continue
            builder.push_condition(mask[mask_bit])
            builder.cz(carrier, km.array([inverse[j]
                                          for j in inverse_indices]))
            builder.pop_condition()
        builder.del_and(flag, omega[i], carrier)
    if owns_carrier:
        builder.free(carrier)


class SerialForneyDecoder(Experiment020Decoder):
    """Same EEA and Chien/Forney schedule, serial quantum phase carrier only."""

    def _chien_search_and_forney_mbuc(self, builder: km.CircuitBuilder,
                                      reg_b: Sequence[km.array],
                                      error_mbuc: Sequence[km.array],
                                      n_b: km.array, n_B: km.array) -> None:
        gf = self.field
        degree = gf.degree
        m = len(reg_b)
        t = self.n_syndromes // 2
        block_length = (1 << degree) - 1
        primitive = gf.primitive_element

        with builder.mark('pre_align_reg_b'):
            self._pre_align_reg_b(builder, reg_b, n_b, n_B, is_adjoint=False)

        sigma = reg_b[0]
        sigma_prime = reg_b[1]
        omega = reg_b[m // 2 + t]
        sigma_prime_inv = builder.alloc_qubits(degree)
        located_carrier = builder.alloc_qubits(1)[0]
        is_sigma_zero = builder.alloc_qubits(1)[0]
        is_error = builder.alloc_bits(1)
        phase_plan = phase_connection_map(gf)

        omega_indices = range(m // 2 + 1, m // 2 + t + 1)
        step_multipliers = [
            (k, gf.pow(primitive, k))
            for k in range(1, t + 1)
        ] + [
            (k, gf.pow(primitive, (m - 2 - k) % block_length))
            for k in omega_indices
            if (m - 2 - k) % block_length != 0
        ]

        sum_pairs = (
            [(reg_b[k], omega) for k in range(m // 2 + 1, m // 2 + t)]
            + [(reg_b[k], sigma_prime) for k in range(3, t + 1, 2)]
            + [(reg_b[k], sigma) for k in range(2, t + 1, 2)]
            + [(sigma_prime, sigma)]
        )
        fwd_src = km.array([q for src, _ in sum_pairs for q in src])
        fwd_dst = km.array([q for _, dst in sum_pairs for q in dst])
        rev_src = km.array([q for src, _ in reversed(sum_pairs) for q in src])
        rev_dst = km.array([q for _, dst in reversed(sum_pairs) for q in dst])

        num_positions = min(block_length, len(error_mbuc))
        forney_step = builder.mark('forney_step')
        for j in range(num_positions):
            with forney_step:
                builder.bit_store(is_error[0], True, control=error_mbuc[j])
                builder.push_condition(is_error[0])

                builder.cx(fwd_src, fwd_dst)
                builder.flip_if_equal(sigma, 0, target=is_sigma_zero)

                _, inverse_chain = builder.init_gf2_inverse_with_scaffold(
                    sigma_prime, target=sigma_prime_inv, field=gf)

                serial_controlled_field_phase(
                    builder, is_sigma_zero, omega, sigma_prime_inv,
                    error_mbuc[j], gf,
                    carrier=located_carrier, plan=phase_plan)

                builder.del_gf2_inverse_with_scaffold(
                    sigma_prime, target=sigma_prime_inv,
                    scaffold=inverse_chain, field=gf)
                builder.free(inverse_chain)

                builder.flip_if_equal(sigma, 0, target=is_sigma_zero)
                builder.cx(rev_src, rev_dst)

                builder.pop_condition()
                builder.bit_store(is_error, False)

                if j + 1 < num_positions:
                    for k, step in step_multipliers:
                        builder.gf2_imul(step, target=reg_b[k], field=gf)

        if num_positions > 1:
            for k, step in step_multipliers:
                builder.gf2_idiv(
                    gf.pow(step, num_positions - 1),
                    target=reg_b[k], field=gf)

        builder.free(is_error)
        builder.free(located_carrier)
        builder.free(sigma_prime_inv + km.array([is_sigma_zero]))
        with builder.mark('unalign_reg_b'):
            self._pre_align_reg_b(builder, reg_b, n_b, n_B, is_adjoint=True)


def build_serial_forney_circuit(m: int, n: int, degree: int):
    """Same DQI input register names and coherent norm EEA as Experiment 020."""
    if degree != 12:
        raise ValueError("The authenticated Experiment 020 norm EEA requires GF(2^12)")
    builder = km.CircuitBuilder()
    syndromes = [builder.create_quantum_register(degree, name=f'S{i}')
                 for i in range(n)]
    masks = [builder.create_classical_register(degree, name=f'E{j}')
             for j in range(m)]
    SerialForneyDecoder(n, km.GF2Field(degree),
                        quotient_mode='norm_inverse').build_syndrome_decoding_mbuc(
                            builder, syndromes=syndromes, error_mbuc=masks,
                            n_iters=default_n_iters(n))
    return builder.finish_circuit()
