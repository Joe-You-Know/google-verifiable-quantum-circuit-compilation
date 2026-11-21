# Experiment 022 — witnessed source liveness and independent inverse-phase nonconstruction

**Research date:** 2026-11-21.  
**Source basis:** Only our verified Experiment 020 decoder, its native Kickmix runtime and our earlier original source-identity ledger. No public competitor gate stream, decoder source or chemistry table is incorporated.

**Status:** serial phase gadget and smaller DQI native phase checks PASS; full n=70,m=70 and n=70,m=4095 native static compiler and occurrence audit PASS for combined source; full 4095-position 102400-shot official-confidence verification remains NOT RUN. A separate full-dimension reduced-shot development sample is independently tracked.

## 1. Reopen the actual source construction

At n=70, field degree=12, the Experiment 020 decoder allocates, before stage-specific temporary work:

| Retained source identity | Qubits |
|---|---:|
| 70 named syndrome registers | 840 |
| Three additional reg_a field elements | 36 |
| 73 reg_b field elements | 876 |
| Five 8-bit degree and position metadata counters | 40 |
| Flag, two-bit counter, and 8-bit halting counter | 11 |
| **Retained total** | **1,803** |

The original full-size source-occurrence replay (native Q=1876) established that **the first peak is in chien_forney_mbuc / forney_step**, not in quotient_div:

    1803 persistent + 25 Forney stage + 48 native inverse chain = 1876.

The 25 Forney stage qubits have distinct source obligations: a 12-qubit sigma_prime_inv, a 12-qubit conditional product vector located, and one quantum is_sigma_zero flag. The 48-qubit inverse chain retains the native finite-field inverse's reversible witnesses. Source-visible peak equals compiled Q at this point, so no unknown physical-birth gap is assigned to this original peak.

**Necessity boundary:** These are allocations required by the *current implementation*, not a theorem proving 1,803 or 48 qubits is the minimum possible reversible decoder. Do not silently treat a source lifetime as an information-theoretic lower bound.

## 2. Falsified first alternative: a redundant long-lived EEA conjunction

The synchronized EEA constructs is_c3 = counter[0] AND counter[1] and retains it throughout its step. The one-hot controls depend on a separate halting gate h and two counter bits a,b:

    c0 = h AND NOT a AND NOT b
    c1 = h AND a AND NOT b
    c2 = h AND NOT a AND b
    c3 = h AND a AND b

All four can instead be constructed from the three retained sources (h,a,b), without retaining the independent a AND b qubit during the step:

    c1_pre = h AND a
    c2_pre = h AND b
    c3 = c1_pre AND b
    c1 = c1_pre XOR c3
    c2 = c2_pre XOR c3
    c0 = h XOR c1 XOR c2 XOR c3

Reversing the operations cleans all four temporary controls. The halting-counter operation still constructs and uncomputes a AND b only locally. All eight Boolean input combinations and the n6/m15 Kickmix DQI phase test passed. But **alone it is NOT a scored improvement**: at full n70,m70, Q=1876 and static T=4,206,126 are unchanged, with 1,776 more other operations. The Forney-stage peak was unaffected.

Native CI: https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44928355002

## 3. Independent successful alternative: single-bit Forney phase carrier

For the Forney phase, the original source first constructs all 12 bits

    located_i = z AND omega_i,

where z is the quantum sigma-zero flag, omega is the source evaluator field element, and v is the reversibly constructed sigma-prime inverse. It then kicks back a phase whose parity is the selected bits of the field product located times v.

Let B_ijk be the k-th bit of the *already specified native field multiplication* of elementary field representatives 2^i and 2^j. Let M_k denote the existing classical mask bit for the current codeword position. The original phase parity can be expanded exactly, over GF(2), as

    phase = XOR_{i,j,k} (z AND omega_i) AND v_j AND M_k AND B_ijk.

Rather than allocate 12 simultaneous located bits, retain only one reusable carrier c:

1. For each original source index i, construct c = z AND omega_i, leaving z and omega unchanged.
2. For each mask bit k, execute CZ(c,v_j) for every j with B_ijk=1, conditioned on classical M_k.
3. Reverse the original c construction so c returns to its initial empty state, then proceed to the next i.

The same phase follows by field-product bilinearity and the fact that commuting diagonal phase operations combine by XOR of phase parity. It does not build a fictitious inverse or omit the zero case. This is an independently derived operation schedule; the original finite-field inverse with its 48-qubit witness chain is left unchanged.

Actual native standalone tests:

| Field | Cases | Original Q/T | Serial Q/T | Outcome |
|---|---:|---:|---:|---|
| GF(2^4) | 8,192 exhaustive basis states | 13 / 4 | 10 / 4 | PASS, correct phase, intact inputs, clean scratch |
| GF(2^12) | 2,055 deterministic/random basis states | 37 / 12 | 26 / 12 | PASS, correct phase, intact inputs, clean scratch |

The supplied n6,m15 DQI phase verifier ran both variants on identical 512 shots at development confidence -16. Both had zero value errors and zero phase errors; 020 Q=322, serial Q=311; static T=113,521 in both.

Native CI: https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44928545075

## 4. Source-controlled combined construction and full-width compiler evidence

The isolated serial Forney variant passes native compilation at n70,m4095 with **Q=1866**, not the 1865 source-live maximum; the EEA quotient stage becomes the first source-visible peak (1803+6+12+44=1865) and the compiled circuit still requires one additional physical slot beyond that visible maximum.

Combining the separately audited sparse EEA control with serial Forney removes this final competing peak. Native measurements:

| n=70,m=4095 (degree 12) | Verified 020 | Serial Forney | Combined 022c |
|---|---:|---:|---:|
| Physical Q | 1,876 | 1,866 | **1,865** |
| Static Toffoli-like T | 5,618,901 | 5,618,901 | **5,618,901** |
| Native circuit operations | 83,791,054 | 85,388,104 | **85,389,880** |

The combined circuit has a first native source-visible peak of **1,865**, exactly equal to compiled physical Q:

    1803 persistent + (12 sigma_prime_inv + 1 carrier + 1 zero flag)
       + 48 inverse chain = 1865.

The same native n70,m70 audit passed with Q 1876→1865 and static T 4,206,126→4,206,126. This is measured native resource reduction, not inferred from an isolated gadget count. The small combined n6/m15 DQI phase verifier also passed 512 common shots with zero errors.

Combined native CI: https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44928808020

Total extra non-Toffoli instructions are 1,598,826 at n70,m4095 (approximately 1.91% more instructions). Scored T does not increase in these native static counts. If eventual full-confidence mean T and repetition overhead remain as before, the isolated Q-squared cost factor would improve by approximately **1.1831%** (cost ratio 1.011831), but this is a model projection, **not** a verified Kaggle leaderboard result.

## 5. Obligations and next test

- The baseline Experiment 020 already has a user-reproduced full 102,400-shot official local DQI PASS and an actual Kaggle COMPLETE public score of 1.03006.
- The Experiment 022 source copies have passed 8,192 exhaustive GF4 and 2,055 GF12 phase gadget cases and the smaller 512-shot integrated DQI phase tests.
- Experiment 022b's 1,866-Q standalone serial-full decoder passed the actual n70,m4095 **512-shot** development-confidence DQI verifier, zero errors; native compile/run: https://github.com/Joe-You-Know/google-verifiable-quantum-circuit-compilation/actions/runs/44928699070.
- The full n70,m4095 **102,400-shot official-confidence test for 022c remains an open obligation** before any competition submission. Even a zero-error 512-shot development sample must not be confused with it.
- The native Forney inverse's 48-qubit scaffold remains another candidate for independent arithmetic derivation, but deleting it without equivalent reversible cleanup is unsound.

## WSL reproduction without modifying the accepted Experiment 020 ZIP

~~~bash
git -c http.version=HTTP/1.1 -c http.proxy= -c https.proxy= fetch origin
git worktree add --detach /tmp/vqcc022-source \
  origin/research/vqcc-022-causal-liveness
cd /tmp/vqcc022-source
export PYTHONPATH="$PWD/kickmix:$PWD/verifiers:$PWD/scripts:$PWD"

python3 - <<'PY'
from research.dqi022_serial_forney import build_sparse_serial_forney_circuit
c = build_sparse_serial_forney_circuit(m=4095,n=70,degree=12)
print("Q",c.num_qubits)
print("T_static",c.operation_statistics().num_toffoli_like)
c.to_file("/tmp/vqcc_dqi022_combined.kmb",format="kmb")
PY

python3 verifiers/dqi/verify_submission_dqi.py \
  /tmp/vqcc_dqi022_combined.kmb \
  --m 4095 --n 70 --degree 12 \
  --num-shots 102400 --batch-size 256 \
  --log2-delta -128 --max-workers 1
~~~

The new KMB is not a Kaggle submission until this full verification passes, the original Invsqrt and chemistry source artifacts are retained, and a new submission.zip is deliberately constructed with a separate name and audit fingerprint.
