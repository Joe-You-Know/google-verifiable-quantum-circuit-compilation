# Experiment 001: Conservative causal-frontier gate omission

**Status:** local structural experiment reproduced; the official Kickmix
simulator was not executable in the evaluation environment. This is **not**
an officially verified or scored competition submission.

## Hypothesis and constructive law

Two instances of the same involutory gate U can be omitted when no retained
operation between them touches any of the gate's qubits. Intervening operations
on disjoint supports commute, allowing the two instances to meet and cancel:
U U = I. The omitted gate pair has no externally distinguishable action.

The prototype handles only unconditional Kickmix X, CX and CCX. Unknown syntax,
register declarations, measurements (HMR, R), conditioned gates, and other
operations are global barriers. This avoids inventing relationships between
unknown operations and candidate gate pairs.

For each qubit the optimizer retains the last touching gate. A candidate gate
cancels with a previous identical gate only when all its qubits report that
same previous gate as their most recent touching operation. If cancellation
occurs, prior qubit-frontier links are restored and subsequent gates can be
checked. Reports contain input/output SHA-256 digests and source-line pairs.

This rewrite is an exact unitary identity, not a statistical approximation.
However, serialization and each competition task's full register, phase,
measurement and cost requirements require independent verification.

## Results and limits

Dataset: uploaded third-party ThemBones milestone generator archive,
archive (2).zip, the 15 text circuits under chem/loaders_kmx/angle_k_*.kmx.

First local run: **1,306 cancellation pairs**, removing **2,612 CX gates**
and **zero CCX gates** across the 15 circuits. These are *not* the circuits
currently tracked under sample_submission/dfthcsos in this repository.

Eight Python unit tests passed. The tests include 60 deterministically
generated five-qubit circuits (60 operations each), exhaustively compared
against an independent basis-state simulator across all 32 basis inputs.
This is 1,920 input/circuit comparisons. Other tests cover measurement
barriers, conditioned operations, shared-wire dependencies and byte
preservation of nonremoved lines.

**Not established:** a Toffoli reduction, a lower official competition score,
or successful execution of the modified circuits by the official verifier.
The full source dataset and large binaries are not committed.

## Reproduce under WSL

Run from the repository root. **The bundled Kaggle `kickmix/kickmix.so`
requires CPython 3.13.** In particular, Python 3.12 lacks
`PyObject_ClearManagedDict`. Structural optimizer tests require only
the Python standard library and also work on 3.12.

If `python3.13` is already available:

~~~bash
python3.13 -m venv ~/vqcc-venv
source ~/vqcc-venv/bin/activate
python -m pip install -U pip
python -m pip install numpy scipy
~~~

Otherwise install a separate 3.13 runtime with `uv` (rather than replacing
Ubuntu's system Python). See https://docs.astral.sh/uv/getting-started/installation/

~~~bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.13
uv venv --python 3.13 ~/vqcc-venv
source ~/vqcc-venv/bin/activate
uv pip install numpy scipy
~~~

Check the exact library load **before** running conversions:

~~~bash
export PYTHONPATH="$PWD/kickmix:$PWD/verifiers"
python -c 'import sys,kickmix,numpy,scipy; print(sys.version); print(kickmix.__file__)'
python -m unittest discover -s tests -v
python tools/causal_frontier_kmx.py original.kmx optimized.kmx --report optimized.audit.json
~~~

If `import kickmix` fails with a missing `GLIBCXX_3.4.32`, the local
`libstdc++.so.6` is too old; it needs the corresponding GCC 13 runtime.
Ubuntu 24.04 normally has a sufficiently recent C++ runtime, but confirm
the actual diagnostic rather than overriding shared-library paths blindly.

For binary competition circuits, first configure the Kickmix package
already provided under kickmix/:

~~~bash
export PYTHONPATH="$PWD/kickmix:$PWD/verifiers"
python scripts/convert_kickmix.py sample_submission/invsqrt.kmb \
  /tmp/invsqrt_original.kmx
python tools/causal_frontier_kmx.py /tmp/invsqrt_original.kmx \
  /tmp/invsqrt_optimized.kmx --report /tmp/invsqrt_optimized.audit.json
python scripts/convert_kickmix.py /tmp/invsqrt_optimized.kmx \
  /tmp/invsqrt_optimized.kmb
~~~

Short smoke test, **not** full benchmark verification:

~~~bash
python verifiers/invsqrt/verify_submission_invsqrt.py \
  sample_submission/invsqrt.kmb --max-x 16 --shots-per-x 2 --batch-size 16 --max-workers 1
python verifiers/invsqrt/verify_submission_invsqrt.py \
  /tmp/invsqrt_optimized.kmb --max-x 16 --shots-per-x 2 --batch-size 16 --max-workers 1
~~~

The original failed at the verifier's argument-validation gate when run
without `--batch-size 16`: 16 inputs times 2 shots = 32 shots, not divisible
by the default batch size of 256. This flag corrects the smoke-test settings;
no verifier pass is claimed yet.

Local WSL CPython 3.13/Kickmix conversion of the submitted Invsqrt baseline
reported 62,160 operations, 260 qubits, and 7,735 static Toffoli-like gates.
The conservative optimizer identified two pairs and omitted four X gates,
leaving 62,156 operations, 260 qubits and 7,735 static Toffoli-like gates.
No Toffoli improvement was observed in this test. Both `.kmb` conversions
succeeded; functional verification is still pending.

Both runs must pass. To compare the same stochastic trajectories during
diagnostics, use an identical explicit --seed for both. Without --seed,
the verifier derives different seeds from the two circuit file hashes.
The full benchmark must subsequently run with its official defaults.

For chemistry, convert and optimize all angle_k_*.kmb files into a new
family directory, retaining the same submission.npz. Then run the
original verifiers from this repository:

~~~bash
python verifiers/dfthcsos/verify.py sample_submission/dfthcsos --shots-per-address 1
python verifiers/dfthcsos/verify.py /path/to/optimized_family --shots-per-address 1
~~~

The chemistry verifier requires the locally retained FCIDUMP file under
verifiers/dfthcsos. The DQI circuit is large and its verifier requires
substantial RAM; defer its execution until the smaller tests pass.

## Next falsification gate

For any proposed replacement, independently confirm: (1) Kickmix parses
the output; (2) register and phase contracts hold; (3) the official
verifier passes at full settings; (4) Toffoli-like cost or qubit cost
improves. A reduction in CX count alone need not improve the score.
