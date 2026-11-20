# Experiment 014 — Fredrickson's Euclidean law and the DQI quotient scaffold

**2026-11-20, research notes; no Kaggle replacement circuit submitted.**

## Sources and boundaries

The following user-uploaded papers were reopened and compared with the
actual source at verifiers/dqi/dqi_reference_circuit.py:

1. Joseph Fredrickson, *Extended Euclidean Modular Inversion as a
   Primitive Constructive Law* v0.1, July 23, 2026, Theorem 4.1,
   Theorem 8.3, and the distinction in Section 14.
2. Joseph Fredrickson, *Dyadic Anchor Exclusion for Delayed Modular
   Inversion on secp256k1 Point Progression*, v0.1, July 23, 2026,
   Theorems 8.1, 9.1, 10.1, and Remark 8.3.
3. *Indexed Zero-Divisor Ledgers*, July 17, 2026,
   Theorem 5.1: no completed ratio when denominator is a zero
   contribution, but a typed finite evaluation ledger may survive.
4. *Primitive Constructive Logic*, v1.4 (October 11, 2026):
   separate source occurrence, retained constraints, and projected
   scalar equalities.

The original integer Euclidean source face uses
    L = qR + N,  0 <= N < R,
    c_N = c_L - q c_R,
    (L,c_L),(R,c_R) -> (R,c_R),(N,c_N).

The DQI *outer* Euclidean algorithm is synchronized and reversible
over GF(2^12)[X]; the descending measure is polynomial degree, and
"subtraction" of coefficient polynomials is equal to addition because
the field has characteristic two:
    A(X) = q(X) B(X) + N(X),  deg N < deg B,
    c_N(X) = c_A(X) + q(X)c_B(X).
All source polynomial coefficients are retained as distinct
constructive occurrences, despite numerical cancellation in GF(2).

The original integer unit-orientation determinant flip projects to
the *same* GF(2^12) determinant after a row exchange, because +1 and
-1 are equal as field elements. The integer signed orientation is not
recoverable by projecting solely into characteristic two. Distinct
source role labels can still retain the exchange history.

The dyadic anchor's integer inequalities and prime-field normalization
do not transfer literally to GF(2^12)[X]. The applicable part is the
explicit retained numerator/denominator and quotient/remainder
construction, with unit-closure, source and boundary roles separated.
The zero-divisor paper does not license a reciprocal at field element
zero. Quantum basis states with zero denominator must follow an
explicit totalized unitary convention compatible with the supplied
source and verifier, without constructing a fictitious inverse.

## The exact observed peak and its source

User WSL Experiment 013 on the original n=70, m=70, degree=12
source compiled to Q=1893 with no unknown source-live peak gap.
At the first peak:
- 840 named syndrome qubits;
- 963 root EEA workspace qubits;
- 6 qubits from the EEA step;
- 12 from multiply-and-add-or-sub;
- 72 from quotient_div;
- total 1893.
There are 888 observed peak events, and the first is event 299.

In source, quotient_div:
    ratio, scaffold = builder.init_gf2_div_with_scaffold(
        reg_b[index], reg_a[index], field=gf)
    builder.gf2_iadd(ratio, target=q_i, field=gf, control=control)
    builder.del_gf2_div_with_scaffold(...)
    builder.free(scaffold + ratio).

The coefficient ratio is computed *unconditionally*; its transfer
into q_i is conditional. This limits a naive zero-branch omission:
the required transfer must remain quantum coherent and reversible.

The actual Kickmix API probe run 44837285857 found at b=12:
- ratio register: 12 qubits;
- retained inverse scaffold: 60 qubits;
- total source witness 72 qubits;
- the same probe at b=4 found 4+8=12 qubits.

The source-preserving polynomial QR/shear test passed 500 pairs each
at b=4 and b=12, with 1066 and 1114 retained quotient steps,
respectively. These tests validate the algebraic transfer, not a
smaller circuit.

## Cost-model falsification and control requirement

Native b=12 quotient gadget measurements, CI 44837536500:

| Source implementation | Conditional? | Q total including input, output, ctrl | Static Toffolis |
|---|---|---:|---:|
| Hold ratio + inverse scaffold | Yes | 109 | 390 |
| Recompute inverse in cleanup | Yes | 109 | 705 |
| Direct quotient XOR | No | 97 | 378 |

The last implementation is NOT a legal drop-in replacement because
it updates q_i even when the source control is false.

Thus recomputation does not save Q; it merely increases T. The
mathematical source identity also does not alone remove any qubit.
The next candidate is to compute the inverse with its scaffold,
perform a **controlled field product directly into q_i** rather than
building the separate 12-bit quotient result, and release only the
inverse chain. This preserves the controlled source update, but its
actual Q/T must be measured and phase-validated. The native interface
exposes the required init_gf2_inverse_with_scaffold and
ixor_gf2_mul(...,control=control) primitives.

A build with lower Q must preserve the original DQI source law
across arbitrary quantum input superpositions, the numerator and
denominator values (including the zero branch), scratch cleanup and
the original syndrome/MBUC phase. The official DQI verifier still
has not been run on a replacement.

No claim about speedup, field inversion removal or Kaggle score
improvement is made before this is demonstrated.
