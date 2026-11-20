# Submission 003 — best Invsqrt plus unmodified DQI and chemistry baseline

**Date:** 2026-11-20.  
**Competition:** https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation

**Status:** user reported an initial Kaggle rejection due to the uploaded
ZIP filename, which had been generated as `vqcc_experiment003.zip`.
The user renamed it to `submission.zip`; a subsequent accepted upload or
Kaggle score has **not** yet been confirmed in the current conversation.
No Kaggle score, receipt or leaderboard placement is claimed.

## Submission contract

The user's Kaggle submission attempt established that the **outer archive filename must be exactly `submission.zip`**. Our earlier packager incorrectly permitted other ZIP filenames; the issue is corrected, with a regression test. The competition ZIP contains:

- invsqrt.kmb — our best Experiment 003 precision candidate;
- dqi.kmb — the local, large DQI sample from the competition;
- dfthcsos/submission.npz — original factorization and Givens tree;
- dfthcsos/angle_k_0.kmb through angle_k_9.kmb — original chemistry family.

**Do not zip the entire data directory.** DQI (~661 MiB uncompressed)
must remain local because it exceeds the normal GitHub file-size ceiling.
The ZIP is not committed to the repository.

The packaging tool checks input presence, chemistry numbering, required
NPZ array filenames, output ZIP members, CRC, and source hashes. This
confirms packaging consistency, NOT validation of DQI or chemistry physics.

## Local WSL procedure

From the repo root on the research/vqcc-frontier-001 branch:

~~~bash
git -c http.version=HTTP/1.1 -c http.proxy= -c https.proxy= fetch origin
git merge --ff-only origin/research/vqcc-frontier-001
source ~/vqcc-venv/bin/activate
export PYTHONPATH="$PWD/kickmix:$PWD/verifiers"

# Confirm the local DQI and chemistry baselines exist:
ls -lh sample_submission/dqi.kmb \
       sample_submission/dfthcsos/submission.npz
ls sample_submission/dfthcsos/angle_k_*.kmb

# Best candidate was already generated under /tmp/vqcc_best003:
test -f /tmp/vqcc_best003/delta_bits_and_product_bits_and_result_bits_minus_1.kmb

python scripts/package_vqcc_submission.py \
  --invsqrt /tmp/vqcc_best003/delta_bits_and_product_bits_and_result_bits_minus_1.kmb \
  --dqi sample_submission/dqi.kmb \
  --chemistry sample_submission/dfthcsos \
  --output submissions/submission.zip \
  --report submissions/vqcc_experiment003.audit.json

python -m zipfile -l submissions/submission.zip
~~~ 

The ZIP will appear on Windows at:
D:\google-verifiable-quantum-circuit-compilation\submissions\vqcc_experiment003.zip

If your existing ZIP was already built and renamed, **do not rebuild** it.
Verify in Windows PowerShell with
`Test-Path .\\submissions\\submission.zip`, and use the file you renamed.

For the already-installed Kaggle CLI in **Windows PowerShell**, submit as
**one line** (no Bash backslashes):

~~~powershell
kaggle competitions submit google-verifiable-quantum-circuit-compilation -f ".\\submissions\\submission.zip" -m "Experiment 003: optimized Invsqrt, baseline DQI and chemistry"
kaggle competitions submissions google-verifiable-quantum-circuit-compilation
~~~

Alternatively use the competition's Submit page in the Kaggle website
to upload `submission.zip`. Never send credentials to ChatGPT or commit
them into the repository. If uploading fails, preserve the exact Kaggle
rejection message. Rename only changes the outer file path: it does
not alter the ZIP's internal member names or their contents.

## Validation distinction

Observed experiment: winning Invsqrt circuit reduces Toffoli count
7,735 -> 7,447 and qubits 260 -> 256. The reference numerical model
passed all 3,133,452 allowed inputs. Kickmix smoke verifier passed
8,192 shots on the user's independent WSL machine; targeted Kickmix
phase check passed 5,312 shots on 83 additional challenging inputs.
The full original three-task Kaggle evaluation has NOT been run.

Our first submission is an early leaderboard measurement, not a final
competition result. Kaggle scores the **geometric mean across all three
tasks**. If DQI or chemistry is invalid, the full portfolio fails.
Preserve Kaggle's submission ID, status and error if any in a follow-up
ledger. Do not assume success merely because upload completes.
