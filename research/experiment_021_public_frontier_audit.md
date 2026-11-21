# Experiment 021 — public VQCC source and leaderboard-frontier audit

**Date:** 2026-11-21. **Status:** public-source cross-audit complete; latest external circuits NOT independently simulated. **Sources:** user-uploaded `archive (5).zip` and `qcc-3-375-t-loaders-tight-table-lb-33-13521.ipynb`. Their complete archive and notebook bytes are retained by the original user, not copied into this research branch.

## Exact input provenance

- Public archive SHA-256: `435189ab7ea18c4d11679630a06647b58413ff91d15ab29f34770eff30b97810`
- Notebook SHA-256: `e5d8a335e982923b70df71f84602aa49a3df08082dc3390db35239724f44cf96`
- Audit method: parse notebook JSON and literal AST; never execute arbitrary notebook cells. Inspect both nested `.pack` ZIP files, compare archived SHA-256 manifest against independently streamed digests of selected members; load public chemistry `submission.npz` with `allow_pickle=False` and recompute GF(2) low-bit matrix ranks with binary row elimination.

The archive has two 18-member submissions (`submission_final.pack` and `submission_d.pack`), both with one Invsqrt, one DQI, fifteen `angle_k` chemistry circuits and one chemistry table. They retain Apache-2.0 LICENSE/NOTICE crediting team ThemBones (Danish Ali), Syed Asad Ali, and upstream authors. Exact DQI SHA-256 values: final `175a61e31f5ac33e2869c2d945caf194c12e1011a50588855e71546b16042099`; alternate d `47480efbb7b94b337304ac57acbc4e1b604259b95a6d7402e35ab7c9ba750204`.

## The notebook requires additional independently sourced public files

The notebook (version 8, 2026-11-21) pins:
- Invsqrt `d2148a7cd7a4d0a004eca1e7b18f9fd1282df4ed3be4a9aa970842f9119fa307` — **matches the archive**.
- DQI `4b5721411adc239f61fc11c773a2358b75dfe7cb15586efae4f0459c77d77e52` — **matches neither archived DQI variant**.
- 15 maoxin123 loaders — **zero of 15 match archived loader hashes**.
- leotang09 or maoxin123 public chemistry tables (`51f412e9…` / `508364c7…`) — **do not match archive `e259454d…`**.

Thus a successful replay of the latest notebook cannot be made from the two uploaded files alone. The uploaded archived submission can serve as an independently tested predecessor and source control, not a substitute for the pinned 900-qubit DQI.

## Cross-submission score and resource comparison

The user's Experiment 020 was verified locally at n=70,m=4095, 102,400 shots and `log2_delta=-128`, zero phase/value errors, Q=1876, mean Toffoli-like=5,618,551.922959, local DQI score=23,555,742,358,022.918, and Kaggle server `COMPLETE` public aggregate score=1.03006 (submission 58651355).

The *public notebook reports* a local 33.135213064726 three-task score from unmodified official verifier APIs with 0 DQI errors, using:
- rithvikredrouthu Invsqrt `d2148a7c…`: Q=37; cost=60,955.326708;
- tonylica DQI `4b572141…`: Q=900; mean Toffoli-like=316,131.221563; cost=305,041,647,011.398;
- maoxin123 15 chemistry loaders: 3,375 Toffolis per pass, chemistry T=13,250, Q=405; with leotang09-inspired refitted weights chemistry cost=251,774,061.476.

The literal notebook reference costs are (Invsqrt 2,076,774.233715282; DQI 24,439,463,583,672.93; chemistry 3,355,599,588.3155375). Independently recomputing their cost ratios yields 34.07043, 80.11845, and 13.32782, geometric mean **33.13521306472748** — matching the notebook's 33.13521306472598. This is **not independent evidence of the notebook's Kaggle server leaderboard score**; our 1.03006 is server-reported, whereas its 33.13521 has only been inspected in local notebook outputs.

The public notebook's DQI cost is about **77.2214 times lower** than our verified candidate, resulting from Q 1876→900 (−52.03%) and mean Toffoli factor ≈17.7728. This is a difference between decoder architectures, not evidence that our standalone norm quotient can be directly substituted into the public source.

## Independent causal-word constraint test on uploaded archive

Archive `angle_words` is shape (1219,75). Group each row as 15 blocks of 5 words, set each block's source-indexed difference word `D_k = B_(k-1) XOR B_k` (initial previous block absent, represented by an explicit first-block relationship), and evaluate bit 0 over the notebook's 77×16 address layout (first 76 rows). Recomputed maximum GF(2) ranks:

```text
k:     0  1  2  3  4  5  6  7  8  9 10 11 12 13 14
rank: 16 16  2  2  2 16  2 16  2  2  2 16  2  2  2
```

Matches the public notebook exactly. The high-rank restarts are k={0,1,5,7,11}. Notebook-reported maoxin123 source-loader T-per-pass counts:

```text
246,241,218,218,218,241,218,241,213,218,218,241,218,213,213
```

Sum exactly 3,375 per pass. The rank pattern is **independently reproduced from supplied data**; causal explanation relating high rank to low-bit rounding-chain restart is notebook authors' interpretation pending separate source-level derivation. New word construction overcoming a rank-restart constraint is a falsifiable chemistry direction; local table-weight tuning has very limited remaining margin near the reported error_1/error_2/gap gates.

## Next controlled experiments

1. Verify both archived DQI variants **separately** with the actual supplied DQI grader. Never attribute the notebook's 900-Q/316k metrics to their different hashes.
2. Obtain the notebook's exact pinned `4b572141…` DQI, 15 maoxin123 loaders and `51f412e9…` leotang09 table from their credited public outputs. Validate all SHA-256 values and retain attribution/NOTICE before reuse.
3. Make three one-component control comparisons against our verified Experiment 020 ZIP: replace **only Invsqrt**, **only DQI**, **only the chemistry family** in separate submissions, verifying each locally first. Distinguish measured gains from score model predictions.
4. For **novel** DQI optimization, inspect public source for its current producer structure and register liveness before trying to integrate our authenticated Experiment 019 gate; the large original quotient scaffold may not exist in the newer architecture.
5. For **novel** chemistry optimization, vary the five high-rank restart words under full literal word, factorization and gate fidelity; retain the unchanged source and run native compile plus exact verifier.

**Unverified model-only scenarios** (do not report as Kaggle scores): our other two tasks unchanged with the notebook DQI would scale score 1.03006 to about 4.3864; our DQI unchanged with notebook Invsqrt and chemistry would yield ≈7.7812 in the same reference-cost model; the notebook's all-public configuration gives ≈33.13521 in its own local run.

This source audit is a change of experimental baseline, not evidence of a new optimization or of an independently reproduced public DQI verifier run. Retain all credits when making controlled public-asset comparisons.
