"""Experiment 026: source-regenerated multi-round locator constraints.

This independently derives a multi-round Reed–Solomon locator coefficient
construction from the DQI syndrome source equation, not from third-party
circuits or code. It solves the source Hankel system

  H[i,j] = S[t+i-j-1], y[i] = S[t+i], 0<=i,j<t.
  H c = y.

The polynomial 1 + c[0] z + ... + c[t-1] z^t satisfies the last t
syndrome recurrence constraints exactly if det(H)!=0.

For j=0..t-1, a quantum K_j = adj(H)[:,j] is GENERATED from ORIGINAL
quantum syndromes only, rather than stored as a polynomial history.
Its source determinant B=det(H) obeys H K_j = B e_j. This creates
c_i ^= (y_j / B) K_{j,i}. At B=0 no inverse/correction is claimed;
the output coefficient state remains zero and status is "unresolved".
The source B, K_j and quotient registers are all uncomputed.

Two circuits share the same source equations and final phase:
- "history": retain each source quotient F_j until reverse evolution.
- "streaming": uncompute F_j immediately from original y_j and B;
  free its physical slots, regenerate it from retained originals only
  when reversing that contribution.

No K_j histories are retained in EITHER circuit. Physical storage
counts include determinant, inverse scaffold, all cofactors, selected
round's coefficient registers, and retained F_j histories.
Reconstruction costs additional gates, so this is a real Q/T tradeoff.
This is an exact source-defined locator solution on the nonsingular
degree-t stratum. It does NOT solve the singular lower-degree cases
or constitute a complete DQI decoder.
"""
from __future__ import annotations
from itertools import permutations

import kickmix as km


def hankel_matrix(S, t):
    assert len(S) == 2 * t
    return [[S[t + i - j - 1] for j in range(t)]
            for i in range(t)]


def xor_field_determinant(builder, M, target, gf):
    """Reversible field determinant source production for 0<=size<=4.

    Characteristic two: all Leibniz permutation signs are +.
    Scratch from each product chain is cleaned before the next chain.
    The ORIGINAL quantum source matrix entries are never modified.
    """
    n=len(M)
    assert n <= 4 and all(len(row)==n for row in M)
    if n==0:
        builder.x(target[0])
        return
    if n==1:
        builder.cx(M[0][0],target)
        return
    for ordering in permutations(range(n)):
        if n==2:
            builder.ixor_gf2_mul(M[0][ordering[0]],M[1][ordering[1]],
                                target=target,field=gf)
            continue
        scratch=[]
        first=builder.alloc_qubits(gf.degree)
        builder.ixor_gf2_mul(M[0][ordering[0]],M[1][ordering[1]],
                            target=first,field=gf)
        scratch.append(first)
        for i in range(2,n):
            if i==n-1:
                builder.ixor_gf2_mul(
                    scratch[-1],M[i][ordering[i]],
                    target=target,field=gf)
            else:
                tmp=builder.alloc_qubits(gf.degree)
                builder.ixor_gf2_mul(
                    scratch[-1],M[i][ordering[i]],
                    target=tmp,field=gf)
                scratch.append(tmp)
        for i in range(len(scratch)-1,-1,-1):
            if i==0:
                builder.ixor_gf2_mul(
                    M[0][ordering[0]],M[1][ordering[1]],
                    target=scratch[i],field=gf)
            else:
                builder.ixor_gf2_mul(
                    scratch[i-1],M[i+1][ordering[i+1]],
                    target=scratch[i],field=gf)
            builder.free(scratch[i])


def minor_matrix(M,row,col):
    return [[entry for j,entry in enumerate(items) if j!=col]
            for i,items in enumerate(M) if i!=row]


def construct_adjugate_column(builder,H,column,out,gf):
    """Out[i] ^= cofactor[H row=column, col=i] for every original i."""
    assert len(H)==len(out)
    for i in range(len(out)):
        xor_field_determinant(
            builder,minor_matrix(H,column,i),out[i],gf)


def phase_usage(builder,C,S):
    """Small test phase makes a locator coefficient an actual observable."""
    builder.cz(C[0][0],S[1][0])
    if len(C)>1:
        builder.cz(C[1][1],S[0][1])


def build_multiround_locator(*,degree=12,rounds=3,mode="streaming"):
    if degree not in (4,12):
        raise ValueError("native source field requires degree 4 or 12")
    if not (1<=rounds<=4):
        raise ValueError("native first study has 1..4 syndrome constraints")
    if mode not in ("streaming","history"):
        raise ValueError("expected streaming or history")

    b=km.CircuitBuilder()
    gf=km.GF2Field(degree)
    S=[b.create_quantum_register(degree,name=f"S{i}")
       for i in range(2*rounds)]
    H=hankel_matrix(S,rounds)
    C=[b.alloc_qubits(degree) for _ in range(rounds)]

    with b.mark("original_source_Hankel_determinant"):
        det=b.alloc_qubits(degree)
        xor_field_determinant(b,H,det,gf)

    # Native finite-field inverse is a reversible total extension,
    # but its consequence is gated off when det=0.
    with b.mark("source_inverse_scaffold"):
        active=b.alloc_qubits(1)[0]
        b.flip_if_equal(det,0,target=active)
        b.x(active)
        inv=b.alloc_qubits(degree)
        _,inv_chain=b.init_gf2_inverse_with_scaffold(
            det,target=inv,field=gf)

    current_original_f=[]
    all_original_f=[]
    source_k_physical_ids=[]
    round_carrier_physical_ids=[]
    for j in range(rounds):
        with b.mark(f"construct_round_{j}_cofactor_and_quotient"):
            K=[b.alloc_qubits(degree) for _ in range(rounds)]
            source_k_physical_ids.append(tuple(
                tuple(int(q.id) for q in item) for item in K))
            construct_adjugate_column(b,H,j,K,gf)
            F=b.alloc_qubits(degree)
            round_carrier_physical_ids.append(
                tuple(int(q.id) for q in F))
            b.ixor_gf2_mul(S[rounds+j],inv,target=F,
                              field=gf,control=active)
            for i in range(rounds):
                b.ixor_gf2_mul(F,K[i],target=C[i],
                                  field=gf,control=active)
            # The witness that determines F is the original syndrome
            # S[t+j] and *the same* determinant produced from source.
            # This intentionally does not create a history-polynomial K.
            if mode=="streaming":
                b.ixor_gf2_mul(S[rounds+j],inv,target=F,
                                  field=gf,control=active)
                b.free(F)
            else:
                current_original_f.append(F)
            construct_adjugate_column(b,H,j,K,gf)
            for item in reversed(K):
                b.free(item)

    with b.mark("phase_from_constructed_locator"):
        phase_usage(b,C,S)

    for j in reversed(range(rounds)):
        with b.mark(f"reverse_round_{j}_reconstruct_from_original_sources"):
            K=[b.alloc_qubits(degree) for _ in range(rounds)]
            construct_adjugate_column(b,H,j,K,gf)
            if mode=="streaming":
                F=b.alloc_qubits(degree)
                b.ixor_gf2_mul(S[rounds+j],inv,target=F,
                              field=gf,control=active)
            else:
                F=current_original_f[j]
            for i in reversed(range(rounds)):
                b.ixor_gf2_mul(F,K[i],target=C[i],
                              field=gf,control=active)
            b.ixor_gf2_mul(S[rounds+j],inv,target=F,
                          field=gf,control=active)
            b.free(F)
            construct_adjugate_column(b,H,j,K,gf)
            for item in reversed(K):
                b.free(item)

    with b.mark("uncompute_original_source_inverse"):
        b.del_gf2_inverse_with_scaffold(
            det,target=inv,scaffold=inv_chain,field=gf)
        b.free(inv_chain)
        b.free(inv)
        b.x(active)
        b.flip_if_equal(det,0,target=active)
        b.free(active)
    with b.mark("uncompute_original_source_determinant"):
        xor_field_determinant(b,H,det,gf)
        b.free(det)
    for item in reversed(C):
        b.free(item)

    circuit=b.finish_circuit()
    return circuit,{
        "S":S,
        "rounds":rounds,
        "degree":degree,
        "mode":mode,
        "construction":"Hankel adjugate columns regenerated from retained syndromes",
        "history_polynomial_K_registers_retained":0,
        "quotient_F_registers_retained_during_forward":
            rounds if mode=="history" else 0,
        "cofactor_original_physical_slots":source_k_physical_ids,
        "forward_quotient_physical_slots":round_carrier_physical_ids,
        "singular_det_scope":"no corrections; locator unresolved",
    }


def determinant_value(gf,mat):
    n=len(mat)
    if not n:return 1
    v=0
    for perm in permutations(range(n)):
        p=1
        for i in range(n):
            p=int(gf.mul(p,int(mat[i][perm[i]])))
        v^=p
    return v


def minor_value(gf,mat,row,col):
    return determinant_value(
        gf,[[x for j,x in enumerate(items) if j!=col]
            for i,items in enumerate(mat) if i!=row])


def classical_locator_from_syndromes(gf,S,rounds):
    H=[[int(S[rounds+i-j-1]) for j in range(rounds)]
       for i in range(rounds)]
    y=[int(S[rounds+i]) for i in range(rounds)]
    det=determinant_value(gf,H)
    C=[0]*rounds
    if det:
        inverse=int(gf.pow(det,(1<<gf.degree)-2))
        for j in range(rounds):
            ratio=int(gf.mul(y[j],inverse))
            for i in range(rounds):
                cofactor=minor_value(gf,H,j,i)
                C[i]^=int(gf.mul(ratio,cofactor))
    residuals=[]
    for j in range(rounds):
        actual=y[j]
        for i in range(rounds):
            actual^=int(gf.mul(H[j][i],C[i]))
        residuals.append(actual)
    return {
        "coefficients":C,
        "source_determinant":det,
        "source_equations_residuals":residuals,
        "rank_chart":"FULL_RANK" if det else "SINGULAR_UNRESOLVED",
    }
