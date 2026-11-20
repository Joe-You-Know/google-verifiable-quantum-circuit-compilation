# Experiment 005 — DQI baseline causal-resource audit

**Date:** 2026-11-20  
**Status:** analysis method and static profile script implemented; actual large
local .kmb profile and benchmark score pending. No DQI improvement claimed.

## Why the cost structure differs from Invsqrt and chemistry

The supplied original verifier is
verifiers/dqi/verify_submission_dqi.py. It checks an MBUC phase oracle
with n=70 syndrome registers of 12 qubits each (840 syndrome qubits),
m=4095 classical outcome registers each 12 bits, and an upper bound of
l=n//2=35 errors. The field size is 2**12 and the default accepted
value count is 2016.

The verifier evaluates N=102,400 sampled shots by default, and computes

    score = R(eps_plus) * Q**2 * T,

where Q is total qubits, T is the mean observed Toffoli-like count per
shot, and eps_plus is the one-sided Clopper-Pearson confidence upper
bound. The verifier rejects eps_plus >= 1/16 and rejects Z_POW
instructions. It also requires syndrome preservation, clean ancillas,
and correct MBUC parity phase.

This differs from Invsqrt: merely reducing a static operation count
does not guarantee a decrease in its measured T. Conversely, a small
relative reduction in Q has twice its first-order influence on Q**2.

## Source-derived high-cost stages to inspect

verifiers/dqi/dqi_reference_circuit.py has five named stages:
initial_shift, forward_eea, chien_forney_mbuc, reverse_eea, and
uncompute_initial_shift.

The Chien/Forney stage iterates over up to 4,095 positions and contains
a controlled GF(2**12) inverse operation as well as conditional phase
contributions. It is a plausible high-cost target; its true
contribution has NOT yet been measured for the user's shipped .kmb
baseline.

Experiment target: derive which inverse/scaffold constructions can be
reused or withheld based on witnessed original control dependencies,
without altering phase parity, sampled measurement branches or clean
ancilla obligations. In particular, do not infer that masked or
conditioned work is absent when that condition has not been established.

## Measured baseline needed before optimization

The large DQI circuit is gitignored and is only on the user's WSL
machine. The baseline file is roughly 661 MiB; parsing it may require
several GiB of memory, so --load must be chosen explicitly.

~~~bash
source ~/vqcc-venv/bin/activate
export PYTHONPATH="$PWD/kickmix:$PWD/verifiers:$PWD"

# Cheap, streaming SHA-256/size receipt, no circuit in memory:
python scripts/profile_dqi_baseline.py \
  --report /tmp/vqcc_dqi005_file.json

# Explicitly opt in to parsing the large circuit and collecting static
# Toffoli/Q/operation stats, including official register-schema checking:
python scripts/profile_dqi_baseline.py --load \
  --report /tmp/vqcc_dqi005_static.json
~~~

The --load command is **only a static census**, not the unmodified
official DQI shot verifier. Keep its result even if parsing is too
memory intensive. No source file or competition artifact is edited.

The next experimental choice should be driven by recorded per-stage
resource costs, followed by a small n,m controlled instance and an
independently checked full DQI instance. Avoid treating low-confidence
shot tests as an official score: the default confidence requirement is
extremely strict at 2**(-128), and small sample sizes can fail the
confidence bound even for zero observed errors.
