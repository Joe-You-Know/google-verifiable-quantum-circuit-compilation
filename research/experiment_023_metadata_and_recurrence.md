# Experiment 023 — Typed metadata carriers and independent syndrome recurrence

**2026-11-21.** All implemented candidate circuits derive from our Experiment 022c; the supplied public competitor notebook is a reference for reported performance only. No third-party compiled circuits, gate words, or chemistry tables are reused.

## 1. Persistent source state

Experiment 022c reserves 1,803 persistent qubits before stage-local computation: 840 named syndrome qubits, 36 extra A coefficients, 876 B coefficients, and 51 metadata/control qubits (five eight-bit degree/position registers plus eleven other controls). Its compiled n70/m4095 Q is 1,865 and static T is 5,618,901.

The independent 023 candidate changes the five eight-bit degree/position registers to seven-bit representations, with A/B and a/b kept at equal operand widths for native comparisons. Root reserved Q becomes 1,798; field-element coefficient registers remain twelve bits and the conditional division and serial phase are unchanged. Narrowing only one of the degree-register pairs failed at native compilation with incompatible comparison widths. The paired and all-five reductions both compiled and passed the small DQI phase checks.

## 2. Measured native results

| Actual 70 syndrome × 4095 positions | Experiment 022c | Four narrow registers | Five narrow registers |
|---|---:|---:|---:|
| Physical qubits | 1865 | 1861 | **1860** |
| Static Toffoli-like gates | 5,618,901 | 5,605,821 | **5,602,269** |
| Operations | 85,389,880 | 85,286,416 | **85,255,780** |

The small n6/m15 original construction generated a byte-identical KMB digest to the authenticated 022c circuit: 9d43e33992d75de05782ba65a04b2eef1b5c26680c1a55cfae4dbcbfdbc7d72f.

The small 512-shot DQI sample gave 0 value and 0 phase errors in all three variants; Q respectively 311, 307, 306; static T respectively 113,521, 111,833, 111,353. At full n70/m4095, both narrowed candidates also passed the supplied DQI verifier on 512 development-confidence shots with zero value and phase errors. The all-five-narrow version had Q1860, mean T5,601,901.546875, and circuit SHA-256 754f9d3a46f08b7105b5e3a0bcb9ecf549307c237fb88406be27be27d6858c9e.

Native CI: https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44933516329

A separate adversarial native simulator test compared the original and both narrowed candidates on 256 arbitrary six-syndrome and 64 arbitrary seventy-syndrome cases, including deliberately chosen boundary inputs. All three restored the syndrome and scratch qubits and had identical phase outputs in those finite screens. The test is NOT exhaustive over all 840-bit syndrome inputs.

Source CI: https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44933734903

**Important status boundary:** A separate 102,400-shot n70/m4095 full-confidence verifier at log2_delta -128 was launched; its result was not yet available when this report was written. It must not be claimed to have passed. No new Kaggle submission was made.

Full-confidence job: https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44933734979

## 3. Derive source constraints instead of carrying both full polynomials

The supplied DQI contract defines syndrome words
    S_i = sum_j e_j * alpha^((i+1)j).
For a valid sparse error support x_j=alpha^j, define a locator
    Lambda(z) = product_(j with e_j nonzero) (1+x_j z).
Its product relation compels the late-moment recurrence
    sum_(h=0)^L Lambda_h S_(i-h) = 0
because each source x_j satisfies Lambda(1/x_j)=0. Preserve the original identities of the source x_j rather than treating the resulting scalar cancellation as the absence of its producer.

An independently coded classical recurrence computes Lambda, evaluator coefficients
    Omega_h = sum_(k=0)^h Lambda_k S_(h-k), for 0<=h<L,
and retrieves an error value only at a witnessed locator root z=1/x_j:
    e_j = Omega(z) / Lambda_prime(z).
When the derivative denominator is absent (field zero), no inverse is constructed and the source is explicitly marked unresolved rather than fabricated.

Independent first-party verifier generated data:
- n=6,m=15: 128 cases, 0 phase mismatches; maximum inferred degree 3.
- n=70,m=4095: 64 cases, 0 phase mismatches; maximum inferred degree 34, within the valid 35-error correction range.

Native source-check CI:
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44933586422

This is a CLASSICAL existence result over valid-error syndrome sources, not a reversible quantum decoder and not a measured cost reduction. Arbitrary syndrome inputs may have higher minimal recurrence degree. A quantum implementation must preserve all incoming coherent source states.

## 4. Source-forgetting recurrence is not reversible

Let D be the linear current-syndrome discrepancy functional and K a shifted previous locator with D(K)=b different from field zero. Consider the naive field correction
    U(C)=C+[D(C)/b]K.
For any t in the field,
    D(C+tK)=D(C)+tb,
    U(C+tK)=C+tK+[D(C)/b+t]K=U(C).
This is noninjective on unrestricted source states: a change in a previously distinguishable source can disappear at the output.

Exhaustive native GF(2^12) test: 4,096 **distinct normalized input polynomials** of the form C+tK were all mapped to **the same corrected polynomial**. Exactly one input had zero discrepancy and withheld the correction; the other source histories still produced that same output. This establishes a mathematically sharp absence-versus-existence witness.

CI:
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44933883296

The result rules out that particular source-forgetting operation as a standalone reversible quantum map. It does NOT establish a general lower bound for all possible source-conserving algorithms.

### Inverse-capable carrier, derived but not yet compiled

A source-preserving alternative introduces an independent field-element carrier f. Execute two successive field shears:
    f_new = f_old + D(C_old)/b
    C_new = C_old + f_new K.
The inverse uses
    C_old = C_new + f_new K
    f_old = f_new + D(C_old)/b.
These relations are exact and bijective for b nonzero. Starting with f_old zero produces the desired corrected polynomial while retaining the source quotient in f_new. A future causal witness must be established before that carrier can be lawfully released. Adding an independent twelve-bit carrier for every irreversible recurrence step could erase the memory advantage, so this alone is NOT an optimized quantum algorithm.

## 5. Consequence and next falsification

The target reported by the public notebook is 900 total qubits, of which the immutable benchmark inputs already require 840. Our current measured 1860-qubit candidate still reserves 876 qubits just for reg_b. This indicates the large next target is a new coherent method that avoids constructing an entire second 73-element polynomial array.

Before implementing another full decoder:
1. Compile a native, reversible GF(2^b) one-step discrepancy shear with its independent f carrier; verify all small-field basis states, zero-denominator nonconstruction, and exact inverse/clean ancilla.
2. Compose source-indexed recurrence steps and test whether earlier f values can be inferred from future retained original-source obligations without inventing an absent operation.
3. Quantify the Q/T tradeoff against the verified 022c baseline and the 023 narrowed metadata candidate. Only advance candidates with independently verified phase correctness.
4. Preserve the first-party Kaggle accepted Experiment 020 submission. A 512-shot development pass, a static native build and a predicted public score are not a completed official-confidence result.

All reported source evidence remains chronological; no corrections or failed modes are silently erased.


## 6. Later evidence: full local official-confidence DQI PASS

**Verified native GitHub Actions run (2026-11-21):**
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44933734979

The first-party DQI verifier API ran n70, m4095, degree12, **102,400 shots at log2_delta −128**, max_workers=1, using the native **all-five 7-bit** source candidate. Output:

| Exact full-confidence field | Observed |
|---|---:|
| Status | **PASS** |
| Physical Q | **1,860** |
| Mean Toffoli-like T | **5,601,918.613564453** |
| Static Toffoli-like T | **5,602,269** |
| Native circuit operations | **85,255,780** |
| Verified shots | **102,400** |
| Value errors | **0** |
| Phase errors | **0** |
| Effective error-rate bound | 0.0008660587301657926 |
| Repetition factor | 1.1912604648115832 |
| Reaction depth | 169,921 |
| DQI score (lower cost is better) | **23,087,101,495,484.246** |
| Circuit SHA-256 | 754f9d3a46f08b7105b5e3a0bcb9ecf549307c237fb88406be27be27d6858c9e |

The user's Experiment 020 officially tested local DQI cost was
23,555,742,358,022.918. The new full-confidence cost is **1.9894973%
lower** (ratio prior/new 1.02029882). If the other two benchmark costs
remain identical, a *model projection* based on the previous Kaggle
public score 1.03006 is approximately **1.03698**. This is NOT a Kaggle
server result; no new submission has been made.

The older pending status in section 2 is retained in chronological order,
and is superseded by this completed source-verifier receipt.

## 7. Later evidence: actual reversible quotient-carrier native construction

**Independent native test (2026-11-21):**
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44934219307

A fixed-source four-coefficient GF(2^12) recurrence shear was compiled
into a native Kickmix quantum circuit. The polynomial coefficients
occupy 48 qubits, with a separate 12-qubit carrier F. The source
discrepancy weights and shifted carrier K were fixed witnesses in this
isolated experiment; both can change in the eventual decoder, but that
larger case has NOT been implemented.

The forward map is the invertible carrier lift
    F_new = F_old + D(C_old)/b
    C_new = C_old + F_new K.

The inverse maps exactly back to the independent incoming C,F. The
native builder used **60 named qubits and zero additional scratch**:

| Native construction | Q | Static Toffolis | Operations | Basis cases | Errors |
|---|---:|---:|---:|---:|---:|
| Forward source-conserving lift | 60 | 0 | 104 | 8,192 | **0** |
| Forward and exact inverse | 60 | 0 | 208 | 8,192 | **0** |

All 4,096 previously colliding normalized field states remained
distinct in the joint (C_new,F_new) output. This is a demonstrated
reversible **one-step, fixed-denominator** quantum construction.
The zero-Toffoli count is special to the linear fixed-source case.
No result for dynamic quantum denominators, multiple recurrence
steps, complete DQI, or a 900-qubit implementation is claimed.

**Next mathematically decisive obligation:** determine whether a
future retained syndrome/locator relationship recovers the old F carrier
without retaining an ever-growing history. Without such a witness,
source-distinguishable absence and nonzero-correction histories must
remain separate; collapsing them would be nonunitary.
