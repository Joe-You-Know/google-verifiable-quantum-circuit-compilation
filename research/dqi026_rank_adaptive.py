"""Experiment 026b: coherent variable-degree Reed–Solomon locator source atlas.

For a maximum correction radius t, original input is exactly 2t syndromes.
Each candidate locator degree d is produced on demand from its ORIGINAL
Hankel constraints, checked against *all* 2t syndrome moments, then
uncomputed. Source flags choose the MINIMUM valid d; no K-polynomial
histories, quotient histories or candidate locators remain retained.

- d=0 is valid exactly if every syndrome is field zero.
- d>=1 is valid iff det(H_d) !=0 AND every source recurrence residual
  for k=d,...,2t-1 is zero.
- If no candidate is valid, output resolved=0 and leave coefficients
  zero (an explicit unresolved source, not a fabricated locator).

The valid source syndrome distribution with at most t distinct nonzero
error positions has a witnessable minimal locator degree, including
all lower-rank cases. Arbitrary 2t-word syndrome inputs need not have
such a locator; this circuit conservatively distinguishes those cases.

The construction uses determinant adjugates expanded for t<=3.
It does not copy any public competitor circuit or claim a scalable
t=35 determinant implementation. All source arrays are quantum.
"""
from __future__ import annotations
import kickmix as km
from research.dqi026_hankel_locator import (
    hankel_matrix,
    xor_field_determinant,
    construct_adjugate_column,
    classical_locator_from_syndromes,
    phase_usage,
)


def xor_rank_locator(builder,S,degree,C,field):
    """Toggle the original-source degree-d candidate into existing C."""
    if degree<=0:
        return
    H=hankel_matrix(S[:2*degree],degree)
    with builder.mark(f"source_locator_degree_{degree}"):
        det=builder.alloc_qubits(field.degree)
        xor_field_determinant(builder,H,det,field)
        active=builder.alloc_qubits(1)[0]
        builder.flip_if_equal(det,0,target=active)
        builder.x(active)
        inverse=builder.alloc_qubits(field.degree)
        _,scaffold=builder.init_gf2_inverse_with_scaffold(
            det,target=inverse,field=field)
        for row in range(degree):
            with builder.mark(f"original_source_row_{row}"):
                K=[builder.alloc_qubits(field.degree)
                   for _ in range(degree)]
                construct_adjugate_column(builder,H,row,K,field)
                quotient=builder.alloc_qubits(field.degree)
                builder.ixor_gf2_mul(
                    S[degree+row],inverse,target=quotient,
                    control=active,field=field)
                for i in range(degree):
                    builder.ixor_gf2_mul(
                        quotient,K[i],target=C[i],
                        control=active,field=field)
                builder.ixor_gf2_mul(
                    S[degree+row],inverse,target=quotient,
                    control=active,field=field)
                builder.free(quotient)
                construct_adjugate_column(builder,H,row,K,field)
                for reg in reversed(K):
                    builder.free(reg)
        builder.del_gf2_inverse_with_scaffold(
            det,target=inverse,scaffold=scaffold,field=field)
        builder.free(scaffold)
        builder.free(inverse)
        builder.x(active)
        builder.flip_if_equal(det,0,target=active)
        builder.free(active)
        xor_field_determinant(builder,H,det,field)
        builder.free(det)


def xor_recurrence_residual(builder,S,C,k,degree,target,field):
    """Source discrepancy S[k]+sum_i C[i]*S[k-i-1], reversible XOR."""
    builder.cx(S[k],target)
    for i in range(degree):
        builder.ixor_gf2_mul(C[i],S[k-i-1],
                            target=target,field=field)


def toggle_degree_valid(builder,S,degree,valid,field):
    """XOR the witnessed-degree predicate into an existing valid bit.

    All workspace is released before return. Running twice uncomputes.
    A degree flag is not a single solution: it states the exact original
    source recurrence holds for *all available syndrome indices*.
    """
    n=len(S)
    if degree==0:
        syndrome_source=km.array([q for reg in S for q in reg])
        builder.flip_if_equal(syndrome_source,0,target=valid)
        return

    C=[builder.alloc_qubits(field.degree) for _ in range(degree)]
    xor_rank_locator(builder,S,degree,C,field)

    H=hankel_matrix(S[:2*degree],degree)
    det=builder.alloc_qubits(field.degree)
    xor_field_determinant(builder,H,det,field)
    active=builder.alloc_qubits(1)[0]
    builder.flip_if_equal(det,0,target=active)
    builder.x(active)

    # All n-degree recurrences are examined; their original source
    # identity remains visible. Counter counts failures, not a
    # conflated scalar-zero claim.
    bad_width=max(1,(n-degree).bit_length())
    bad_count=builder.alloc_qubits(bad_width)
    for k in range(degree,n):
        residual=builder.alloc_qubits(field.degree)
        xor_recurrence_residual(
            builder,S,C,k,degree,residual,field)
        nonzero=builder.alloc_qubits(1)[0]
        builder.flip_if_equal(residual,0,target=nonzero)
        builder.x(nonzero)
        builder.iadd(1,target=bad_count,control=nonzero)
        builder.x(nonzero)
        builder.flip_if_equal(residual,0,target=nonzero)
        builder.free(nonzero)
        xor_recurrence_residual(
            builder,S,C,k,degree,residual,field)
        builder.free(residual)

    no_fail=builder.alloc_qubits(1)[0]
    builder.flip_if_equal(bad_count,0,target=no_fail)
    builder.ccx(active,no_fail,valid)
    builder.flip_if_equal(bad_count,0,target=no_fail)
    builder.free(no_fail)

    for k in reversed(range(degree,n)):
        residual=builder.alloc_qubits(field.degree)
        xor_recurrence_residual(
            builder,S,C,k,degree,residual,field)
        nonzero=builder.alloc_qubits(1)[0]
        builder.flip_if_equal(residual,0,target=nonzero)
        builder.x(nonzero)
        builder.isub(1,target=bad_count,control=nonzero)
        builder.x(nonzero)
        builder.flip_if_equal(residual,0,target=nonzero)
        builder.free(nonzero)
        xor_recurrence_residual(
            builder,S,C,k,degree,residual,field)
        builder.free(residual)
    builder.free(bad_count)
    builder.x(active)
    builder.flip_if_equal(det,0,target=active)
    builder.free(active)
    xor_field_determinant(builder,H,det,field)
    builder.free(det)
    xor_rank_locator(builder,S,degree,C,field)
    for reg in reversed(C):
        builder.free(reg)


def xor_selected_locator(builder,S,flags,out,field):
    """Choose first source-valid degree without storing a polynomial atlas.

    The repeated adjugate computation is the explicit T-cost of not
    retaining candidate/quotient polynomial histories.
    """
    for degree in range(1,len(flags)):
        previous_empty=builder.alloc_qubits(1)[0]
        prefix=km.array(flags[:degree])
        builder.flip_if_equal(prefix,0,target=previous_empty)
        chosen=builder.alloc_qubits(1)[0]
        builder.init_and(flags[degree],previous_empty,chosen)
        candidate=[builder.alloc_qubits(field.degree)
                   for _ in range(degree)]
        xor_rank_locator(builder,S,degree,candidate,field)
        for i in range(degree):
            for bit in range(field.degree):
                builder.ccx(chosen,candidate[i][bit],out[i][bit])
        xor_rank_locator(builder,S,degree,candidate,field)
        for reg in reversed(candidate):
            builder.free(reg)
        builder.del_and(flags[degree],previous_empty,chosen)
        builder.flip_if_equal(prefix,0,target=previous_empty)
        builder.free(km.array([chosen,previous_empty]))


def build_rank_adaptive_locator(*,field_degree=12,max_degree=3,
                                probe=True):
    if field_degree not in (4,12):
        raise ValueError("Only original native GF4 and GF12 controls")
    if not 1<=max_degree<=3:
        raise ValueError("Rank-adaptive first test max degree 1..3")
    builder=km.CircuitBuilder()
    gf=km.GF2Field(field_degree)
    S=[builder.create_quantum_register(field_degree,name=f"S{i}")
       for i in range(2*max_degree)]
    if probe:
        C=[builder.create_quantum_register(field_degree,name=f"L{i+1}")
           for i in range(max_degree)]
        resolved=builder.create_quantum_register(1,name="resolved")[0]
    else:
        C=[builder.alloc_qubits(field_degree)
           for _ in range(max_degree)]
        resolved=builder.alloc_qubits(1)[0]

    flags=builder.alloc_qubits(max_degree+1)
    with builder.mark("derive_exact_original_source_degree_flags"):
        for degree in range(max_degree+1):
            toggle_degree_valid(builder,S,degree,flags[degree],gf)

    builder.flip_if_equal(flags,0,target=resolved)
    builder.x(resolved)

    with builder.mark("select_minimal_original_source_locator"):
        xor_selected_locator(builder,S,flags,C,gf)
    if not probe:
        with builder.mark("use_resolved_locator_phase"):
            phase_usage(builder,C,S)
        with builder.mark("uncompute_minimal_locator_from_source"):
            xor_selected_locator(builder,S,flags,C,gf)
        builder.x(resolved)
        builder.flip_if_equal(flags,0,target=resolved)
        builder.free(resolved)

    with builder.mark("uncompute_original_source_degree_flags"):
        for degree in reversed(range(max_degree+1)):
            toggle_degree_valid(builder,S,degree,flags[degree],gf)
    builder.free(flags)
    if not probe:
        for item in reversed(C):
            builder.free(item)
    return builder.finish_circuit(),{
        "S":S,"locator":C,"resolved":resolved,
        "mode":"source_locator_probe" if probe else "phase_roundtrip",
        "max_degree":max_degree,
        "field_degree":field_degree,
        "retained_K_histories":0,
        "retained_quotient_histories":0,
        "selector_flag_qubits":max_degree+1,
        "singular_root":"recheck lower degrees; otherwise unresolved",
    }


def classical_minimal_locator(gf,S,max_degree):
    if not any(S):
        return {"resolved":True,"degree":0,
                "coefficients":[0]*max_degree,
                "witness":"ALL_SYNDROMES_ZERO"}
    for d in range(1,max_degree+1):
        item=classical_locator_from_syndromes(gf,S,d)
        if not item["source_determinant"]:
            continue
        cc=item["coefficients"]
        residuals=[]
        for k in range(d,len(S)):
            residual=int(S[k])
            for i in range(d):
                residual^=int(gf.mul(
                    int(cc[i]),int(S[k-i-1])))
            residuals.append(residual)
        if not any(residuals):
            return {"resolved":True,"degree":d,
                    "coefficients":cc+[0]*(max_degree-d),
                    "witness":"FULL_ORIGINAL_SYNDROME_RECURRENCE"}
    return {"resolved":False,"degree":None,
            "coefficients":[0]*max_degree,
            "witness":"NO_WITNESSED_DEGREE; NOT_A_ZERO_ERROR_LOCATOR"}
