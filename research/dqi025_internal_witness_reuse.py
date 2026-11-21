"""Experiment 025 — internally witnessed quantum carrier release and reallocation.

Independent extension of our 024 native reversible two-step finite-field
source law, *not* a copied public decoder.

Original inputs are only five source syndrome words S and two quantum
four-coefficient carrier source polynomials K1,K2. The working C polynomial
is freshly allocated in its zero state and constructed as C_i = S_i for
i=0,..,3. This guarantees the original-source witness, rather than
postulating C_initial[i] = S_i as an incoming restriction.

B_j is ALSO constructed in the circuit from the original source
relationship B_j = D_j(K_j,S). Therefore B_1 != 0 implies at least one
coefficient of K_1 is nonzero. An exclusive first-nonzero-coefficient
selector (indexed by original source occurrence, not numerical value)
recovers F_1 from any nonzero slope.

When the initial F1 is zero, the post-two-step source relation is
  S_i + C2_i + z2*F2*K2_i = z1*F1*K1_i.
For B1!=0, use the first i with K1_i!=0 to determine F1; when B1=0,
F1 was never constructed and remains empty. The full unitary is a
controlled XOR and retains meaning off the intended source subspace.

Once zero, the 12-bit F1 register is actually freed, a 12-word block of
derived future workspace is allocated and uncomputed, and 12 bits are
allocated anew. The original F1 is reconstructed from the same retained
sources before running the exact adjoints of the two steps.

A matched "retain" control runs identical operations without releasing
F1. The compiled native peak Q, original S and K, all temporary work and
the final quantum phase are then compared.

This is a source-conserving TOY TWO-STEP recurrence, not yet a full DQI
decoder or a verified 876-qubit polynomial-array removal.
"""
from __future__ import annotations
import kickmix as km

from research.dqi024_quantum_carrier import (
    field_discrepancy, source_step,
)


def recover_all_coefficient_witnesses(builder, C, S, K, B, F, field):
    """Toggle F1 using guaranteed original-source witnesses S[0:4].

    The selection is a disjoint source decision: the first nonzero
    ORIGINAL coefficient K1[i], conditioned on witnessed B1!=0.
    All select, inverse and product scratch states are uncomputed.
    """
    degree=field.degree
    z1=builder.alloc_qubits(1)[0]
    z2=builder.alloc_qubits(1)[0]
    builder.flip_if_equal(B[0],0,target=z1)
    builder.x(z1)
    builder.flip_if_equal(B[1],0,target=z2)
    builder.x(z2)

    for i in range(4):
        with builder.mark(f"coefficient_witness_{i}"):
            earlier_zero=builder.alloc_qubits(1)[0]
            current_nonzero=builder.alloc_qubits(1)[0]
            temp=builder.alloc_qubits(1)[0]
            selected=builder.alloc_qubits(1)[0]

            if i==0:
                builder.x(earlier_zero)
            else:
                earlier=km.array([
                    q for previous in K[0][:i] for q in previous])
                builder.flip_if_equal(earlier,0,target=earlier_zero)

            builder.flip_if_equal(K[0][i],0,target=current_nonzero)
            builder.x(current_nonzero)
            builder.init_and(z1,earlier_zero,temp)
            builder.init_and(temp,current_nonzero,selected)

            delta=builder.alloc_qubits(degree)
            builder.cx(S[i],delta)
            builder.cx(C[i],delta)
            builder.ixor_gf2_mul(F[1],K[1][i],target=delta,
                                field=field,control=z2)

            inverse_slope=builder.alloc_qubits(degree)
            _, chain=builder.init_gf2_inverse_with_scaffold(
                K[0][i],target=inverse_slope,field=field)
            builder.ixor_gf2_mul(delta,inverse_slope,target=F[0],
                                field=field,control=selected)
            builder.del_gf2_inverse_with_scaffold(
                K[0][i],target=inverse_slope,scaffold=chain,field=field)
            builder.free(chain)
            builder.free(inverse_slope)

            builder.ixor_gf2_mul(F[1],K[1][i],target=delta,
                                field=field,control=z2)
            builder.cx(C[i],delta)
            builder.cx(S[i],delta)
            builder.free(delta)

            builder.del_and(temp,current_nonzero,selected)
            builder.del_and(z1,earlier_zero,temp)
            builder.x(current_nonzero)
            builder.flip_if_equal(K[0][i],0,target=current_nonzero)
            if i==0:
                builder.x(earlier_zero)
            else:
                builder.flip_if_equal(earlier,0,target=earlier_zero)
            builder.free(km.array([
                earlier_zero,current_nonzero,temp,selected
            ]))

    builder.x(z2)
    builder.flip_if_equal(B[1],0,target=z2)
    builder.x(z1)
    builder.flip_if_equal(B[0],0,target=z1)
    builder.free(km.array([z1,z2]))


def future_source_workspace(builder,S,K,field,*,word_count=12):
    """Witnessed ephemeral future source products, 12 field-word storage.

    This is a controlled test of peak simultaneous storage. Both no-release
    and release variants perform identical arithmetic and exact cleanup;
    the workspace is not offered as a novel DQI decoder stage.
    """
    with builder.mark("future_workspace"):
        words=[builder.alloc_qubits(field.degree)
               for _ in range(word_count)]
        first_word_ids=(
            tuple(int(q.id) for q in words[0]) if words else ()
        )
        for j in range(word_count):
            source_row, column = divmod(j,4)
            s=S[source_row]
            k=K[0 if source_row==2 else source_row][column]
            builder.ixor_gf2_mul(s,k,target=words[j],field=field)
        for j in reversed(range(word_count)):
            source_row, column = divmod(j,4)
            s=S[source_row]
            k=K[0 if source_row==2 else source_row][column]
            builder.ixor_gf2_mul(s,k,target=words[j],field=field)
        for item in reversed(words):
            builder.free(item)
        return first_word_ids


def build_internal_witness_circuit(*,degree=12,release_first=True,
                                   workspace_words=12):
    """Finish an exact quantum identity on arbitrary S,K basis inputs."""
    if degree not in (4,12):
        raise ValueError("native experimental field must be 4 or 12")
    builder=km.CircuitBuilder()
    gf=km.GF2Field(degree)

    # The only quantum INPUTS: these sources are never touched by
    # initialization/uncomputation gates.
    S=[builder.create_quantum_register(degree,name=f"S{i}")
       for i in range(5)]
    K=[[builder.create_quantum_register(degree,name=f"K{j}_{i}")
        for i in range(4)] for j in range(2)]

    # All work starts empty and is later restored to empty.
    C=[builder.alloc_qubits(degree) for _ in range(4)]
    B=[builder.alloc_qubits(degree) for _ in range(2)]
    F=[builder.alloc_qubits(degree) for _ in range(2)]
    original_f1_ids=tuple(int(q.id) for q in F[0])

    # Witness W_i = S_i is enforced for ALL incoming quantum S,K.
    with builder.mark("construct_original_locator_source"):
        for i in range(4):
            builder.cx(S[i],C[i])
    with builder.mark("construct_original_denominator_sources"):
        for j in range(2):
            field_discrepancy(builder,K[j],S,j,B[j],gf)

    # Carry two independent quotient histories.
    with builder.mark("forward_step1"):
        source_step(builder,C,K[0],S,B[0],F[0],gf,offset=0)
    with builder.mark("forward_step2"):
        source_step(builder,C,K[1],S,B[1],F[1],gf,offset=1)

    # A *constructed* relation, not an input test promise, now
    # forces F1 to zero for all original source states.
    with builder.mark("recover_first_from_original_sources"):
        recover_all_coefficient_witnesses(builder,C,S,K,B,F,gf)

    # Explicit free + reuse, with matched no-release control.
    if release_first:
        builder.free(F[0])
    with builder.mark("derived_future_workspace"):
        first_future_ids=future_source_workspace(
            builder,S,K,gf,word_count=workspace_words)
    if release_first:
        F[0]=builder.alloc_qubits(degree)
    reconstructed_f1_ids=tuple(int(q.id) for q in F[0])

    with builder.mark("reconstruct_original_f1_for_exact_reverse"):
        recover_all_coefficient_witnesses(builder,C,S,K,B,F,gf)

    with builder.mark("reverse_step2"):
        source_step(builder,C,K[1],S,B[1],F[1],gf,
                    offset=1,adjoint=True)
    with builder.mark("reverse_step1"):
        source_step(builder,C,K[0],S,B[0],F[0],gf,
                    offset=0,adjoint=True)

    with builder.mark("uncompute_denominators"):
        for j in (1,0):
            field_discrepancy(builder,K[j],S,j,B[j],gf)
    with builder.mark("uncompute_original_locator"):
        for i in reversed(range(4)):
            builder.cx(S[i],C[i])

    for reg in (F[1],F[0],B[1],B[0],*reversed(C)):
        builder.free(reg)
    circuit=builder.finish_circuit()
    return circuit,{"S":S,"K":K,
                    "original_f1_physical_ids":original_f1_ids,
                    "reallocated_f1_physical_ids":reconstructed_f1_ids,
                    "physical_F1_ids_reused":(
                        original_f1_ids==reconstructed_f1_ids),
                    "first_future_word_ids":first_future_ids,
                    "released_F1_slot_reused_by_future_word":(
                        set(original_f1_ids)==set(first_future_ids)),
                    "field_degree":degree,
                    "release_first":release_first,
                    "workspace_words":workspace_words}
