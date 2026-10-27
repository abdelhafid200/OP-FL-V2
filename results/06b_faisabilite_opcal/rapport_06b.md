# Rapport 06b — faisabilité de la calibration de site sans label (OP-Cal)

Généré le 2026-10-26 12:20 par `notebooks/06b_faisabilite_opcal.ipynb`. Protocole `d92099ea7c11d517`. Agrégats uniquement.

## Verdict : GO COMPLET

| code | question | mesure | seuil | rempli |
|---|---|---|---|---|
| F1 | calibration prévisible sans label (mortalité, x_only, S_all) | R²_τ = 0.595 [0.283 ; 0.930] ; gain vs E1 = 0.0574 [0.0153 ; 0.1015] | R²_τ ≥ 0.25 et IC bas du gain > 0 | True |
| F2 | a priori appris utile avec k = 50 labels (mortalité, x_only) | retrecissement_fixe − EB_descripteurs = 0.0370 [0.0167 ; 0.0590] | IC bas > 0 | True |
| F3 | taux de dosage explique la calibration (hyperlactatémie, x_only) | R²_τ(S_mech) = 0.264 ; ρ = 0.520 ; γ = 0.93 [0.50 ; 1.37] | R²_τ ≥ 0.5 ou ρ ≥ 0.5 | True |

## Calibration de transfert (hôpitaux tenus à l'écart)

| tâche | rôle | seeds | hôpitaux | séjours | événements | événements/hôpital (méd.) | \|CITL\| moyen | CITL moyen (μ DL) | τ | I² | pente moyenne |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mortalite_x_only | principal | 3 | 60 | 19826 | 1862 | 24.000 | 0.304 | 0.058 | 0.285 | 0.632 | 1.006 |
| mortalite_x_obs | secondaire | 3 | 60 | 19826 | 1862 | 24.000 | 0.344 | 0.116 | 0.320 | 0.682 | 1.024 |
| mortalite_grud | secondaire | 3 | 60 | 19826 | 1862 | 24.000 | 0.356 | 0.093 | 0.328 | 0.691 | 0.997 |
| lactate_x_only | mécanisme | 5 | 60 | 11509 | 287 | 4.000 | 0.841 | 0.267 | 0.768 | 0.660 | 2.107 |
| lactate_x_obs | secondaire | 5 | 60 | 11509 | 287 | 4.000 | 0.728 | 0.333 | 0.554 | 0.507 | 6.619 |
| aki_x_only | contraste | 5 | 60 | 10763 | 440 | 6.000 | 0.432 | 0.080 | 0.277 | 0.338 | 0.931 |
| aki_x_obs | secondaire | 5 | 60 | 10763 | 440 | 6.000 | 0.370 | 0.108 | 0.000 | 0.000 | 1.001 |

## Régime 0 — prédiction croisée de a_h

| ligne | descripteurs | mean_abs_citl | R2_tau | R2_tau_IC_bas | R2_tau_IC_haut | gain_vs_E1 | gain_IC_bas | gain_IC_haut |
|---|---|---|---|---|---|---|---|---|
| mortalite_x_only / E0_aucune | 0 | 0.304 | 0.000 |  |  | -0.000 | -0.014 | 0.014 |
| mortalite_x_only / E1_moyenne | 0 | 0.304 | -0.009 | -0.043 | 0.021 | 0.000 | 0.000 | 0.000 |
| mortalite_x_only / S_obs | 12 | 0.291 | 0.299 | -0.170 | 0.606 | 0.013 | -0.028 | 0.054 |
| mortalite_x_only / S_case | 23 | 0.304 | -0.017 | -0.055 | 0.014 | -0.001 | -0.003 | 0.001 |
| mortalite_x_only / S_struct | 8 | 0.313 | -0.085 | -0.344 | 0.052 | -0.010 | -0.028 | 0.006 |
| mortalite_x_only / S_model | 2 | 0.299 | 0.129 | -0.091 | 0.322 | 0.005 | -0.019 | 0.028 |
| mortalite_x_only / S_all | 45 | 0.246 | 0.595 | 0.283 | 0.930 | 0.057 | 0.015 | 0.101 |
| mortalite_x_only / S_all+apache | 47 | 0.250 | 0.571 | 0.264 | 0.901 | 0.054 | 0.011 | 0.096 |
| mortalite_x_obs / E0_aucune | 0 | 0.344 | 0.000 |  |  | -0.016 | -0.044 | 0.014 |
| mortalite_x_obs / E1_moyenne | 0 | 0.328 | -0.044 | -0.098 | 0.005 | 0.000 | 0.000 | 0.000 |
| mortalite_x_obs / S_obs | 12 | 0.310 | 0.023 | -0.439 | 0.387 | 0.018 | -0.022 | 0.058 |
| mortalite_x_obs / S_case | 23 | 0.332 | -0.078 | -0.158 | -0.010 | -0.005 | -0.012 | 0.002 |
| mortalite_x_obs / S_struct | 8 | 0.327 | -0.065 | -0.373 | 0.139 | 0.001 | -0.024 | 0.026 |
| mortalite_x_obs / S_model | 2 | 0.320 | 0.007 | -0.162 | 0.167 | 0.008 | -0.009 | 0.026 |
| mortalite_x_obs / S_all | 45 | 0.256 | 0.394 | 0.027 | 0.772 | 0.072 | 0.029 | 0.117 |
| mortalite_x_obs / S_all+apache | 47 | 0.260 | 0.384 | 0.021 | 0.752 | 0.068 | 0.025 | 0.113 |
| mortalite_grud / E0_aucune | 0 | 0.356 | 0.000 |  |  | -0.006 | -0.030 | 0.019 |
| mortalite_grud / E1_moyenne | 0 | 0.350 | -0.047 | -0.107 | 0.011 | 0.000 | 0.000 | 0.000 |
| mortalite_grud / S_obs | 12 | 0.333 | 0.057 | -0.431 | 0.396 | 0.017 | -0.029 | 0.059 |
| mortalite_grud / S_case | 23 | 0.351 | -0.087 | -0.184 | -0.006 | -0.001 | -0.014 | 0.010 |
| mortalite_grud / S_struct | 8 | 0.351 | -0.082 | -0.334 | 0.089 | -0.001 | -0.026 | 0.022 |
| mortalite_grud / S_model | 2 | 0.348 | 0.003 | -0.118 | 0.120 | 0.002 | -0.012 | 0.016 |
| mortalite_grud / S_all | 45 | 0.247 | 0.589 | 0.302 | 0.905 | 0.103 | 0.055 | 0.150 |
| mortalite_grud / S_all+apache | 47 | 0.251 | 0.584 | 0.292 | 0.891 | 0.099 | 0.053 | 0.146 |
| lactate_x_only / E0_aucune | 0 | 0.841 | 0.000 |  |  | -0.016 | -0.081 | 0.058 |
| lactate_x_only / E1_moyenne | 0 | 0.825 | -0.118 | -0.209 | -0.044 | 0.000 | 0.000 | 0.000 |
| lactate_x_only / S_obs | 12 | 0.719 | 0.249 | -0.278 | 0.688 | 0.106 | 0.009 | 0.197 |
| lactate_x_only / S_case | 23 | 0.793 | 0.047 | -0.383 | 0.261 | 0.032 | -0.022 | 0.089 |
| lactate_x_only / S_struct | 8 | 0.858 | -0.343 | -0.747 | -0.148 | -0.033 | -0.068 | 0.003 |
| lactate_x_only / S_model | 2 | 0.841 | -0.373 | -1.276 | 0.056 | -0.017 | -0.094 | 0.053 |
| lactate_x_only / S_all | 45 | 0.743 | 0.292 | -0.293 | 0.595 | 0.082 | -0.031 | 0.197 |
| lactate_x_only / S_mech_fixe | 0 | 0.720 | 0.332 | -0.333 | 0.776 | 0.105 | -0.044 | 0.262 |
| lactate_x_only / S_mech | 1 | 0.692 | 0.264 | -0.106 | 0.649 | 0.133 | 0.016 | 0.256 |
| lactate_x_obs / E0_aucune | 0 | 0.728 | 0.000 |  |  | -0.000 | -0.076 | 0.084 |
| lactate_x_obs / E1_moyenne | 0 | 0.728 | -0.092 | -0.374 | -0.018 | 0.000 | 0.000 | 0.000 |
| lactate_x_obs / S_obs | 12 | 0.637 | 0.519 | -0.529 | 0.953 | 0.091 | -0.003 | 0.182 |
| lactate_x_obs / S_case | 23 | 0.715 | 0.049 | -0.321 | 0.338 | 0.013 | -0.021 | 0.048 |
| lactate_x_obs / S_struct | 8 | 0.730 | -0.419 | -1.958 | -0.022 | -0.002 | -0.034 | 0.029 |
| lactate_x_obs / S_model | 2 | 0.749 | -0.272 | -1.324 | -0.118 | -0.021 | -0.055 | 0.010 |
| lactate_x_obs / S_all | 45 | 0.678 | 0.325 | -0.695 | 0.696 | 0.051 | -0.030 | 0.135 |
| lactate_x_obs / S_mech_fixe | 0 | 0.604 | 0.704 | -0.667 | 1.000 | 0.124 | -0.012 | 0.266 |
| lactate_x_obs / S_mech | 1 | 0.583 | 0.636 | 0.112 | 1.000 | 0.145 | 0.031 | 0.265 |
| aki_x_only / E0_aucune | 0 | 0.432 | 0.000 |  |  | 0.006 | -0.016 | 0.027 |
| aki_x_only / E1_moyenne | 0 | 0.439 | -0.177 | -1.580 | -0.008 | 0.000 | 0.000 | 0.000 |
| aki_x_only / S_obs | 12 | 0.440 | -0.108 | -1.405 | 0.901 | -0.002 | -0.032 | 0.028 |
| aki_x_only / S_case | 23 | 0.427 | 0.039 | -0.601 | 1.000 | 0.012 | -0.015 | 0.038 |
| aki_x_only / S_struct | 8 | 0.451 | -0.116 | -3.213 | 0.532 | -0.012 | -0.048 | 0.027 |
| aki_x_only / S_model | 2 | 0.443 | 0.189 | -2.978 | 1.000 | -0.004 | -0.052 | 0.044 |
| aki_x_only / S_all | 45 | 0.448 | 0.196 | -1.273 | 1.000 | -0.009 | -0.051 | 0.031 |
| aki_x_only / S_mech_fixe | 0 | 0.431 | -0.155 | -0.751 | 0.373 | 0.008 | 0.001 | 0.015 |
| aki_x_only / S_mech | 1 | 0.433 | -0.293 | -1.809 | 0.414 | 0.006 | -0.009 | 0.023 |
| aki_x_obs / E0_aucune | 0 | 0.370 |  |  |  | 0.021 | -0.005 | 0.046 |
| aki_x_obs / E1_moyenne | 0 | 0.392 |  | -13.141 | -0.025 | 0.000 | 0.000 | 0.000 |
| aki_x_obs / S_obs | 12 | 0.391 |  | -16.304 | -0.077 | 0.000 | -0.002 | 0.003 |
| aki_x_obs / S_case | 23 | 0.394 |  | -16.080 | -0.177 | -0.002 | -0.006 | 0.001 |
| aki_x_obs / S_struct | 8 | 0.400 |  | -22.266 | 0.386 | -0.008 | -0.021 | 0.004 |
| aki_x_obs / S_model | 2 | 0.392 |  | -13.138 | -0.025 | 0.000 | -0.000 | 0.000 |
| aki_x_obs / S_all | 45 | 0.395 |  | -17.949 | -0.151 | -0.004 | -0.008 | -0.001 |
| aki_x_obs / S_mech_fixe | 0 | 0.386 |  | -5.071 | 1.000 | 0.006 | -0.001 | 0.013 |
| aki_x_obs / S_mech | 1 | 0.390 |  | -15.022 | 1.000 | 0.002 | -0.012 | 0.016 |

## Mécanisme (labels définis par un examen)

| tâche | rôle | rho_spearman | gamma | gamma_IC_bas | gamma_IC_haut | R2_tau_S_mech_fixe | R2_tau_S_mech | R2_tau_S_all | ET du log taux de dosage |
|---|---|---|---|---|---|---|---|---|---|
| lactate_x_only | mécanisme | 0.520 | 0.928 | 0.504 | 1.372 | 0.332 | 0.264 | 0.292 | 0.858 |
| lactate_x_obs | secondaire | 0.574 | 0.827 | 0.489 | 1.101 | 0.704 | 0.636 | 0.325 | 0.858 |
| aki_x_only | contraste | 0.307 | 1.638 | -4.229 | 6.686 | -0.155 | -0.293 | 0.196 | 0.029 |
| aki_x_obs | secondaire | 0.297 | 2.994 | 0.007 | 6.218 |  |  |  | 0.029 |

Lactate, split train, par tiers de dosage :

| tiers | hopitaux | redoses | prevalence_neg | prevalence_cc |
|---|---|---|---|---|
| bas | 20 | 0.0666 | 0.0103 | 0.1552 |
| moyen | 20 | 0.1565 | 0.0220 | 0.1406 |
| haut | 20 | 0.2911 | 0.0452 | 0.1554 |

## Régimes 1 et 2 — |CITL| moyen sur la moitié déploiement

k = 0 : sans label ; k = −1 : nombre d'événements (régime 1).

**mortalite_x_only** (a priori S_all)

| méthode \ k | -1 | 0 | 25 | 50 | 100 | 200 |
|---|---|---|---|---|---|---|
| EB_descripteurs |  |  | 0.321 | 0.321 | 0.306 | 0.231 |
| EB_global |  |  | 0.365 | 0.360 | 0.333 | 0.250 |
| agrege_EB_descripteurs | 0.315 |  |  |  |  |  |
| agrege_local | 0.398 |  |  |  |  |  |
| aucune |  | 0.374 |  |  |  |  |
| descripteurs |  | 0.322 |  |  |  |  |
| local |  |  | 0.696 | 0.563 | 0.438 | 0.309 |
| moyenne |  | 0.374 |  |  |  |  |
| retrecissement_fixe |  |  | 0.364 | 0.358 | 0.331 | 0.250 |

**lactate_x_only** (a priori S_mech)

| méthode \ k | -1 | 0 | 25 | 50 | 100 | 200 |
|---|---|---|---|---|---|---|
| EB_descripteurs |  |  | 0.758 | 0.745 | 0.633 | 0.581 |
| EB_global |  |  | 0.789 | 0.762 | 0.663 | 0.541 |
| agrege_EB_descripteurs | 0.725 |  |  |  |  |  |
| agrege_local | 0.814 |  |  |  |  |  |
| aucune |  | 0.816 |  |  |  |  |
| descripteurs |  | 0.782 |  |  |  |  |
| local |  |  | 1.023 | 0.841 | 0.793 | 0.579 |
| moyenne |  | 0.829 |  |  |  |  |
| retrecissement_fixe |  |  | 0.811 | 0.821 | 0.711 | 0.667 |

## Contrôles

| controle | ok |
|---|---|
| Protocole identique (hash) | True |
| Aucun hôpital du test verrouillé dans les prédictions, calibrations ou descripteurs | True |
| Chaque hôpital de développement apparaît une fois par tâche, dans le pli où il est tenu à l'écart | True |
| Prédictions moyennées sur toutes les seeds retenues, pour chaque séjour | True |
| Descripteurs inchangés quand on permute les labels (y_mortality, cr_peak, aki_cc, aki_neg, la_peak, hyper_cc, hyper_neg) | True |
| Split train des descripteurs cohérent avec le manifest (n_train) | True |
| Prédiction croisée : modifier les a_h du pli 0 ne change pas leur prédiction | True |
| APACHE IVa absent de S_all | True |
| Critères calculés sur la tâche principale attendue | True |
