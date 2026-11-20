# QDay ECC ROM audit — cross-application to VQCC and constructive QR

Date: 2026-11-20. Source: user-supplied q_day_work-main.zip.
Original archive SHA-256: 25ec6cf363cdbd6026db257c5101c50a1b0de8916e09e5b365a57a1769a379a2.
Status: verified offline raw-count audit and exact source-ROM structural test.
No new Qiskit/Aer/IBM execution, full DQI replacement, or Kaggle submission.

## Quantum recovery inference and null controls

The original classical host computes an ECC table from public G and Q,
using CPU-side affine EC arithmetic and Euclidean inversion. The
quantum ROM is a sequence of one-hot controlled XORs. It does NOT run
the ECC group law or Extended Euclidean Algorithm coherently in hardware.

The original candidate voter applies a public-key equality filter
before choosing the winner. Our exact raw-count reanalysis found:

| run | verified d | raw winning-relation rank of d | top unfiltered candidate |
|---|---:|---:|---:|
| order 7, 1024 shots | 6 | 2 | 5 |
| order 31, 2048 shots A | 18 | 6 | 17 |
| order 31, 2048 shots B | 18 | 7 | 21 |

Independent 1,000-trial permutations of measured s against r for each
run preserve separate r,s marginals but destroy their pairing.
The original postverification procedure still returned the known d
for all 3,000 randomized controls.

For an ideal ROM on zeroed output ancillas, its output must be a
source-table value. The source allows 4 distinct output values in the
order-7 example and 16 in order-31. User archived measurements:
- order7: 110/1024 valid outputs (10.74%), 914 invalid.
- order31 A: 215/2048 valid (10.50%), 1833 invalid.
- order31 B: 237/2048 valid (11.57%), 1811 invalid.

Archived physical two-qubit gate counts: 20191, 542774, 569092.
Thus the source archive does not establish quantum key recovery; the
intended oracle outputs are largely not preserved in the recorded
hardware samples. The logs may still document real hardware runs.

## Exact measured-output fiber reduction

For original finite public table f, injectively map its distinct
observed output values through a new label C. Then f(x)=f(y) exactly
when C(f(x))=C(f(y)). The measured-output partition and hence ideal
Fourier address distribution are preserved. No private d enters
the construction of C.

- order 7: 8 output qubits -> 2 (4 source classes, 6 logical saved).
- order 31: 8 output qubits -> 4 (16 classes, 4 logical saved).
- Frequency-aware class labels reduce source output MCX count
  198 -> 56 (order 7), 3168 -> 1984 (order 31).
- Gray address traversal, preserving and restoring zero-control masks,
  reduces pretranspile X toggles 384 -> 74 and 10240 -> 1042.

Exhaustive symbolic basis mapping tests (4 PASS) and noiseless
Fourier partition comparisons show exact source-level equivalence.
New candidate Qiskit hardware gate counts and actual quantum fidelity
have NOT yet been measured. The ROM table remains exponential in
address width.

Retaining full-point orientation vs x-only output distinguishes
31 instead of 16 output classes for order31, but changes the chosen
ideal Fourier relation statistic only from 21.75% to 21.81%.
This is a useful negative control about the observable's needs.

## Cross-project applicability

1. Immediate QDay: compact measured-output classes; Gray ROM; blind
   Fourier voting; Aer and equal-basis Qiskit transpilation.
2. PCL/QR: source preserving distinguishability conditional on a
   declared downstream measurement; an explicit finite source
   equivalence that can justify withholding surplus output labels.
3. DQI: NO direct qubit saving. QDay EC inversion is classical
   preprocessing; DQI 72-qubit quantum quotient/scaffold and
   conditional phase still require a new coherent reversible circuit.
4. Chemistry: no direct output relabel without reversible decoding,
   because Givens angle words are consumed coherently.
5. Invsqrt: no direct arithmetic optimization, though blind
   verification and exact source controls transfer.

## Software/source corrections

In Qiskit 2.2, QFTGate(num_qubits) accepts neither reported
approximation_degree=1 nor do_swaps/insert_swaps; the source's
try/except fallback appears to produce exact QFT, despite requested
approximation degree 1 in its report.
ibm_torino was 133-qubit Heron r1, not Falcon; IBM retired that
backend on 2026-04-01.

The user-provided conversation contains a self-contained offline
artifact QDay_Audit_and_Compact_Oracle_Experiment.zip with full
source reanalysis, JSON evidence, compact builder, four symbolic
tests, and optional Windows Qiskit comparison runner.

No cryptographic or Kaggle benefit is claimed without a newly
compiled circuit, blind information test, and resource measurements.


## DQI-first correction: Experiment 016 actual coherent quotient ROM

**2026-11-20:** The intended cross-application was a lower-qubit
**DQI** circuit, not an effort to optimize QDay for its own sake.
The QDay host-built ROM was therefore transferred to DQI's *quantum*
controlled quotient division and actually compiled with Kickmix.

For every nonzero denominator value d, the quotient update
target XOR=control*(numerator/d) is a linear GF2 transform of the
numerator. The construction computes the predicate [denominator=d]
under the original quantum control, applies its precomputed linear
map through controlled Toffolis, and uncomputes the predicate.
Denominator=0 gives no update. This preserves all inputs, controls,
target XOR behavior and scratch cleanup.

Original-source vs QDay-ROM measurements (independent Kickmix
simulator, GitHub CI run 44840542001):

| width | mode | Q | static Toffoli | simulator tests |
|---:|---|---:|---:|---:|
| 4 | native scaffold | 25 | 31 | 1536 PASS |
| 4 | QDay denominator ROM | 18 | 278 | 1536 PASS |
| 6 | native scaffold | 43 | 90 | 512 PASS |
| 6 | QDay denominator ROM | 26 | 2034 | 512 PASS |

Thus the method truly reduces **isolated gadget** Q while retaining
reversible quotient behavior. The Toffoli burden, however, is too
large for an attractive Q^2*T improvement at full field width.

Exactly, each nonzero denominator d produces a constant GF2 linear
numerator map. For each numerator bit j, the image of its basis
vector under inverse(d) runs through all nonzero output words as d
runs through nonzero field elements. Across all d, each target bit
appears 2^(b-1) times; b sources times b targets gives
b^2*2^(b-1) controlled XOR terms.

At b=12, direct expansion gives 294,912 such terms per quotient
before address equality comparisons. The existing b=12 native
controlled quotient gadget costs only 390 static Toffolis, with
109 total gadget qubits. A 12-bit full ROM has not been compiled.

The transfer therefore succeeds on *correctness and isolated qubit
compression*, but fails as an immediate efficient Toffoli design.
Next research should factor the 12-bit field into smaller coherent
subfield operations or prove that some EEA source denominator
values are unreachable; never assume that simply from tiny-curve
public ROM tables.

Source and exact reproducible checks:
scripts/bench_dqi016_qday_rom_quotient.py;
research/experiment_016_qday_rom_dqi_ci_results.json.
Whole DQI verifier has NOT run against a replacement.
