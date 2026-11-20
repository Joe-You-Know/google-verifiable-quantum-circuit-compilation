# Experiment 003 — source-derived Invsqrt precision-width search

**Date:** 2026-11-20.  
**Status:** candidate generator and numerical screening added, but no
precision-shortened candidate is accepted until both full-domain accuracy
and the official Kickmix verifier pass.

## Research question

The supplied reference generator uses a three-step Newton-Raphson circuit.
It exposes five independent integer-valued precision parameters:

| Parameter | Reference value | Meaning |
|---|---:|---|
| delta_bits | 14 | Horner input precision |
| coef_bits | 17 | Polynomial coefficient and Horner result width |
| square_bits | 28 | Squared approximation width |
| product_bits | 28 | Normalized product and correction width |
| result_bits | 29 | Final result width |

These are **not** arbitrary numerical guesses: the reference
verifiers/invsqrt/nr_reference_circuit.py provides both
fixed_point_model(...) and build_nr_circuit(...), with matching
precision parameters.

The reference model comments report worst-case relative error around
2.84e-8 for the default pipeline. The required precision threshold
is 2^-24 (~5.96e-8), so there may be headroom to omit low-weight
intermediate bit construction.

The research hypothesis is that decreasing one of these bit widths
can preserve the required phase approximation while reducing counted
CCX/CCZ/CSWAP cost or number of qubits.

## Procedure and source receipts

scripts/sweep_invsqrt_precision.py:
1. Constructs a fixed, reproducible input set covering the first 256
   inputs, last 256 inputs, a uniform and geometric grid, and neighborhoods
   of dyadic boundaries;
2. Evaluates the reference's original relative_error model for baseline
   and every one-coordinate minus-1/minus-2 precision;
3. Rejects nonfinite/error/overflow candidates;
4. When --full is enabled, evaluates **all 3,133,452 input values** in
   bounded memory chunks for each screen-passing candidate;
5. Can compile passing candidates with the original build_nr_circuit,
   retaining their source precision tuple and unmodified Kickmix cost
   statistics;
6. Writes a JSON provenance record and new .kmb outputs outside the repo.
   No existing submission is overwritten.

This is a directed deterministic numerical screen: no random input
selection and no searching for desired outputs by measuring the
grader's unknown stochastic outcomes.

## Run under existing WSL CPython 3.13 environment

From the existing research branch:

~~~bash
git -c http.version=HTTP/1.1 fetch origin
git merge --ff-only origin/research/vqcc-frontier-001
source ~/vqcc-venv/bin/activate
export PYTHONPATH="$PWD/kickmix:$PWD/verifiers"

# Fast numerical screen, no circuit creation:
python scripts/sweep_invsqrt_precision.py \
  --levels 1 2 --no-circuits \
  --report /tmp/vqcc_precision_preview.json

# Follow-up: full-domain numerical check and circuit construction.
# Creates new .kmb files only for candidates whose model passes:
python scripts/sweep_invsqrt_precision.py \
  --levels 1 2 --full \
  --output-dir /tmp/vqcc_precision_003 \
  --report /tmp/vqcc_precision_full.json
~~~

Only candidates with "full": {"status": "PASS",
"entire_domain_checked": true} should proceed to simulator verification.
The default baseline's 7,735 static Toffoli-like gates and 260 qubits
are comparison targets, not a claimed optimum.

For a generated candidate at /tmp/vqcc_precision_003/NAME.kmb:

~~~bash
python verifiers/invsqrt/verify_submission_invsqrt.py \
  /tmp/vqcc_precision_003/NAME.kmb \
  --max-x 16 --shots-per-x 2 \
  --batch-size 16 --max-workers 1 --seed 20261120
~~~

This is only a quick smoke test. A full official grader run is required
before any score improvement is confirmed. In particular, the model
relative-error criterion is not itself an official phase verification,
and the short seeded test covers only 16 x inputs.

CI workflow: .github/workflows/invsqrt_precision_screen.yml, which
checks a directed sample on Python 3.13 and preserves the JSON receipt.

## Interpretation

An observed reduction in static Toffoli-like cost after exhaustive
reference-model checks is a **candidate** optimization; only a complete
passing official verifier result supports a scored reduction. The
source construction of all omitted low-weight arithmetic contributions
must remain auditable by recording parameter widths and provenance,
and by retaining the original reference file unmodified.
