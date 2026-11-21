"""Experiment 024: quantum source K and b with explicit nonconstruction at b=0.

Native two-shear update over GF(2^d), using only our independently verified
Experiment 023 source law. All C, K, S, B, F registers are quantum-valued:
  d_j(C,S) = XOR_i C_i * S_(j+3-i)
  z_j = [B_j != 0]
  F_j' = F_j XOR (z_j * d_j(C,S) * Inv(B_j))
  C_i' = C_i XOR (z_j * F_j' * K_(j,i)).
The totalized *native inverse subroutine* has to be checked at B=0;
we explicitly gate its consequences by z_j. No field inverse is asserted
to exist at zero. The construction itself never changes C for B=0.

The inverse of a step reverses C's field shear before reconstructing its
original discrepancy and undoing F's shear. Source K, B and S are unchanged.
This does not assert B = d_j(K,S); that is a separate source-compatibility
constraint that tests must record, not smuggle into a unitary gate.
"""
from __future__ import annotations
from typing import Sequence
import kickmix as km


def field_discrepancy(builder, C, S, offset, target, field):
    assert len(C) == 4 and len(S) == 5
    for i in range(4):
        builder.ixor_gf2_mul(C[i], S[offset + 3 - i],
                            target=target, field=field)


def source_step(builder, C, K, S, B, F, field, *,
                offset=0, adjoint=False):
    """Exact source-preserving quantum shear; all scratch uncomputed."""
    assert len(C) == len(K) == 4
    assert 0 <= offset <= 1
    with builder.mark("quantum_source_step_backward"
                      if adjoint else "quantum_source_step_forward"):
        active = builder.alloc_qubits(1)[0]
        builder.flip_if_equal(B, 0, target=active)
        builder.x(active)

        # Inverse order: first restore C to the state that was input
        # when the forward F-update computed its discrepancy.
        if adjoint:
            for i in reversed(range(4)):
                builder.ixor_gf2_mul(F, K[i], target=C[i],
                                    field=field, control=active)

        discrepancy = builder.alloc_qubits(field.degree)
        field_discrepancy(builder, C, S, offset, discrepancy, field)

        inv_b = builder.alloc_qubits(field.degree)
        _, chain = builder.init_gf2_inverse_with_scaffold(
            B, target=inv_b, field=field)

        # b=0: no quotient is consumed and no carrier/locator changes.
        builder.ixor_gf2_mul(discrepancy, inv_b, target=F,
                            field=field, control=active)

        builder.del_gf2_inverse_with_scaffold(
            B, target=inv_b, scaffold=chain, field=field)
        builder.free(chain)
        builder.free(inv_b)

        field_discrepancy(builder, C, S, offset, discrepancy, field)
        builder.free(discrepancy)

        if not adjoint:
            for i in range(4):
                builder.ixor_gf2_mul(F, K[i], target=C[i],
                                    field=field, control=active)

        builder.x(active)
        builder.flip_if_equal(B, 0, target=active)
        builder.free(active)



def recover_first_with_external_witness(builder, C, K, B, F, W, field):
    """Conditional, reversible recovery of F1 from an ORIGINAL source W=C0[1].

    At the end of two steps the source relation is
      W + C2[1] + z2*F2*K2[1] = z1*F1*K1[1].
    If B1!=0 and K1[1]!=0, divide the witnessed difference by K1[1]
    and XOR it into F1. This sends F1 to the empty state ONLY when W
    really is the retained initial source, F1 started at zero, and the
    two-step source law was followed. For absent denominators/degenerate
    slopes it explicitly leaves F1 retained rather than inventing a value.
    The gate map is a reversible XOR even outside that promised subspace.
    """
    with builder.mark("future_source_witness_release"):
        if len(C) != 4 or len(K) != 2 or len(B) != 2:
            raise ValueError("must follow exactly two source-indexed steps")

        z1 = builder.alloc_qubits(1)[0]
        z2 = builder.alloc_qubits(1)[0]
        knz = builder.alloc_qubits(1)[0]
        enabled = builder.alloc_qubits(1)[0]
        builder.flip_if_equal(B[0], 0, target=z1)
        builder.x(z1)
        builder.flip_if_equal(B[1], 0, target=z2)
        builder.x(z2)
        builder.flip_if_equal(K[0][1], 0, target=knz)
        builder.x(knz)
        builder.init_and(z1, knz, enabled)

        delta_w = builder.alloc_qubits(field.degree)
        builder.cx(W, delta_w)
        builder.cx(C[1], delta_w)
        builder.ixor_gf2_mul(F[1], K[1][1], target=delta_w,
                            field=field, control=z2)

        inv_k = builder.alloc_qubits(field.degree)
        _, inv_chain = builder.init_gf2_inverse_with_scaffold(
            K[0][1], target=inv_k, field=field)
        builder.ixor_gf2_mul(delta_w, inv_k, target=F[0],
                            field=field, control=enabled)
        builder.del_gf2_inverse_with_scaffold(
            K[0][1], target=inv_k, scaffold=inv_chain, field=field)
        builder.free(inv_chain)
        builder.free(inv_k)

        builder.ixor_gf2_mul(F[1], K[1][1], target=delta_w,
                            field=field, control=z2)
        builder.cx(C[1], delta_w)
        builder.cx(W, delta_w)
        builder.free(delta_w)

        builder.del_and(z1, knz, enabled)
        builder.x(knz)
        builder.flip_if_equal(K[0][1], 0, target=knz)
        builder.x(z2)
        builder.flip_if_equal(B[1], 0, target=z2)
        builder.x(z1)
        builder.flip_if_equal(B[0], 0, target=z1)
        builder.free(km.array([z1,z2,knz,enabled]))


def build_dynamic_quantum_steps(*, degree=12, steps=1, roundtrip=False,
                               recover_first=False):
    if degree not in (4, 12):
        raise ValueError("only native trial field degrees 4 and 12")
    if steps not in (1, 2):
        raise ValueError("only 1 or 2 source-indexed steps")
    b = km.CircuitBuilder()
    C = [b.create_quantum_register(degree, name=f"C{i}") for i in range(4)]
    S = [b.create_quantum_register(degree, name=f"S{i}") for i in range(5)]
    K = [
        [b.create_quantum_register(degree, name=f"K{j}_{i}")
         for i in range(4)]
        for j in range(steps)
    ]
    B = [b.create_quantum_register(degree, name=f"B{j}")
         for j in range(steps)]
    F = [b.create_quantum_register(degree, name=f"F{j}")
         for j in range(steps)]
    gf = km.GF2Field(degree)
    W = (b.create_quantum_register(degree, name="W_initial_coefficient1")
         if recover_first else None)
    if recover_first and steps != 2:
        raise ValueError("recovery requires two source-indexed steps")
    for j in range(steps):
        source_step(b, C, K[j], S, B[j], F[j], gf, offset=j)
    if recover_first:
        recover_first_with_external_witness(b, C, K, B, F, W, gf)
    if roundtrip:
        if recover_first:
            recover_first_with_external_witness(b, C, K, B, F, W, gf)
        for j in reversed(range(steps)):
            source_step(b, C, K[j], S, B[j], F[j], gf,
                        offset=j, adjoint=True)
    return b.finish_circuit(), {
        "C":C, "S":S, "K":K, "B":B, "F":F, "W":W,
    }


def discrepancy_value(gf,C,S,step):
    value=0
    for i in range(4):
        value ^= int(gf.mul(int(C[i]),int(S[step+3-i])))
    return value


def classical_step(gf,C,K,S,B,F,step,*,adjoint=False):
    original=list(C)
    f=int(F)
    active=(int(B)!=0)
    if adjoint and active:
        original=[int(c)^int(gf.mul(f,int(k)))
                  for c,k in zip(original,K)]
    if active:
        d=discrepancy_value(gf,original,S,step)
        inverse=int(gf.pow(int(B),(1<<gf.degree)-2))
        f ^= int(gf.mul(d,inverse))
    if not adjoint and active:
        original=[int(c)^int(gf.mul(f,int(k)))
                  for c,k in zip(original,K)]
    return original,f


def classical_two(gf,C,K,S,B,F,*,adjoint=False):
    cc=list(C)
    ff=list(F)
    order=range(len(B)-1,-1,-1) if adjoint else range(len(B))
    for j in order:
        cc,ff[j]=classical_step(
            gf,cc,K[j],S,B[j],ff[j],j,adjoint=adjoint)
    return cc,ff


def classical_witness_check(gf,*, exhaustive=True):
    """Two-step cannot recover F1 from C2,F2 alone; adds independent W."""
    degree=gf.degree
    if not exhaustive and degree>4:
        raise ValueError("Use finite-field exhaustion to prove collision")
    # S, K, B are fixed here to isolate a complete source-collision family.
    S=[3,1,2,7,9]
    K1=[0,1,0,0]
    K2=[0,1,1,0]
    B1=discrepancy_value(gf,K1,S,0)
    B2=discrepancy_value(gf,K2,S,1)
    assert B1 and B2 and K1[1]
    C0=[1,3,5,9]
    seen_full=set()
    seen_without_first_carrier=set()
    first_carriers=set()
    recovered=0
    for t in range(1<<degree):
        C_in=[int(c)^int(gf.mul(t,int(k)))
              for c,k in zip(C0,K1)]
        C_out,F_out=classical_two(
            gf,C_in,[K1,K2],S,[B1,B2],[0,0])
        full=(*C_out,F_out[0],F_out[1])
        seen_full.add(full)
        seen_without_first_carrier.add((*C_out,F_out[1]))
        first_carriers.add(F_out[0])
        # Independent original-source W=C_in[1], sourced before overwrite.
        witness=C_in[1]
        # C1_1=C2_1+F2*K2_1 since B2 nonzero.
        c1_1=C_out[1]^int(gf.mul(F_out[1],K2[1]))
        observed=witness^c1_1
        k1_inv=int(gf.pow(K1[1],(1<<degree)-2))
        recovered_f1=int(gf.mul(observed,k1_inv))
        assert recovered_f1==F_out[0],(t,F_out,recovered_f1)
        recovered+=1
    return {
       "degree":degree,"source_family_size":1<<degree,
       "step1_denominator":B1,"step2_denominator":B2,
       "first_carrier_distinct_values":len(first_carriers),
       "complete_output_distinct":len(seen_full),
       "after_forgetting_first_carrier_distinct":len(seen_without_first_carrier),
       "second_step_alone_recovers_first_carrier":False,
       "independent_witness":"W=C_initial[1]",
       "witness_slope":K1[1],
       "witness_recovery_cases":recovered,
       "extra_witness_may_need_additional_qubits":True,
       "witness_is_not_implied_by_step2":True,
    }
