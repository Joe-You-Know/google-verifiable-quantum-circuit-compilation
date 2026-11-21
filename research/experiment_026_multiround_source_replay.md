# Experiment 026 — multi-round source-regenerated locator constraints, no retained polynomial history

**2026-11-21. Source:** user-authored Experiment 025 reversible source-conservation work, and the original first-party DQI syndrome equation. No competitor circuit, gates or tables copied.

## What changed from Experiment 025

The two-step source identity in Experiment 025 demonstrated physical carrier release, but it retained separate original input polynomials K1 and K2. Retaining K_j of length t over t rounds scales as t squared field words, potentially costing more qubits than quotient release saves.

This experiment instead constructs each round's K_j on demand from the exact original syndrome sources, uses it and uncomputes it before the next round. No K polynomials are named quantum inputs and none is retained between rounds.

For a degree-t locator polynomial 1+c1 z+...+ct z^t, the original syndrome recurrence is

    S_k + sum_(i=1)^t c_i S_(k-i)=0, k=t,...,2t-1.

Define source Hankel matrix H_(row,col)=S_(t+row-col-1) and source y_row=S_(t+row). The t equations are Hc=y. For det(H) nonzero, let column K_j=adj(H) e_j. The original-source identity

    H K_j = det(H) e_j

gives a deterministic quotient for each independent row: q_j=y_j / det(H) and c= sum_j q_j K_j. The original S source registers determine and witness EVERY q_j; they need not be preserved as separate historical quantum registers once their contribution is applied.

The native circuit explicitly constructs det(H) and its reversible inverse witness. It computes each cofactor column K_j from the ORIGINAL S registers using the determinant's field-product laws, applies q_j K_j to the working locator, and uncomputes K_j. At det(H)=0 it does not pretend to have a field inverse; the correction is disabled and the result is explicitly marked SINGULAR_UNRESOLVED.

Two matched native circuits test the workspace policy:
- HISTORY: retain all q_j field registers until exact reverse.
- STREAMING: after applying q_j K_j, reconstruct the same q_j from the original S and determinant to uncompute and physically release the field register; regenerate q_j only when reversing the operation.

All ORIGINAL syndrome input registers are restored, all temporary K, inverse and quotient scratch is cleaned, and a small nontrivial locator-dependent CZ phase is produced and checked. This is a genuine source-equation locator circuit, not only an identity-only mock operation.

## First failed construction and correction (retained chronology)

Original CI run 44945131383 failed native compilation in both field widths: the Hankel matrix reuses the same original source syndrome word in distinct rows/columns. Some determinant products therefore applied a two-input multiplication to the same quantum register, creating an illegal duplicate CCX control (e.g. q12,q12).

The correction is mathematically forced: GF(2^d) squaring is the linear Frobenius map. When both determinant operands name the SAME original source occurrence, compile its square as original-source bitwise CNOTs:

    (sum_i a_i 2^i)^2 = sum_i a_i (2^i)^2.

Distinct-source field products retain the native multiplication. This fixes a collision without faking two independently prepared source words or copying a syndrome.

The corrected workflows compiled and passed all native basis, phase, source-cleanup and exact source-equation checks.

## Native Q/T measurements and scope

**Corrected GitHub Actions CI PASS:**
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44945215726

| Field | Rounds | Control history Q | Streaming Q | Q saved | Control static T | Streaming static T | Extra T | Samples per mode |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GF(2^4) | 2 | 57 | 53 | **4** | 200 | 252 | +52 | 128 |
| GF(2^4) | 3 | 77 | 69 | **8** | 1,058 | 1,136 | +78 | 128 |
| GF(2^4) | 4 | 97 | 85 | **12** | 11,274 | 11,378 | +104 | 128 |
| GF(2^12) | 2 | 205 | 193 | **12** | 1,365 | 1,665 | +300 | 128 |
| GF(2^12) | 3 | 265 | 241 | **24** | 7,179 | 7,629 | +450 | 128 |

Original input Q grows with the number of original syndrome equations (2t source field words); there is ZERO persistent round-indexed K polynomial history on either side. The history control retains t quotient field words; streaming retains none between rounds and pays extra arithmetic for regeneration. Observed physical Q savings increase exactly as (t−1)*field_degree for the measured rounds. This empirical trend is not a proof of the same scaling outside the tested circuit family.

Every row passed its 128 independent syndrome-source basis tests with **zero source changes, zero dirty-workspace cases, zero phase disagreements and zero original-source equation failures** in every nonsingular trial.

The singular output is unresolved; this is NOT a variable-degree locator decoder. In the 128 arbitrary source cases per GF12 mode, 64 were nonsingular and 64 were deliberately singular. GF4 r2/r3 each had 63 nonsingular, r4 62.

## Cross-check against the benchmark source

The first-party DQI test sampler was used only to produce syndrome examples; no official DQI circuit source was copied.

- At n=4, t=2, GF(2^12), 96 source samples: **24 nonsingular cases**, all 24 exact coefficient matches to an independent BM recurrence; remaining 72 singular/unresolved.
- At n=6, t=3, GF(2^12), 96 source samples: **15 nonsingular cases**, all 15 exact coefficient matches to independent BM; remaining 81 singular/unresolved.
- No full benchmark phase oracle, Chien/Forney stage, arbitrary-degree decoding or Kaggle submission is claimed for this component-level experiment.

## Next actual locator obligation

The primary missing branch is rank adaptation. In real DQI test data, a syndrome produced by fewer than t error locations legitimately has a shorter locator. A singular t×t Hankel matrix cannot be interpreted as "no error."

Derive a reversible coherent degree selector: for each d=0..t, construct a candidate from source Hankel constraints, verify ALL supplied syndrome recurrences for that d, select the smallest witnessed-valid d, and uncompute each candidate and all selection scratch. This must work for all valid up-to-t error source distributions, not merely the nonsingular full-rank chart.

For t=35 (n=70), factorial-size direct determinant expansion is not computationally practical; before a serious full-DQI replacement, the source-column producer must be replaced by an efficient, source-preserving quotient/remainder elimination network or checkpointed constructive recursion. The measured low-t Q/T savings are a proof of carrier reuse, not evidence that the current determinant implementation beats the full 1,860-Q Experiment 023 baseline.

**Verification boundary:** The present native experiments solve and uncompute up to four genuine finite-field syndrome constraints, with no retained K history and a measured 12/24-Q space saving in GF12 small locators. No new full Reed–Solomon decoder or Kaggle score has been produced.


## Later evidence A — coherent rank-adaptive locator, including singular lower-degree sources

**Native CI PASS (2026-11-21):**
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44945454180

An earlier all-or-nothing degree-t Hankel chart left shorter valid locator sources unresolved. In a separate independent circuit, every candidate degree d=0..3 is generated **from original S only**, checked against all available recurrence equations, and selected only if it is the *smallest witnessed-valid* degree. A degree-0 locator is authorized if and only if all original syndrome words are zero; singular degree-3 alone is not interpreted as zero error. No K polynomial, candidate locator or quotient history is retained after selection.

The circuit has two coherent versions: a quantum-output probe and a phase-only version which uses the locator then exactly uncomputes it.

| Field | Original sample cases | Probe Q/T | Exact phase+reverse Q/T | Source/phase/workspace errors |
|---|---:|---:|---:|---:|
| GF(2^4), 64 arbitrary | 64 | 88 / 8,287 | 88 / 10,168 | **0** |
| GF(2^12), 64 arbitrary + 128 valid first-party | 192 | 284 / 55,489 | 284 / 68,568 | **0** |

At GF(2^12), every one of the **128 valid-error first-party source samples** was resolved, and every source locator agreed with our independent original Berlekamp–Massey recurrence. The 64 additional arbitrary-source samples included 8 truly unresolved degree-0..3 cases, which remain explicitly flagged as unresolved. Across all 192 samples the witnessed degree distribution was {0:16, 1:38, 2:56, 3:74, unresolved:8}. This is a source and quantum-locator result, not yet a complete DQI decoder.

## Later evidence B — complete small DQI quantum phase (first-party verifier PASS)

**GitHub Actions native supplied DQI verifier PASS (2026-11-21):**
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44945612261

Our **independent** source-only rank-adaptive locator was connected to an original-source evaluator Ω, codeword-position root tests, derivative, and Forney phase transfer. On the original GF(2^12) n=6,m=15 benchmark, source inputs and classical error masks had exactly the names and widths the first-party DQI verifier requires. It ran **512 first-party DQI shots at log2_delta = −16**, and produced:

| Verifier result | Experiment 026 complete small decoder |
|---|---:|
| Status | **PASS** |
| Q | **284** |
| Static Toffoli-like | **87,633** |
| Mean Toffoli-like | **87,633.0** |
| Native operations | **965,066** |
| Reaction depth | 317 |
| Verified shots | 512 |
| Value errors | **0** |
| Phase errors | **0** |
| Local development score | 21,096,773,742.425747 |
| Circuit SHA-256 | 7bab9a078230a88dc4a2e8d55af0f61a98e97f5a70dcc64d8e7fde81d7d1c9f8 |

The independently checked Experiment 023 n6/m15 small control was Q306, static Toffoli-like 111,353 and 1,145,593 native operations, also with zero errors on its 512-shot small phase screen. **At these same dimensions**, the new source-only complete decoder uses 22 fewer Q, 23,720 fewer static T and 180,527 fewer native operations. The static Q-squared-T resource cost is approximately **32.2109% lower**. This is a *small fixture comparison*, not a public Kaggle score or a full n70/m4095 advantage.

The full small source program does not retain a polynomial K_j history or a field quotient tape. It produces rank-adaptive locator coefficients, uses them to compute Ω(z)/Λ'(z) at witnessed roots z=α^(−position), kicks back parity under the supplied classical error mask, and exactly uncomputes all source-derived work. The incomplete or singular denominator branch is gated off rather than supplying a fictitious field inverse.

### Scope and remaining engineering gap

**Demonstrated**: a native, coherent, variable-degree, complete DQI decoder on the six-syndrome, fifteen-position GF(2^12) problem; actual measured Q/T/ops reduction relative to the independently tested Experiment 023 small reference; first-party 512-shot phase verification with zero phase/value errors; no K/F history tape.

**Not demonstrated**: a replacement for the complete 70-syndrome / 4,095-position benchmark, its 102,400-shot −128-confidence verifier, or any Kaggle score for this experiment. The determinant/candidate enumeration in the current native construction is practical only at these small degrees. In particular, directly expanding a degree-35 Hankel determinant using all permutations is computationally infeasible. The next source-preserving construction must implement Hankel/subresultant elimination with *polynomial* instruction complexity, while retaining the identity and lifetime proof that generated and uncomputed K_j can be recovered from the original S without a growing checkpoint tape. Avoid reintroducing 35 full polynomial checkpoint registers under a different name.

**Machine ledger:** research/experiment_026_native_results.json.


## Later evidence C — independent 8,192-shot DQI holdout

**2026-11-21; first-party 8,192-shot native verifier PASS:**
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44945868608

The same complete independent small n6/m15/GF(2^12) source-only decoder was tested on a separate seed (20261122) and a stricter confidence setting log2_delta=−32, with **8,192 verified shots, zero value errors and zero phase errors**. Its circuit SHA-256 remained exactly

    7bab9a078230a88dc4a2e8d55af0f61a98e97f5a70dcc64d8e7fde81d7d1c9f8

with Q284, static/mean Toffoli-like 87,633, 965,066 native operations and reaction depth 317. The local verifier score was 9,717,213,330.2116 at this new confidence setting. This confidence-dependent score is **not** a Kaggle three-task score and should not be compared to the earlier 512-shot development score without preserving the different confidence specification.

The independently observed zero-error holdout improves the empirical evidence, but does not close the remaining algorithmic scaling barrier. The degree-35 determinant source generator currently requires a different polynomial-time method; no full-size DQI decoder or leaderboard result is claimed.
