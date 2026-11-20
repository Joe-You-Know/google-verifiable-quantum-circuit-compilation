# Experiment 010 — Locator-relative syndrome phase via polynomial QR

**Date:** 2026-11-20  
**Status:** Exact finite-field identity tested at toy degrees; 392 exhaustive
single-error GF(8) controls, 150 randomized GF(16) two-error controls,
complete trace-dual pairing checks and 1,000 deterministic GF(16) sparse
error/mask cases of weights 0..3 all PASS in GitHub Actions run
44830497018. **No reversible quantum circuit synthesized; no scored
Toffoli improvement claimed.**

## Source framing

The unmodified DQI verifier defines an error word e with support size
k<=n/2, a classical MBUC mask M_j for every field position, and observed
syndromes

    S_i = sum_(j in support) e_j * x_j^(i+1),  x_j=alpha^j.

The desired phase bit is the bitwise binary pairing

    phase = XOR_(j in support) dot_bits(M_j, e_j).

The current supplied DQI source separately reconstructs each root's
Forney value via a reversible inverse scaffold. Experiment 009 measured
315 Toffolis for that inverse round trip at degree 12, plus 24 zero
detector and 12 located-AND Toffolis per position. Experiment 008 measured
351 incremental Toffolis for each m position independently of syndrome
counts n=6,8,12 (at degree 12).

The alternative here **does not require constructing each e_j as an
intermediate output**. It replaces their individual inverse relationships
with a single locator-relative polynomial quotient and remainder.

## Construction and proof

Write GF = GF(2^b), q=2^b, and let x_j=alpha^j enumerate the q-1
nonzero field elements. Let Tr(z)=sum_{t=0}^{b-1} z^(2^t), an element
of GF(2). The trace pairing is nondegenerate. For each classical mask M_j
there is a unique field element d_j such that

    Tr(d_j e) = dot_bits(M_j, e) for every e in GF.

The entire classical mask input defines a polynomial F_M of degree
strictly less than q-1, uniquely specified on nonzero elements by

    F_M(x_j) = d_j / x_j.

Its coefficients may be constructed **from classical mask bits only**.
For m=q-1, explicit inverse multiplicative-group transforms give

    c_i = sum_(j=0)^(m-1) d_j * x_j^(-(i+1)),
    F_M(X) = sum_(i=0)^(m-1) c_i X^i.

This follows from orthogonality of nonzero-field powers; m is odd,
so the m identical terms at equal evaluation points sum to 1 in
characteristic two. These coefficients are classical-source producers,
not newly assumed quantum observables.

Let J be the error support and

    L_J(X) = product_(j in J) (X + x_j)

the monic locator polynomial of degree k=|J|. Perform **explicit
polynomial quotient and remainder**, retaining both producers:

    F_M(X) = Q_J(X) L_J(X) + R_J(X),   degree(R_J)<k.

At every actual error root, L_J(x_j)=0, so
R_J(x_j)=F_M(x_j)=d_j/x_j.

Write R_J(X)=sum_(i=0)^(k-1) r_i X^i. Then:

    sum_i r_i S_i
      = sum_j e_j x_j sum_i r_i x_j^i
      = sum_j e_j x_j R_J(x_j)
      = sum_j e_j d_j.

Applying the field trace to both sides:

    Tr(sum_i r_i S_i)
      = XOR_j dot_bits(M_j, e_j).

This is exactly the required DQI phase. For k=0, the source has
zero phase and the construction reports zero remainder.

No candidate error positions, decoded e_j array or per-root
field inverse are required as *outputs* of the replacement identity.
Only the original syndromes, the locator and the input mask are used.

## Verification

The Python audit independently constructs the trace-dual transform
from all field basis elements, interpolates F_M, confirms its value
at each x_j, constructs L from the actual support, verifies its QR
reconstruction, computes the retained syndrome pairing and independently
compares with the original bitwise phase.

Observed GitHub CI:
- all 392 GF(8) cases with one arbitrary nonzero error and its mask PASS;
- 150 seeded GF(16) two-error controls PASS;
- all 16x16 GF(16) trace-dual basis/function pairings PASS;
- 1,000 seeded GF(16) random cases, weight 0..3, PASS;
- no failed polynomial QR construction or interpolation witness.

Source: scripts/dqi010_syndrome_phase_qr.py and
research/test_dqi010_syndrome_phase_qr.py. CI run 44830497018.

## Resource blocker and next experiment

The identity is exact, but its practical cost is *unknown*. In
particular, computing R_J when the locator coefficients are quantum is
not a free operation. A naive polynomial long-division circuit of
degree (q-2) by degree k can require up to (q-1-k)*k nonconstant
field multiplications; for q=4096 and k=35 that is 142,100
field multiplications. This could cost much more than the 1,289,925
Toffolis of 4,095 inverse scaffolds in the existing reference.

Therefore do NOT call this a cryptographic/quantum speedup or a valid
Kaggle submission yet. The next experiment is to derive and implement a
bounded, inverse-free **reversible remainder transport** using the
quantum locator and classical F_M. It must preserve syndrome
restoration, all ancilla cleanup, phase on arbitrary input
superpositions and the supplied verifier's low error bound.

First target: small b=3 or b=4 and k<=2. Compile both implementations
with Kickmix, compare exact phase and all register outputs over every
basis-state input, and measure Toffoli-like cost and qubits. If the
remainder circuit costs more, retain the counterexample rather than
claiming an advantage.
