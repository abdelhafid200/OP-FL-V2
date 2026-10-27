# OP-Cal — confirmatory analysis plan for the eICU locked test set (frozen specification + amendment 1)

**Status:** PROPOSED — not yet validated.
**Protocol hash:** `d92099ea7c11d517` (60 development hospitals in 5 leave-hospitals-out folds; 96 locked hospitals with 100–499 stays by protocol, never accessed).

## Files and fingerprints
| File | SHA-256 |
|---|---|
| `specification_gelee.json` (frozen 2026-10-26T18:32:44) | `302a9b448a1adcf481802ce6827e95e8c9afb623c3b7cf39ac3ca9f9eead25ae` |
| `amendement_1.json` (2026-10-27T10:54:14) | `a02997c2662a2fb725ea3baf4eee104afaabd6634e651cd4b20a62e36e268352` |
| `opcal_feas.py` / `opcal_robust.py` / `opcal_amend.py` | `9770a8614e7599ee…` / `eaa1313c3521df86…` / `b7a16ab9572f90e1…` |

## Method under test
OP-Cal predicts the calibration-in-the-large offset a_h of a federated model at a new hospital without any of its labels. It uses an
empirical-Bayes (REML) meta-regression on 44 label-free site descriptors (observation process, case-mix, structure, score distribution),
fitted once on out-of-federation offsets of the 60 development hospitals. For labels defined by a test (hyperlactataemia, "not tested = negative"),
the theory Y* = D·Y predicts an offset slope γ = 1 on the log testing rate.

## Why the frozen primary criterion was amended (before any access to the locked set)
The frozen primary criterion had insufficient power (0.31 under the development estimates; median sampling variance of a_h ≈ 0.169 (about 7 expected deaths per locked hospital) versus between-hospital τ² ≈ 0.081 in development). The amendment also defines the estimand, its link to calibration improvement (b > 1/2) and multiplicity control. Power was simulated with the real locked-hospital sizes (96 hospitals, median 70 evaluation
patients) and the exact final procedure; all scenarios are in `amendement_1.json` (field `puissance`). The few-label criterion (k = 25)
becomes descriptive (power 0.17).

## Confirmatory hypotheses (one-sided α = 2.5%, family-wise error controlled)
* **Family 1 (Holm):** C1a — site-level calibration slope b > 0 (REML meta-regression of locked a_h on frozen predictions, Knapp–Hartung);
  C4 — γ > 0 (offset logistic regression, hospital bootstrap).
* **Family 2 (only if family 1 is fully rejected; fixed sequence):** C1b — b > 0.5 (equivalent to a reduction of the expected squared
  calibration error versus the best constant); then C2 — per-patient log-likelihood gain versus no correction > 0.

Estimated power under the development estimates (b = 0.92, γ = 0.93): C1a 0.95; C4 0.99; family 1 0.94;
C1b confirmed 0.33; C2 confirmed 0.30. Simulated type I error: C1a 0.024,
C1b 0.016, C4 0.047 (target 0.025).

## Always reported (descriptive)
α, b and R²_τ with CIs; bootstrap of b; |CITL| and log-likelihood versus no correction and versus a constant; label-shift estimators (EM,
BBSE); GRU-D; mechanism-only offset; few-label updating (k = 25).

## Reporting rules
C1a alone: "the site calibration signal transports; the size of the gain remains uncertain". C1b: "calibration improvement confirmed".
Failures are reported as such. The locked set is evaluated once.
