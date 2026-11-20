# Experiment 004 — chemical angle-word quotient/remainder precision

**Date:** 2026-11-20  
**Current status:** Five rounding-law tests PASS on GitHub Actions and structural
128-qubit-cap checks PASS for the four configurations listed below. The
physical reconstruction accuracy and full Kickmix oracle functionality are
**not yet tested** for the reduced-width candidates.

## Source and mechanism

Reference implementation:
- verifiers/dfthcsos/example_submission/angle_k_reference_circuit.py
- verifiers/dfthcsos/verify.py
- verifiers/dfthcsos/SCORING_README.md
- sample_submission/dfthcsos/submission.npz

The original source has 12-bit angle words and 75 angles per source row,
stored across 10 circuits, 8 words each. Each circuit loads a source-relative
XOR delta between consecutive 8-word batches. For this benchmark the 3976
source rows require a 12-qubit selection register plus 11 temporary
segment-tree qubits. The word registers add J*brot qubits. Thus a
reference-style ANGLE oracle uses 23 + J*brot qubits.

With a 128-qubit hard ANGLE circuit limit, the maximum batch size at each
tested precision is:

| bits | J | number of circuits | oracle qubits |
|---|---:|---:|---:|
| 12 | 8 | 10 | 119 |
| 11 | 9 | 9 | 122 |
| 10 | 10 | 8 | 123 |
| 9 | 11 | 7 | 122 |

These are structural counts, not guarantees that numerical factorization
accuracy will survive quantization.

For a source integer angle word w, to move from source precision b0 to b,
write the Euclidean quotient and remainder

    w = q*(2**(b0-b)) + r, with 0 <= r < 2**(b0-b).

An explicit rounding policy chooses q or q+1; the final word is its
Euclidean remainder against 2**b. Nearest-even ties and downward rounding
are independently tested. Note that the physical angle is periodic:
theta = pi*w / 2**(b-1). Reducing width may change the recovered vectors,
lambda_eff, and the two strict 20mHa reconstruction constraints.

## Reproduction in local WSL

The FCIDUMP required by the original verifier was gitignored because it
is a very large original competition data file. Consequently GitHub CI
can test the exact source-to-word conversion and qubit cap but cannot
independently evaluate chemistry acceptance from its bare checkout.

The user's local WSL repository already retains the FCIDUMP, so from
the repo root after a normal fetch and fast-forward:

~~~bash
source ~/vqcc-venv/bin/activate
export PYTHONPATH="$PWD/kickmix:$PWD/verifiers:$PWD"
ls -lh verifiers/dfthcsos/FeMoCo76o113e.fcidump

# Reject invalid chemistry before building any replacement circuit.
python scripts/sweep_chem_angle_precision.py \
  --widths 12 11 10 9 --roundings nearest_even floor \
  --report /tmp/vqcc_chem004_screen.json

# Only after inspecting the numerical receipt, build the passing candidates.
python scripts/sweep_chem_angle_precision.py \
  --widths 11 10 9 --roundings nearest_even floor --build \
  --out-dir /tmp/vqcc_chem004_candidates \
  --report /tmp/vqcc_chem004_build.json
~~~

A candidate directory, if built, contains the unchanged factorization
and tree plus adjusted diagnostic source words and a newly compiled
ANGLE_k family. Check each built directory using the original verifier:

~~~bash
python verifiers/dfthcsos/verify.py \
  /tmp/vqcc_chem004_candidates/brot11_J9_nearest_even \
  --shots-per-address 64
~~~

Use the actual candidate directory printed by the script. Do not run the
example path if its metrics did not pass or it was not built. The verifier
returns JSON status PASS and a score on success; a failed oracle,
out-of-range Hamiltonian residual or invalid resource contract must be
preserved as a falsifying result.

Only a full official verifier PASS with lower resource cost constitutes
a chemistry improvement. Changing the angle data alone is not an
equivalence proof. Never overwrite the reference or currently grading
Kaggle submission.

## Evidence log

- Five exact integer word rescaling tests passed on GitHub Actions
  run 44827376521; captures identity, exact transport, ties, wrapped
  angles and rejected invalid values.
- Structural candidate oracle qubit counts 119, 122, 123 and 122
  from the same CI run.
- No numerical chemistry candidate has been reported as PASS yet.
- No official dfthcsos verification has been reported as PASS yet.


## Automated stage-B circuit verification

Once the numeric screen has built candidate folders, use the unmodified
chemistry verifier to compare the original and **every** built candidate
without silently ignoring failed candidates:

~~~bash
python scripts/verify_chem_precision_candidates.py \
  --baseline sample_submission/dfthcsos \
  --candidates /tmp/vqcc_chem004_candidates \
  --shots-per-address 64 \
  --report /tmp/vqcc_chem004_verified.json
~~~

Every source address is tested with 64 simulator shots, including
original-word recovery, register cleanup, phase correctness, chemical
accuracy and scored resources. The JSON keeps explicit failure reasons
and chooses the minimum passing score; it does not create or upload a
Kaggle ZIP, nor does it overwrite the already-grading submission.

## Experiment 006 negative-control audit

The shipped QROM builder also has an overly restrictive early-exit
predicate: it compares a subtree with one scalar instead of the entire
row vector. A corrected vector-uniform predicate is exact in principle,
but the 2026-11-20 10-circuit CI scan showed **zero** missed uniform
subtrees in this particular baseline, and **zero** predicted Toffoli
savings. All ten families retained 3974 needed AND nodes each.

Evidence: research/experiment_006_preflight.json; CI run 44827749977.
Do not spend additional runs on that exact predicate unless new source
tables exhibit the missing equality witnesses.
