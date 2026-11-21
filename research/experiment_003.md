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


## Results — completed source-ledger experiments (2026-11-20)

All 32 subsets of the five independent **one-bit** width reductions were
evaluated. The numeric program verified each screen-passing candidate on
all 3,133,452 values of x, then the original Kickmix circuit builder
constructed .kmb files and the unmodified official Invsqrt verifier
checked 32 shots (x=1..16, two per x, batch 16, seed 20261120).

- 32 candidate configurations screened;
- 12 passed full reference numerical model, including baseline;
- all 12 passed the 32-shot official Kickmix smoke verifier;
- 20 were rejected by the numerical screen or a full-domain counterexample;
- **NO** full official 200-million-shot benchmark was run.

| Configuration | Static Toffoli-like | Qubits | Official 32-shot score |
|---|---:|---:|---:|
| Baseline (14,17,28,28,29) | 7,735 | 260 | 2,064,361.82356 |
| delta 13, product 27, result 28 | **7,447** | **256** | **1,956,947.10716** |
| delta 13, square 27, result 28 | 7,461 | 258 | 1,975,813.57545 |
| product 27, result 28 | 7,561 | 256 | 1,986,131.10716 |
| delta 13, product 27 | 7,531 | 258 | 1,995,337.82150 |

The best triple is a reduction of 288 static Toffoli-like gates
(3.72%) and four logical qubits (1.54%), giving a 5.2033% decrease in
the shortened 32-shot score. The full-domain **numerical model** found
worst relative error 5.04806410491034e-8 at x=2,684,414 versus a
strict acceptance threshold 2^-24 (~5.960464477539063e-8). That
candidate's maximum observed numerical error is 84.69% of the allowed
relative error.

Original unmodified verifier on 32 shots: PASS. SHA-256 of candidate
.kmb serialization as reported by the verifier:
9816fbfb5544949fb2c448410daf8144b825e45d0105cb118aac75c1a8c910e9.

These results are independent CI computations of the original reference
model and unmodified Kickmix verifier, not score estimates inferred
from optimizer logic. They are nevertheless **provisional** for the
competition until full official verification.

Reproducible run logs and structured output:
- research/experiment_003_full_ci_results.json (first 11 candidates)
- research/experiment_003_pairwise_ci_results.json (16 candidates)
- research/experiment_003_all32_ci_results.json (all 32 candidates)
- GitHub Actions run 44813235317 for the complete lattice.

### Reproduce just the best candidate on WSL

~~~bash
git -c http.version=HTTP/1.1 fetch origin
git merge --ff-only origin/research/vqcc-frontier-001
source ~/vqcc-venv/bin/activate

python scripts/sweep_invsqrt_precision.py \
  --levels 1 --combination-order 5 \
  --only delta_bits_and_product_bits_and_result_bits_minus_1 \
  --full --output-dir /tmp/vqcc_best003 \
  --report /tmp/vqcc_best003.json

python verifiers/invsqrt/verify_submission_invsqrt.py \
  /tmp/vqcc_best003/delta_bits_and_product_bits_and_result_bits_minus_1.kmb \
  --max-x 4096 --shots-per-x 2 --batch-size 256 \
  --max-workers 1 --seed 20261120
~~~

The latter command is a larger (8,192-shot) **smoke test**, not
the full competition requirement.

For targeted phase and scratch checks near the worst observed x,
plus dyadic boundaries, run:

~~~bash
python scripts/verify_invsqrt_targets.py \
  /tmp/vqcc_best003/delta_bits_and_product_bits_and_result_bits_minus_1.kmb \
  --focus-x 2684414 --focus-x 2588411 --focus-x 284670 \
  --span 2 --boundaries --shots 64 --seed 20261120 \
  --report /tmp/vqcc_best003_targeted.json
~~~

This script reuses the official verifier's exact phase-target,
tolerance and register routines. It remains a targeted audit, not
the official full-run substitute.

Next experiments: test the best candidate against additional
measurement seeds; investigate bit-width dependence and compensated
rounding without weakening the source-ledger or published accuracy
contract. Do not merge the draft branch into main as an accepted
competition improvement before appropriate verifier evidence.


## Targeted Kickmix source-input challenge — PASS

On 2026-11-20 the separate GitHub Actions run 44813583491 compiled
the best candidate independently and tested 83 distinct difficult x
values, 64 simulator shots per value (5,312 shots total).

Included the model's worst x=2,684,414 and its neighbors, the
reference's worst x=2,588,411, another reduced-precision boundary
x=284,670, the first 16 positive inputs and power-of-two boundaries.

**PASS**, zero register-restoration, scratch or phase failures.
Worst Kickmix phase error / tolerance = 0.8469246188549967
at x=2,684,414; SHA-256 of generated best .kmb:
9816fbfb5544949fb2c448410daf8144b825e45d0105cb118aac75c1a8c910e9.

Structured receipt: research/experiment_003_targeted_ci_results.json.
The targeted audit shares the source official reference phase
calculation but is not the complete official grader.
