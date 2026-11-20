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


## Constructive square-factor accounting: independently indexed rows

**2026-11-20 correction:** The numerical scoring factor Q^2 should be
retained as distinguishable source stages, rather than reduced to a
label before analyzing individual qubit nonconstruction obligations.

At stage i the newly constructed square shell consists of:
- i-1 cells with first index i and second index smaller than i;
- i-1 cells with second index i and first index smaller than i;
- one diagonal corner (i,i).

This stage contains exactly 2*i-1 distinct cells. There are never two
copies of (i,i), and every earlier cell retains its own pair identity.
Thus, with independent occurrence witnesses,

    Q^2 = sum_{i=1}^Q ((i-1) + (i-1) + 1)
        = sum_{i=1}^Q (2*i-1).

The written expression sum_{i=1}^Q (2*Q-1) is not the same:
the latter equals Q*(2*Q-1). The term 2*Q-1 is the *last*
stage's contribution and hence the terminal one-qubit marginal
when Q changes from Q to Q-1 and the whole square is reindexed.

For benchmark Q=1893:
- scored quadratic factor = 3,583,449;
- terminal stage increment = 3,785;
- rescored factor at Q=1892 = 3,579,664;
- change for k removed qubits after a valid recompilation:
  sum_{i=Q-k+1}^{Q}(2*i-1) = k*(2*Q-k).

scripts/constructive_qubit_square.py emits all 1,893 separate stage
records, each retaining distinct row/column/corner sources. Its
independent tests check all ordered cell identities at small Q,
source occurrence counts and the exact 1893-qubit ledger.

**Boundary:** This is an indexed derivation of the *unchanged official
score*. It does NOT mean the existing static circuit can have an
arbitrary stage removed without preserving the actual quantum
construction, scratch cleanup and phase. The stage index is an
accounting occurrence, not a measured mapping onto named physical
qubits; that association must be added from the original circuit
allocator before attributing a particular causal dependency.

### Actual reference census (user WSL, 2026-11-20)

The earlier placeholder statement that DQI profiling was pending
is superseded by the recorded original 886,118,180-byte baseline:
Q=1893, classical bits=49,154, operations=86,051,014,
static Toffoli-like=5,725,461, reaction depth=170,757,
register contract PASS. The original DQI shot verifier remains NOT RUN.
Source: research/experiment_005_wsl_static_results.json.
