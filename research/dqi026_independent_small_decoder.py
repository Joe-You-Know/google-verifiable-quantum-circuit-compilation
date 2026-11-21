"""Experiment 026c: independent small complete DQI source locator/Forney phase.

This is our own Reed–Solomon syndrome-source construction. No competitor
decoder, circuit, gate word or chemistry table is copied.

For n=6 and m<=15 at GF(2^12):
- resolve the smallest degree 0..3 satisfying all source moments;
- build canonical locator Lambda(z)=1+c1*z+c2*z²+c3*z³;
- build Omega(z)=[Lambda(z)*sum_(i>=0) S_i*z^i] at degree<3;
- locate each error at z=alpha^(-position);
- apply masked phase for Omega(z)/Lambda'(z) at witnessed roots;
- reverse every constructed source locator, condition and field inverse.

This uses ONLY original named quantum syndrome sources and classical mask
bits. There is NO persistent polynomial K_j history, F_j quotient history
or source atlas of possible input syndromes.

The expression is valid for sparse distinct error sources. If an
arbitrary syndrome source is unresolved or yields a repeated locator root
with vanishing derivative, the program never asserts a missing inverse.
The supplied DQI verifier is the authority for actual source-state
restoration, correct phase and cost.
"""
from __future__ import annotations
import kickmix as km
from research.dqi026_rank_adaptive import (
    toggle_degree_valid, xor_selected_locator,
)


def xor_field_const(builder,source,target,const,gf):
    """XOR constant-times original field source via a GF2 linear map."""
    for bit in range(gf.degree):
        image=int(gf.mul(1<<bit,int(const)))
        for obit in range(gf.degree):
            if (image>>obit)&1:
                builder.cx(source[bit],target[obit])


def toggle_locator_eval(builder,C,z,target,gf):
    builder.x(target[0])  # constant one
    power=int(z)
    for source in C:
        xor_field_const(builder,source,target,power,gf)
        power=int(gf.mul(power,z))


def toggle_derivative_eval(builder,C,z,target,gf):
    power=1
    for i,source in enumerate(C,1):
        if i&1:
            xor_field_const(builder,source,target,power,gf)
        power=int(gf.mul(power,z))


def toggle_evaluator_eval(builder,C,S,z,target,gf):
    """Omega(z): only first t coefficients, with no coefficient history."""
    power=1
    for h in range(len(C)):
        xor_field_const(builder,S[h],target,power,gf)
        for k in range(1,h+1):
            temp=builder.alloc_qubits(gf.degree)
            builder.ixor_gf2_mul(
                C[k-1],S[h-k],target=temp,field=gf)
            xor_field_const(builder,temp,target,power,gf)
            builder.ixor_gf2_mul(
                C[k-1],S[h-k],target=temp,field=gf)
            builder.free(temp)
        power=int(gf.mul(power,z))


def apply_position_phase(builder,C,S,resolved,mask,z,gf,position):
    with builder.mark(f"chien_forney_position_{position}"):
        locator=builder.alloc_qubits(gf.degree)
        derivative=builder.alloc_qubits(gf.degree)
        numerator=builder.alloc_qubits(gf.degree)
        toggle_locator_eval(builder,C,z,locator,gf)
        toggle_derivative_eval(builder,C,z,derivative,gf)
        toggle_evaluator_eval(builder,C,S,z,numerator,gf)

        root=builder.alloc_qubits(1)[0]
        derivative_nonzero=builder.alloc_qubits(1)[0]
        temp=builder.alloc_qubits(1)[0]
        active=builder.alloc_qubits(1)[0]
        builder.flip_if_equal(locator,0,target=root)
        builder.flip_if_equal(derivative,0,target=derivative_nonzero)
        builder.x(derivative_nonzero)
        builder.init_and(root,derivative_nonzero,temp)
        builder.init_and(temp,resolved,active)

        reciprocal=builder.alloc_qubits(gf.degree)
        _,chain=builder.init_gf2_inverse_with_scaffold(
            derivative,target=reciprocal,field=gf)
        error_value=builder.alloc_qubits(gf.degree)
        builder.ixor_gf2_mul(
            numerator,reciprocal,target=error_value,
            field=gf,control=active)

        for bit in range(gf.degree):
            builder.push_condition(mask[bit])
            builder.z(error_value[bit])
            builder.pop_condition()

        builder.ixor_gf2_mul(
            numerator,reciprocal,target=error_value,
            field=gf,control=active)
        builder.free(error_value)
        builder.del_gf2_inverse_with_scaffold(
            derivative,target=reciprocal,scaffold=chain,field=gf)
        builder.free(chain)
        builder.free(reciprocal)

        builder.del_and(temp,resolved,active)
        builder.del_and(root,derivative_nonzero,temp)
        builder.x(derivative_nonzero)
        builder.flip_if_equal(derivative,0,target=derivative_nonzero)
        builder.flip_if_equal(locator,0,target=root)
        builder.free(km.array([active,temp,derivative_nonzero,root]))

        toggle_evaluator_eval(builder,C,S,z,numerator,gf)
        toggle_derivative_eval(builder,C,z,derivative,gf)
        toggle_locator_eval(builder,C,z,locator,gf)
        builder.free(numerator)
        builder.free(derivative)
        builder.free(locator)


def build_small_independent_dqi(*,m=15,n=6,degree=12):
    if (n,degree)!=(6,12) or not 6<=m<=15:
        raise ValueError("Experiment026c n=6, degree12, 6<=m<=15")
    b=km.CircuitBuilder()
    gf=km.GF2Field(degree)
    S=[b.create_quantum_register(degree,name=f"S{i}")
       for i in range(n)]
    masks=[b.create_classical_register(degree,name=f"E{j}")
           for j in range(m)]
    C=[b.alloc_qubits(degree) for _ in range(n//2)]
    resolved=b.alloc_qubits(1)[0]
    flags=b.alloc_qubits(n//2+1)

    with b.mark("construct_rank_adaptive_locator"):
        for d in range(n//2+1):
            toggle_degree_valid(b,S,d,flags[d],gf)
        b.flip_if_equal(flags,0,target=resolved)
        b.x(resolved)
        xor_selected_locator(b,S,flags,C,gf)

    order=(1<<degree)-1
    primitive=gf.primitive_element
    for position in range(m):
        quotient,exp=divmod(order-position,order)
        assert order-position==quotient*order+exp
        z=int(gf.pow(primitive,exp))
        apply_position_phase(b,C,S,resolved,masks[position],
                             z,gf,position)

    with b.mark("uncompute_rank_adaptive_locator"):
        xor_selected_locator(b,S,flags,C,gf)
        b.x(resolved)
        b.flip_if_equal(flags,0,target=resolved)
        for d in reversed(range(n//2+1)):
            toggle_degree_valid(b,S,d,flags[d],gf)

    b.free(flags)
    b.free(resolved)
    for item in reversed(C):
        b.free(item)

    return b.finish_circuit()
