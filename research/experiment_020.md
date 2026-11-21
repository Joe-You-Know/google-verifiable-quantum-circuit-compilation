# Experiment 020 — controlled six-bit norm quotient inside synchronized EEA

**Research date:** 2026-11-20 (CI completed 2026-11-21 UTC).  
**Status:** smaller DQI circuit sampled phase audit PASS; both 70×70 and 70×4095 native static resource audits PASS. Full 4095-position DQI **phase verifier NOT RUN**.

## Constructive source continuity

Experiment 019 compiled a complete **controlled** quotient gadget on the native
Kickmix backend: 81 qubits/270 Toffoli-like gates, rather than the native
held-scaffold ratio's 109 qubits/390 Toffoli-like gates, with 9,223 identical
simulator basis cases passing on each gadget. The prior experiments' zero divisor
and quantum control obligations are preserved.

Experiment 020 introduces an **experimental source copy only**,
`research/dqi020_experimental_decoder.py`. It changes the single local source
producer `accumulate_quotient` inside `_multiply_and_add_or_sub` by a
`quotient_mode` switch. The `reference` path uses the original
`init_gf2_div_with_scaffold`, controlled `gf2_iadd` and inverse scaffold
cleanup. The `norm_inverse` path replays the exact authenticated Experiment
019 reversible gate word, with the original source numerator, denominator,
accumulator, quantum control and 44 fresh work qubits. This affects both forward
and reverse EEA through the same source method. It does not alter the registered
quantum syndrome registers or the MBUC phase code.

The public reference file
`verifiers/dqi/dqi_reference_circuit.py` is **unchanged**. The exact disabled
mode was independently compiled and checked to have the same serialized
KMB SHA-256 as the public reference in the small DQI fixture.

## Smaller sampled DQI check, GF(2^12), n=6, m=15

Native resource and DQI phase verifier run:
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44844213654

| Measurement | Original | Norm-inverse EEA | Difference |
|---|---:|---:|---:|
| Physical Q | 339 | 322 | -17 |
| Static Toffoli-like T | 127,921 | 113,521 | -14,400 |
| Total circuit ops | 1,462,907 | 1,157,507 | -305,400 |
| Sampled shots | 512 | 512 | common draws |
| Value errors | 0 | 0 | 0 |
| Phase errors | 0 | 0 | 0 |
| Verification status | PASS | PASS | — |

The test called the actual supplied DQI verifier API with the **same sampled
input arrays for both circuits**, a common seed, and development confidence
`log2_delta=-16`, not the competition's `-128`. Both restored syndromes and
cleaned all ancillary qubits, and both returned correct MBUC phases on all
sampled shots. This tests the **integrated** update, beyond the standalone
local gadget.

## Full-width native static compilation, GF(2^12), n=70, m=70

GitHub CI PASS:
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44844213620

| Native static measurement | Original | Norm-inverse EEA | Difference |
|---|---:|---:|---:|
| Physical Q | 1,893 | **1,876** | **-17** |
| Static Toffoli-like T | 4,312,686 | **4,206,126** | **-106,560** |
| Circuit ops | 39,245,008 | **36,985,048** | **-2,259,960** |

The full-width job compiled and counted each circuit **independently** in
the same native Kickmix runtime, then recorded a source-preserving receipt.
It did not simulate the full-width circuit. The integrated gain is **17**
physical qubits, not 28: the parent EEA state and other source work overlap
the quotient producer and constrain maximum liveness.

These results independently reproduce the original 1,893-qubit n=70,m=70
reference as a control; the new 1,876 measurement is therefore an observed,
native-compiled full-width change, not a subtraction inferred from the
standalone 81-qubit gadget.

## Boundaries

1. The full `m=4095` compiled candidate **has now been measured** in the same native Kickmix comparison. See the dated addendum below; this earlier unmeasured boundary was closed.
2. The official 70-syndrome 4095-position sampled phase verifier with
   `log2_delta=-128` has **not run** on this candidate.
3. The official DQI score uses mean per-shot Toffoli-like operation count and
   confidence overhead, not static T alone. No competition score or
   submission eligibility is claimed from this 70×70 static result.
4. Source payloads and gate history are retained in the draft PR;
   the unmodified reference implementation remains independently runnable.

## Reproduce the n=70, m=70 static audit on Tower

~~~bash
git -c http.version=HTTP/1.1 -c http.proxy= -c https.proxy= fetch origin
git worktree add --detach /tmp/vqcc020-integrated \
  origin/research/vqcc-020-featureflag-integrated-norm
cd /tmp/vqcc020-integrated
PYTHONPATH="$PWD/kickmix:$PWD/verifiers:$PWD:$PWD/scripts" \
python3 scripts/bench_dqi020_integrated_norm.py \
  --n 70 --m 70 --degree 12 --compile-only --resource-only \
  --outdir /tmp/vqcc_dqi020_fullwidth
~~~

The next research obligation is the **official full 4095-position phase verifier**, including measured mean Toffoli and error receipts at the stipulated confidence. The full static build now passes (addendum below).

## Addendum — 4095-position competition-width static Kickmix compilation

**New evidence, 2026-11-20 / 2026-11-21 UTC:**  
https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44844416271

After the first 70×70 report, the exact **n=70, m=4095, GF(2^12)**
competition-dimension source was compiled independently for the original and
the feature-flagged norm-inverse version, with native Kickmix
`operation_statistics` on both. The separate compilation conclusively resolves
the previously pending **static full-width** measurement:

| Native static measurement | Original reference | Norm-inverse EEA | Difference |
|---|---:|---:|---:|
| Physical Q | 1,893 | **1,876** | **-17** |
| Static Toffoli-like T | 5,725,461 | **5,618,901** | **-106,560** |
| Circuit ops | 86,051,014 | **83,791,054** | **-2,259,960** |

Unlike the earlier 70×70 test, this is not an extrapolation: both 4095-position
circuits were built and counted by Kickmix itself. The additional 4025 positions
contribute the same 1,412,775 static Toffoli-like gates in both variants.
The candidate still improves the EEA by precisely 106,560 static gates.

**Still not established:** official 4095-position phase correctness across the
required 102,400 shots, confidence parameter `log2_delta=-128`, candidate
per-shot Toffoli mean and scored DQI confidence factor. No official Kaggle
submission has been made; all integration exists only on the experiment branch.
