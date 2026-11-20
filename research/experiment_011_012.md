# Experiments 011–012: Constructive Q-squared rows and actual qubit allocation generations

**Date:** 2026-11-20
**Scope:** Exact source construction and resource accounting, not a decoder improvement.

## Independently verified controlled decoder

The original Kickmix DQI source built a GF(2^6) decoder with n=6
syndromes, m=15 error positions and these measurements:

| Resource | Observation |
|---|---:|
| Compiled physical qubits Q | 180 |
| Named syndrome qubits | 36 |
| Non-syndrome peak slot capacity | 144 |
| Static Toffoli-like gates | 51,991 |
| Distinct temporary source allocation occurrences | 2,036 |
| Physical slots with multiple observed source generations | 36 |
| Largest observed generation count of one slot | 369 |
| Maximum explicitly tracked simultaneous live qubits | 177 |
| Gap to compiler's official Q | 3 |
| Native returned helper qubits released without observed birth | 0 |

The original builder's compiled circuit retained the expected 432,838
operations and 51,991 static Toffoli-like gates. The ledger recorded
2,836 explicit allocation or release events across 632 named stage
entries. The three independent original-source allocation tests
PASSED in GitHub Actions run 44833291311.

A physical slot can serve many distinct source generations sequentially.
The generation count is not the number of physical qubits.

## Corrections found while developing the instrumentation

The first CI trial failed because the Kickmix builder property
max_qubits is the configured allocator capacity, normally infinity,
NOT the actual high-water. The ledger now takes the authoritative
scored Q from the completed circuit's num_qubits.

The second CI trial failed because native C++ GF field helper methods
internally allocate and return source-visible scaffold qubits. These
are now registered as separate native-returned allocation occurrences
when the handle appears in Python source. A future source qubit release
with no observed birth must retain an explicit unknown-provenance label
rather than inventing a producer.

Only the corrected third run is accepted. All original named
syndrome qubits persist and all tracked temporary qubits are freed.

## Indexed Q-squared join

Experiment 012 joins physical q.id slots 0..Q-1 with the canonical
indexed construction stage i=q.id+1. The stage contributes
(i-1) row cells, (i-1) column cells and one shared corner:

    new_positions(i) = 2*i - 1.

The exact scoring factor is

    Q^2 = sum_(i=1)^Q (2*i-1).

Each slot may have multiple separately labeled generation occurrences,
but contributes one canonical row to the scored physical-qubit factor.
The row order is a reproducible accounting index; it does not imply
a physical square layout, that qubits are causally ordered by q.id,
or that all native helper births have been observed.

At Q=180, the factor is 32,400 and its one-qubit terminal marginal
would be 359 after a valid reduced-qubit compilation. At the actual
benchmark Q=1893, Q^2=3,583,449 and the first one-qubit reduction would
change this factor by 3,785.

## Independent WSL replication at benchmark syndrome width

After updating the research branch, execute:

~~~bash
python -m unittest discover -s research -p "test_dqi011*.py" -v
python -m unittest discover -s research -p "test_dqi012*.py" -v

python scripts/profile_dqi_source_allocations.py \
  --n 70 --m 70 --degree 12 \
  --report /tmp/vqcc_dqi011_n70_m70.json

python scripts/join_dqi_square_source.py \
  /tmp/vqcc_dqi011_n70_m70.json \
  --report /tmp/vqcc_dqi012_n70_m70.json
~~~

This is a structural source test with the full 70 syndrome words but
only 70 classical mask positions, rather than the 4095-position
competition source. It does not verify DQI phase correctness or
resource savings. A matching Q is a tested hypothesis, not a
prerequisite assumption.

Next: identify physical-qubit source participation at the actual
high-water stage. Prove that a given temporary source obligation can
be withheld or reused without overlapping any still-required
generation, then rebuild a smaller circuit and run the original DQI
verifier before claiming a score reduction.
