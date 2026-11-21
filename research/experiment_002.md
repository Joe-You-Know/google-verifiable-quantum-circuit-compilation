# Experiment 002 — target/control causal-frontier commutation

**Date:** 2026-11-20  
**Status:** mathematical identity, independent classical tests and a structural
archive scan passed. **Not yet verified by the official Kickmix simulator.**
Do not claim a competition score improvement.

## Derivation

For a basis state, an X, CX or CCX gate toggles exactly one target bit t
if its zero, one or two controls are all 1. The target is not a control.

Two target-toggle gates U and V commute provided neither writes a control
of the other:

- target(U) is not a control of V;
- target(V) is not a control of U.

They may share controls, or share their target. Their target actions are XOR
additions determined by controls that neither changes, so they commute on
every basis state, and as permutation unitaries on arbitrary superpositions.

When U is an involution and each intervening gate commutes with U:

    U V1 ... Vk U = V1 ... Vk U U = V1 ... Vk.

An observed identical pair therefore admits a source-grounded omission
certificate. This does not authorize crossing HMR, R, CZ, Z_POW, register
operations, conditional gates or any other unknown instruction. Those
are global barriers.

## Implementation

The tool at tools/causal_commuting_frontier_kmx.py tracks the most recent
write to each candidate control, most recent read of its target as a
control, and previous retained occurrence of its exact gate signature.

A cancellation is permitted only if all conflicting event indices precede
the previous candidate occurrence. Cancelled events remain in blocker
records. This can miss additional cancellations but cannot add invalid
ones. All unknown lines are preserved.

## Structural observations

Source: uploaded ThemBones *third-party* archive (archive (2).zip),
15 files at chem/loaders_kmx/angle_k_*.kmx, NOT the original reference
circuits at sample_submission/dfthcsos.

- 118,820 CX gates omitted
- 18 X gates omitted
- 0 CCX gates omitted
- 59,419 cancelled pairs total

Per-file data: research/experiment_002_counts.json

Independent local validation:
- 5 Python unit tests passed; 100 generated five-qubit circuits on all 32
  basis inputs = 3,200 before/after comparisons.
- The original and transformed archived circuits had identical nonreversible
  barriers. There were 51 changed reversible segments. Eight randomized
  basis-state comparisons per segment = 408 checks, all passed.
- Official Kickmix functional verifier and score comparison are pending.
  Omitting CX alone cannot improve the scored Toffoli/qubit resources.

## Next independent test on user's WSL machine

Activate the existing CPython 3.13 venv in the local project directory.
These commands preserve all original and v1 files.

~~~bash
git -c http.version=HTTP/1.1 fetch origin
git pull --ff-only
python -m unittest discover -s tests -v
export PYTHONPATH="$PWD/kickmix:$PWD/verifiers"

python tools/causal_commuting_frontier_kmx.py \
  /tmp/invsqrt_original.kmx /tmp/invsqrt_optimized_v2.kmx \
  --report /tmp/invsqrt_optimized_v2.audit.json

python scripts/convert_kickmix.py \
  /tmp/invsqrt_optimized_v2.kmx /tmp/invsqrt_optimized_v2.kmb

python verifiers/invsqrt/verify_submission_invsqrt.py \
  /tmp/invsqrt_optimized_v2.kmb \
  --max-x 16 --shots-per-x 2 --batch-size 16 \
  --max-workers 1 --seed 20261120
~~~

Compare the output with research/experiment_001_invsqrt_smoke.json.
A passing 32-shot smoke test is necessary but insufficient for full
competition acceptance. Scored resource improvement must be separately
observed rather than inferred from instruction count.


### Reproducing the archive audit

Extract the user-supplied ThemBones archive to any private local directory.
Then run from the repo root:

~~~bash
python scripts/audit_reversible_segments.py \
  /path/to/archive/chem/loaders_kmx --samples 8 --seed 20261120
~~~

Expected structural audit: 15 files, 51 changed reversible segments, 408
independent randomized basis comparisons, all PASS. This command does
**not** require Kickmix to be installed because it evaluates only runs of
X/CX/CCX gates separated by preserved instruction barriers.


## Invsqrt source-circuit verification (user WSL, 2026-11-20)

After fetching this branch, the local CPython 3.13 environment passed all
13 structural tests. The v2 optimizer processed the actual converted
Invsqrt reference circuit and removed **four X gates in two pairs**.
Both output .kmx text SHA-256 and output Kickmix .kmb SHA-256 match the
Experiment 001 optimized files, i.e., v2 introduced no additional changes.

The user's official supplied verifier output reports **PASS** with
16 x inputs, two shots each, explicit seed 20261120, batch size 16,
one worker, total 32 shots. Reported metrics:
- operations 62,156 (reference 62,160)
- Toffoli count 7,735 (unchanged)
- qubits 260 (unchanged)
- reaction depth 4,005 (unchanged)
- score 2,064,361.8235632381 (unchanged)
- optimized .kmb SHA-256 c56be5aea2d9ef05dc74f3019971b73fe23535f895897e21726765223d7d28e3.

For full numeric settings and original circuit SHA, see
research/experiment_001_invsqrt_smoke.json. This is a **short smoke test**,
not full-domain verification or evidence of scoring improvement.

The broader chemistry-archive structural omissions also remain outside the
official score until independently tested with full verifier settings.
