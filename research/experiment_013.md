# Experiment 013 — identify the first actual full-width source-live peak

**Date:** 2026-11-20  
**Status:** code and small-decoder falsification controls passed; full n=70,
m=70, GF(2^12) event replay pending on the user's already generated WSL
source allocation receipt.

## Evidence prompting this experiment

The user's source-only decoder at 70 syndrome registers (degree 12)
and 70 classical mask positions compiles to Q=1893, identical to the
full reference Q at 4095 positions. The 70-position decoder has:

- 840 persistent named syndrome qubits;
- 963 persistent source-root workspace qubits;
- a maximum of 1893 simultaneously tracked source qubits;
- 90 additional peak-workspace qubits beyond the 1803 persistent slots;
- 90 physical slots with observed multiple allocation generations;
- 41,602 temporary allocation occurrences and 68,290 event records.

Static benchmark difference is exactly:

    T_full - T_short = 5725461 - 4312686
                     = 1412775 = (4095 - 70) * 351.

Thus the measured 351-Toffoli position-cost law applies exactly to the
full 4095-position reference static circuit, and additional positions
do not increase Q.

This does not prove a specific 90-slot omission is lawful. It identifies
the correct *causal resource pool* to inspect.

## Method

scripts/audit_dqi_peak_overlap.py independently replays every
allocation and release from the user WSL experiment 011 receipt.
It checks that each physical qubit slot has at most one currently
live source occurrence and that the retained number of live sources
agrees after each event. At the first maximum, it retains exact
birth-stage, birth-event-index and occurrence identity for each
currently allocated source.

The output distinguishes:
- the first source event that reaches the maximum;
- the earliest and latest events at that maximum;
- all observed peak-producing source stages;
- root and named persistent source occurrences;
- temporary workspace occurrences, grouped by producing source stage;
- the gap, if any, between source-visible live maximum and compiled
  qubit count Q (native C++ scratch may not be fully visible).

No assignment of absent native births is invented. A live source
occurrence is not itself evidence that its qubit must hold an independent
quantum state throughout the entire allocation lifetime.

The original scoring factor remains an indexed account:

    Q^2 = sum_(i=1)^Q (2*i-1).

This source audit does not change Q, T or the official DQI confidence
factor. A genuine Q reduction requires a recompiled original function,
clean scratch, and successful phase validation.

## Independently executed control

GitHub CI run 44836149005 passed four falsification tests plus the
existing six allocation/square-ledger tests. For the original
controlled n=6, m=15, degree=6 decoder, the first observed source-live
maximum is 177, below compiled Q=180. It occurs in the
forward_eea / eea_step / multiply_and_add_or_sub / quotient_div stage.
The audit does not falsely claim that the invisible three native
slots are absent from the physical circuit.

This peak-stage observation has **not** yet been established for the
benchmark-width 70-syndrome source. Run the source replay on its exact
saved ledger instead of generalizing from the small fixture.

## WSL reproduction, without recompiling the 39M-op circuit

~~~bash
git -c http.version=HTTP/1.1 -c http.proxy= -c https.proxy= fetch origin
git merge --ff-only origin/research/vqcc-frontier-001

python3 scripts/audit_dqi_peak_overlap.py \
  /tmp/vqcc_dqi011_n70_m70.json \
  --report /tmp/vqcc_dqi013_peak_n70_m70.json
~~~

The report's first_peak_other_source_occurrences retain the original
90 or other observed temporary source identities; no additional
source circuit build is required.

Next action after the benchmark-width result: compare the peak source
lifetimes against the actual quotient/division producer and test
whether the original forward and reverse operand obligations admit a
reversible in-place rewrite or alternate scratch reuse. Establish
cost and full equivalence rather than deleting an allocated qubit
merely because its slot is assigned to a temporary register.
