# Experiment 007 — vector-relative 11-bit chemistry projection

**2026-11-20, tested independently on user's WSL machine.**

The prior hypothesis was that jointly projecting the 12-bit Givens
angle-word construction onto an 11-bit chart, measured against the
original reconstructed source vectors, might recover chemical accuracy
that individual angle rounding loses.

It did not.

## Independent source-vector reconstruction

The projection minimized total squared vector distance:
- source rows: 3,976
- 75 angles per row
- original 12-bit reference, target 11-bit
- two backward coordinate passes
- independent nearest projection: 0.02967386568139805
- joint reverse projection: 0.029661852279634277
- fractional decrease: 0.0004048478850972037 (~0.0405%).

This is a genuine, but small, improvement **to the particular objective**
chosen for the source-relative projection. The optimizer does not
minimize either chemical reconstruction metric.

## Original chemical accuracy verifier metrics

The unmodified chemical evaluator (source FCIDUMP preserved) returned:

| Measure | 11-bit independent nearest | 11-bit joint vector projection | Required |
|---|---:|---:|---:|
| error_1 | 0.07690909892185493 | 0.08331625362213337 | <= 0.02 |
| error_2 | 0.029723819285085353 | 0.031288233214112435 | <= 0.02 |
| lambda_eff | 49.40251889398914 | 49.233537435681356 | scored |
| numerical status | FAIL | FAIL | PASS |

Both error measures actually grew after the source-vector error
decreased. The joint candidate was **not built**, and full original
Kickmix oracle verification was **not performed**, because the
numerical acceptance gate failed.

The observed failure does not prove that all possible 11-bit chemistry
representations are inadequate. It falsifies *this* particular
source-vector objective as a sufficient proxy for chemical accuracy.
The next admissible search must optimize the verifier's weighted
Hamiltonian consequences directly, rather than assuming source-vector
Euclidean distance preserves them.

Evidence: research/experiment_007_wsl_results.json. The original
reference's 12-bit circuit continues to PASS the supplied verifier;
nothing changes in the submission already grading on Kaggle.
