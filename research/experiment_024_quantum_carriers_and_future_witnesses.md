# Experiment 024 — Quantum-valued source carriers, two-step nonconstruction, and conditional recovery

**Date:** 2026-11-21. **Provenance:** Independent derivation from the user's own experimentally verified GF(2^12) fixed-source Experiment 023e two-shear map, not from a Kaggle competitor's circuit. The existing Experiment 023 decoder and the accepted Experiment 020 Kaggle ZIP are unchanged.

## 1. Original source recurrence, now quantum-valued

Each original source is a distinct quantum register: the four-element polynomial C, the five-element syndrome window S, the step-specific four-element K_j, denominator B_j and quotient carrier F_j. Each element is GF(2^d). Step j uses the independent source-indexed discrepancy

    D_j(C,S) = XOR_(i=0,...,3) C_i * S_(j+3-i).

A quantum flag z_j witnesses B_j != 0. The total source step is two shears in order:

    F_j+ = F_j XOR (z_j * D_j(C,S) * Inv(B_j))
    C_i+ = C_i XOR (z_j * F_j+ * K_(j,i)).

**Absent denominator:** B_j=0 implies z_j=0, so both F_j and C stay unchanged. No assertion that field-zero has an inverse is made: Kickmix's native inverse computation is a reversible total extension, with its *consequences gated off* at zero. Thus "no inverse constructed" is a mathematical value/causal-report claim, not the false claim that no gates are physically executed by the zero branch.

The exact reverse is

    C_i = C_i+ XOR (z_j * F_j+ * K_(j,i))
    F_j = F_j+ XOR (z_j * D_j(C,S) * Inv(B_j)).

The inverse restores C before recomputing D_j, so the discrepancy work can be uncomputed before C changes in forward order, and after C has been restored in adjoint order. The registers K, S and B are never altered. Native D_j and inverse-chain scratch registers are uncomputed before each source step ends. This is a reversible linear/nonlinear controlled map on *all* source basis states, whether or not the additional recurrence-witness condition B_j=D_j(K_j,S) happens to hold.

The latter relationship is independently recorded as a source-compatibility witness, not assumed from a gate-level Q result.

### Native source tests: both field widths

Github CI: https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44935805336

Each row tests 128 independently generated quantum source basis states including nonzero denominators, zero denominators, both consistency B_j=D_j(K_j,S) and inconsistent source assignments, and arbitrary initial F_j. Values, phases, K/S/B invariance and clean scratch are independently checked against the field-valued source law.

| Field | Native mode | Physical Q | Static Toffoli-like | Operations | Source cases | Phase/value/source/scratch errors |
|---|---|---:|---:|---:|---:|---:|
| GF(2^4) | one forward | 77 | 163 | 1,641 | 128 | **0** |
| GF(2^4) | one forward + exact inverse | 77 | 326 | 3,283 | 128 | **0** |
| GF(2^4) | two forward | 101 | 326 | 3,283 | 128 | **0** |
| GF(2^4) | two forward + exact inverse | 101 | 652 | 6,567 | 128 | **0** |
| GF(2^12) | one forward | 265 | 1,218 | 14,560 | 128 | **0** |
| GF(2^12) | one forward + exact inverse | 265 | 2,436 | 29,121 | 128 | **0** |
| GF(2^12) | two forward | 337 | 2,436 | 29,121 | 128 | **0** |
| GF(2^12) | two forward + exact inverse | 337 | 4,872 | 58,243 | 128 | **0** |

In the GF(2^12) two-step tests, 128 of 256 source denominators were zero and 128 were marked B=D(K,S) consistent. Every corresponding controlled null step left its source untouched; all scratch and source checks passed.

## 2. What the SECOND step can and cannot determine

For the first and second corrected polynomials, with initial F1=F2=0:

    C1 = C0 XOR (z1 * F1 * K1)
    C2 = C1 XOR (z2 * F2 * K2).

The second step's D2 depends only on C1, S and its own retained parameters. Holding those original parameters fixed, two distinct C0 states that map to one C1 cannot be separated by any later deterministic consequence computed exclusively from C1 and those parameters.

A specific fully witnessed GF(2^12) family:

    S=(3,1,2,7,9),
    K1=(0,1,0,0),   B1=D1(K1,S)=2,
    K2=(0,1,1,0),   B2=D2(K2,S)=5,
    C0(t)=(1,3,5,9) XOR t*K1.

Across all **4096** field elements t, the two-step source law produced **4096 distinct complete outputs when F1 was retained**, and only **ONE distinct projected (C2,F2) output when F1 was omitted**. The second denominator is nonzero and source-compatible; the obstruction is not merely a trivial second absent branch.

This is an exact finite-field source-fiber counterexample to universal *recovery from the second step alone*. It does NOT rule out recovery using another independently retained original source, and it is not a lower bound against other DQI decoder architectures.

## 3. An additional original-source witness gives a precise recovery criterion

Let L(C) denote the coefficient C[1]. Suppose the original quantum source W=L(C0) has been preserved independently. Then

    W XOR L(C2) XOR z2*F2*L(K2) = z1*F1*L(K1).

If B1!=0 (so z1=1) and L(K1)!=0, the quotient is uniquely determined:

    F1 = [W XOR L(C2) XOR z2*F2*L(K2)] / L(K1).

The zero-denominator branch B1=0 needs no inverse and leaves the initially empty F1 empty. If B1!=0 and L(K1)=0, this specific witness **cannot** recover F1, and the source carrier must remain. If W is incorrect, a nonzero source residual can remain: do not silently free F1.

### Native conditional recovery with quantum W

Native CI: https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44935992604

Exact native GF(2^12) two-step recovery uses 352 Q, 3,049 static Toffoli-like, and 37,634 operations (forward). It passed 128 independent source tests, including:
- all true-witness/nonzero-slope cases had F1 returned to zero;
- 16 deliberately missing-slope cases retained a nonzero F1 rather than discarding it;
- 32 false-source-witness cases produced an observable nonzero F1 residual;
- 32 absent-denominator cases kept their initially empty F1 empty;
- every original source K/S/B/W was preserved, scratch cleaned, no phase/value deviations;
- exact full reverse passed another 128 cases (Q352, T6098).

GF(2^4) independently passed the same branch tests (Q108 forward, Q108 exact reverse).

The witness W is an *extra* twelve-qubit register here. Recovery does not automatically reduce space: it trades retained F1 against W unless W is shown to be an already present source.

## 4. Existing syndrome as witness: distinct source promise

The experiment also implements the alternative W=S0, i.e., it reuses one existing named original syndrome register instead of allocating a new twelve-qubit witness register. Its mathematical precondition is

    C_initial[1] = S0.

This relation is **not assumed to hold in the currently verified full DQI decoder**. The trial explicitly tests it as a constrained input family, and injects violations to test that a nonzero source residual remains distinguishable. Both consistent and inconsistent cases must be reported.

The Q savings in this isolated trial are versus the *extra-witness* one-step microcircuit, not the accepted DQI implementation. There is still no proof that every actual recurrence occurrence has such a retained source or that an arbitrary quantum state permits releasing that carrier. Only an internally derived, maintained source relation—not a promise sampled from test data—would authorize unconditional physical freeing of F1.

**The final native results for this variant should be appended from the CI receipt, not presumed in advance.**

## 5. Requirements for end-to-end DQI space savings

1. Identify actual source boundaries in a complete causal reversible locator construction where L(C0) is already an original retained syndrome register (or uniquely determined by such a register), with exact occurrence identities.
2. Verify the required nonzero source slope, or route the unresolved L(K1)=0 case to another witnessed relation without inventing an inverse.
3. Implement physical uncomputation and allocator release of F1 within an internally enforced source relationship, then later legal recomputation if exact reverse evolution needs it.
4. Measure per-step and global live quantum Q and T against Experiment 023's fully locally verified Q1860 / 5,602,269 static T decoder. A toy source carrier alone cannot claim an 876-Q polynomial-array saving.
5. Run full-phase and scratch verification and finally the 102,400-shot -128 verifier before any Kaggle submission. Keep all accepted baseline artifacts unchanged.

**Demonstrated:** two reversible quantum-valued recurrence steps with null/non-null denominator branch, full reverse cleanup, exact two-step future-only insufficiency, and conditional original-source quantum quotient recovery.

**Not established:** a fully reversible multi-round BM decoder that releases all intermediate carriers, whether a suitable witness already exists in all DQI source states, persistent Q reduction for full DQI, and a new Kaggle leaderboard score.


## 6. Later native evidence — original syndrome reused instead of independent W

**2026-11-21, completed CI:** https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44936146345

The source-constrained witness test was repeated with **W an alias of the already named original quantum register S0**, under the explicitly declared input relation

    C_initial[1] = S0.

This changes no arithmetic operation. Its only physical resource difference
from the independent-W test is that no additional 12-bit W source register
is allocated. Importantly, source consistency here is a tested **input
subspace condition**, not something presently proved for the accepted DQI
source. Invalid-source cases were also injected and remained distinguishable.

| GF(2^12) quantum native witness mode | Separate W | W=S0 source reuse |
|---|---:|---:|
| Physical Q | 352 | **340** |
| Static Toffoli-like T | 3,049 | 3,049 |
| Native operations | 37,634 | 37,634 |
| Tested forward cases | 128 | 128 |
| Value/phase errors | 0 | 0 |
| Dirty workspace | 0 | 0 |
| Valid-witness first carriers nonzero after recovery | 0 | 0 |
| Missing-slope unresolved nonzero carriers | 16 | 16 |
| False-witness residuals retained | 32 | 32 |
| Absent-denominator source identities | 32 | 32 |
| Exact inverse tested | 128 PASS | 128 PASS |

In GF(2^4), the analogous native comparison reduced physical Q
from 108 to 104 with identical 408 static Toffoli-like operations, and
both forward and adjoint checks PASS.

**What was actually demonstrated:** when a source-register relationship
exists, already retained source storage may serve as the witness required
to recover a previously distinct quotient history. Both quantum-valued
K,b branches and all original sources remain intact on the tested
relations, and independent invalid-source tests exhibit the expected
nonzero residual rather than false cleanup.

**Not demonstrated:** source relation internally enforced on the entire
admissible DQI input subspace; unconditional allocator release of F1;
a native full multi-round reversible locator architecture; any decrease
from Experiment 023's accepted-for-local-verifier 1860 Q baseline; or
a Kaggle score change. The 12 Q comparison above is **microcircuit
witness-register reuse**, not a full decoder saving.
