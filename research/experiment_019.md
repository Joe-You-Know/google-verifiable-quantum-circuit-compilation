# Experiment 019 — complete controlled six-bit norm-inverse quotient

**Date:** 2026-11-20 (CI completed 2026-11-21 UTC).  
**Status:** Native Kickmix standalone compilation and independent basis simulation PASS.  
**The synchronized EEA is unchanged.**

## Continuity

Experiment 013 localized the first benchmark-width full DQI live peak to
`forward_eea/eea_step/multiply_and_add_or_sub/quotient_div`, with 72 qubits
held by the original quotient-plus-scaffold witness.
Experiment 015 proved the direct quotient XOR was cheaper but missed
the required quantum control. Experiments 017 and 018 established the exact
GF(2^12)/GF(2^6) norm decomposition and a reversible norm producer.
Experiment 019 now constructs and checks the **complete controlled quotient**,
including the six-bit inverse and scratch uncomputation.

## Native experiment

GitHub Actions run:
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44843260760

Compiled circuit artifact:
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44843260760/artifacts/14681388928

The candidate replays an authenticated, losslessly compressed 81-wire
X/CX/CCX gate sequence. Its decoded SHA-256 is
`b8e52afde6080e93f674ca2ca8bbdc98abf614799ea803c1c8e6e61e9f89466c`.
Both circuits use the same Kickmix field definition, builder and
`operation_statistics().num_toffoli_like` counter, with the original
held-scaffold gadget reconstructed directly from its reference source.

| Native metric | Original held quotient | Six-bit norm-inverse quotient | Difference |
|---|---:|---:|---:|
| Qubits | 109 | **81** | **-28** |
| Toffoli-like gates | 390 | **270** | **-120** |
| Circuit operations | 6,252 | **3,708** | **-2,544** |
| Workspace beyond 12+12+12+1 I/O | 72 | **44** | **-28** |

Both independent Kickmix simulations passed **9,223/9,223** identical input
cases, including every one of 4,096 denominators (numerator one and quantum
control one), every one of 4,096 numerators (denominator one, both control
values across the sweep), 1,024 randomized tuples and explicit edge cases.

The verified map is

```
|A>|B>|T>|control>|0-work> ->
|A>|B>|T XOR (control AND quotient_GF4096(A,B))>|control>|0-work>
```

The denominator-zero quotient is explicitly zero, matching Kickmix. Both
simulators confirmed intact numerator, denominator, control, exact target XOR,
and zero work-register residue on every case. Earlier source-level arithmetic
testing also checked all 16,777,216 numerator/denominator pairs.

## Verification tiers and unresolved requirements

**Demonstrated:** a smaller native standalone quotient gadget with exact
classical reversible operation and matching controlled simulator tests;
Toffoli-like and qubit counts are now measured by the same Kickmix counter.

**Not demonstrated:** a reduction from 1,893 qubits in the *full* n=70
decoder; any reduction in full-DQI static Toffoli count; official sampled
phase-oracle verification; Kaggle score improvement. A local reduction of
28 qubits cannot be subtracted from the full circuit without recompilation
because workspace liveness and overlap are context-dependent.

**Next experiment:** integrate the candidate in a feature-flagged
`quotient_div` implementation (while retaining the reference path), compile
both n=70,m=70 GF(2^12) decoders, replay peak allocation, verify cleanup and
compare the overall 70-position and 4095-position costs. Run the official DQI
phase verifier before considering competition submission.

The source and CI remain in the draft Experiment 019 pull request.
