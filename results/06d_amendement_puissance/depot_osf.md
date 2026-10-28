# OP-Cal — confirmatory analysis plan for the eICU locked test set (frozen specification + amendment 1, v2)

**Status:** PROPOSED — not yet validated.
**Protocol hash:** `d92099ea7c11d517` (60 development hospitals in 5 leave-hospitals-out folds; 96 locked hospitals with 100–499 stays).

## Files and fingerprints
| File | SHA-256 |
|---|---|
| `specification_gelee.json` (frozen 2026-10-26T18:32:44) | `302a9b448a1adcf481802ce6827e95e8c9afb623c3b7cf39ac3ca9f9eead25ae` |
| `amendement_1.json` (2026-10-27T15:42:20) | `7b74d3fa394112a8e0741a1f931ab6e75506baea3be71ba8484c6549c6e7e795` |
| `opcal_feas.py` / `opcal_robust.py` / `opcal_amend.py` | `9770a8614e7599ee…` / `eaa1313c3521df86…` / `39f947c9a1f4035d…` |

## Method under test
OP-Cal predicts the calibration-in-the-large offset a_h of a federated model at a new hospital without any of its labels. It uses an
empirical-Bayes (REML) meta-regression on 44 label-free site descriptors (observation process, case-mix, structure, score distribution),
fitted once on out-of-federation offsets of the 60 development hospitals. For labels defined by a test (hyperlactataemia, "not tested = negative"),
the theory Y* = D·Y predicts that hospitals testing more record more events than the model expects.

## Access to the locked set
No label, prediction or descriptor of a locked hospital has been read. The protocol notebook (nb01) displayed pooled statistics of the
locked set when the split was created, before OP-Cal was designed. The frozen descriptor function and one development control read the full
manifest file, which contains per-hospital mortality for all hospitals; only development-hospital sizes were used, and no locked-hospital value was
used, displayed or stored. A complete file-access log of the amendment notebook is included in `amendement_1.json` (field `acces`).

## Why the frozen primary criterion was amended (before any access to the locked set)
The frozen primary criterion had insufficient power (0.35 under the development estimates; median sampling variance of a_h ≈ 0.169 (about 7 expected deaths per locked hospital) versus between-hospital τ² ≈ 0.081 in development). The amendment also defines the estimand, the scope of b > 1/2, the comparators and multiplicity control. Power was simulated with the real locked-hospital sizes (96 hospitals, median 70 evaluation
patients) and the exact final procedure (same tests, same numbers of bootstrap and permutation draws). The few-label criterion (k = 25)
becomes descriptive (power 0.16).

## Confirmatory hypotheses (one-sided α = 2.5%, graphical procedure of Bretz et al. 2009, strong family-wise error control)
* **C1a (primary claim, initial weight 1/2):** site-level calibration slope b > 0 — REML meta-regression of locked a_h on frozen predictions, Knapp–Hartung.
* **C4 (mechanism, initial weight 1/2):** exact permutation test of the score U = Σ (z_h − z̄)(O_h − E_h) for the log testing rate.
* **C1b (weight received from C1a):** b > 0.5. Under the model and with a correct mean, this is a reduction of the expected squared calibration
  error versus the best constant (a theoretical reference); it does not by itself imply a log-likelihood gain or superiority over a constant
  correction estimated in development.
* **C2 (weight received from C1b):** per-patient log-likelihood gain versus no correction > 0.
* Edges: C4 → C1a, C1a → C1b, C1b → C2, C2 → C4. Mortality conclusions do not depend on C4.

Estimated power under the development estimates (b = 0.92, γ = 0.93): C1a 0.96; C4 0.97;
C1b 0.36; C2 0.33. Family-wise error of the full procedure under the global null:
0.030 [0.017; 0.049].
These are sensitivity analyses under explicit simulation assumptions (scores drawn from development patients), not guarantees.

## Always reported (descriptive)
α, b and R²_τ with CIs; bootstrap of b; γ with CI (and whether it contains 1); |CITL| and log-likelihood versus no correction and versus a
constant estimated in development; label-shift estimators (EM, BBSE); GRU-D; mechanism-only offset; few-label updating (k = 25).

## Reporting rules
C1a: "the site calibration signal transports"; without C1b: "the size of the gain remains uncertain on this set". C1b: "calibration
improvement versus the best constant confirmed, under the model". Failures are reported as such. The locked set is evaluated once.
