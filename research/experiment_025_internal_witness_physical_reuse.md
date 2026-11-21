# Experiment 025 — internally constructed witnesses and native physical qubit reuse

**2026-11-21. Status: native GF(2^4) and GF(2^12) tests PASS.** All circuits derive independently from our Experiment 024 finite-field two-shear source law. No public competitor circuit, gate stream or source table was copied. Existing Experiment 023 DQI baseline and Kaggle ZIP are unchanged.

## The causal-source difference from Experiment 024

The older Experiment 024 recovery needed a promised relationship between initial polynomial C and syndrome S. Experiment 025 **constructs** that relationship inside a native reversible quantum circuit. The only original, named quantum inputs are five GF(2^d) syndrome words S[0:5] and two four-coefficient source polynomials K[0:2][0:4]. All C, B, F, inverse and control registers are initially empty.

- Construct C_initial[i] = S[i] for i=0,1,2,3 using native reversible XOR.
- Construct quantum denominator B[j] = D_j(K[j],S) using the original source discrepancy D_j(X,S) = XOR_i X[i] * S[j+3-i].
- Preserve every original input S and K throughout.

If B1 is nonzero then at least one original coefficient K1[i] must be nonzero: otherwise D_0(K1,S) would be zero. This witness is a consequence of the program's construction, not an external promise.

After two quantum-valued reversible source steps, the preserved original-source relationship is

    R[i] = S[i] XOR C_after_two_steps[i] XOR z2*F2*K2[i]
         = z1*F1*K1[i],

with z_j witnessing that B_j is nonzero. On the absent denominator B1=0, F1 remains its original empty state; no field inverse at zero is asserted. On B1 nonzero, the circuit deterministically selects the smallest **original coefficient occurrence index** i with K1[i] nonzero and determines F1 = R[i] / K1[i]. Exclusive quantum source controls ensure exactly one chosen coefficient. Inverting its native field-slope construction leaves all source controls and scratch empty and toggles F1 to zero.

This handles a zero preferred slope without inventing an unavailable inverse. Only the chosen original nonzero coefficient is used to transfer the quotient consequence.

## Actual physical release, reallocation, and exact reverse

Two matched circuits execute the exact same gate stream:
1. Prepare C and B from original quantum S,K. Perform two reversible source steps.
2. Recover F1 using all four original-source coefficients, leaving it empty.
3. In the release arm, call native builder.free(F1). In the retain arm, keep the now-empty F1 allocated.
4. Both allocate twelve new source-derived GF field-product words simultaneously, compute and clean them, and release them. This is a deliberate source-liveness **stress fixture**, not a claimed full DQI algorithm.
5. The release arm allocates a fresh field carrier. Both arms reconstruct the former F1 from the same untouched original witnesses, reverse step 2 and step 1, and uncompute their denominators and C to empty.

The released field carrier's physical Q slots are later reused by the first new field word, as independently logged by the native allocator. The original and reconstructed F1 share physical IDs but are distinct source occurrences; they are not silently equated.

## Strengthened native CI (PASS)

https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44937838399

| Field and arm | Native peak Q | Static Toffoli-like | Native operations | Identical test cases | Phase/source/scratch errors |
|---|---:|---:|---:|---:|---:|
| GF(2^4), retain F1 | 132 | 1,676 | 16,855 | 2,048 | **0** |
| GF(2^4), release F1 | **128** | 1,676 | 16,855 | 2,048 | **0** |
| GF(2^12), retain F1 | 396 | 12,304 | 149,627 | 1,024 | **0** |
| GF(2^12), release F1 | **384** | 12,304 | 149,627 | 1,024 | **0** |

At GF(2^12), this is a measured **12-Q smaller compiled physical peak, with zero added static Toffoli-like gates or native operations**, relative to an otherwise identical retained-carrier two-step circuit. The original named inputs total 156 Q in both cases; no extra witness input register is allocated.

Each native test family includes: first K all zero; first denominator absent; **one nonzero K1 coefficient at each of indices 0,1,2,3** with a witnessed nonzero denominator; K1 nonzero but first discrepancy absent; first denominator nonzero but second denominator absent; and independently generated quantum source polynomials. The strengthened GF(2^12) test used 128 cases per eight branch families and GF(2^4) used 256 per family.

The GF(2^12) logged initial F1 slots are physical 228 through 239. The released arm's first new field word occupies **the same physical set in reverse order**, 239 down through 228. Later the reconstructed F1 takes 228 through 239 again. The no-release arm's future word necessarily occupies different slots. All source registers match their inputs after full reversal; all non-input work is empty; no phase changes were observed.

## Proof and verification limits

The mathematical source relation establishes the conditional recovery formula for every original S,K basis state reachable from this internal construction. The native tests independently probe execution and cleanup but do not exhaustively simulate all original-source superpositions.

This demonstrates **actual allocator lifetime and physical peak reduction in a reversible two-step research fixture**, not yet lower Q for the existing full DQI decoder. Whether an entire multi-round locator construction can adopt this law without retaining additional K histories or growing a checkpoint tape is unresolved. The user-authored Experiment 023 DQI remains verified at **1,860 Q**, and no Experiment 025 full DQI KMB or Kaggle submission exists.

**Next:** translate these source-relation initialization and release operations into an actual reversible locator/evaluator recurrence, audit the native simultaneous K-history state, then compare global Q/T and source/phase correctness against Experiment 023. Only a complete new decoder would merit the official 102,400-shot -128 verification.

**Source and evidence:** research/dqi025_internal_witness_reuse.py, scripts/bench_dqi025_internal_witness.py, .github/workflows/dqi025_internal_reuse.yml, and native CI linked above. Three-page formal LaTeX/PDF compiled and available in the conversation as Experiment025_Internal_Witness_Reuse.tex / .pdf, with PDF SHA256 87d809fdf9e1f3754942aba8cfa4e9adf021124f9cbee667af5ee2aafa20161f and TeX SHA256 25f1c8e79cb02c3776e7e18f1e250291da92f3d63e8628cdf3851b9e721f1b69.
