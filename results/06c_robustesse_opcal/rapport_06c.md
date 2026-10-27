# Rapport 06c — robustesse d'OP-Cal, comparateurs publiés et spécification gelée

Généré le 2026-10-26 18:32 par `notebooks/06c_robustesse_opcal.ipynb`. Protocole `d92099ea7c11d517`. Agrégats uniquement.

## Verdict : GELÉE — spécification « gelée » (SHA-256 `302a9b448a1adcf4…`)

| code | question | mesure | seuil | rempli |
|---|---|---|---|---|
| R1 | R²_τ au-delà du hasard (permutation) | R²_τ = 0.595 ; p = 0.0020 | p < 0.05 | True |
| R2 | indépendant des plis du protocole | médiane sur 50 partitions = 0.384 [0.247 ; 0.561] ; LOHO = 0.535 | ≥ 0.25 | True |
| R3 | OP-Cal bat le meilleur comparateur publié (E0_aucune) | 0.0578 [0.0115 ; 0.1050] | IC bas > 0 | True |
| R3b | OP-Cal ajoute à EM | 1.5513 [0.9216 ; 2.2781] | IC bas > 0 | True |

## Comparateurs sans label

| tâche / méthode | référence | mean_abs_citl | median_abs_citl | R2_tau | mean_resid | diff_vs_ref | diff_IC_bas | diff_IC_haut |
|---|---|---|---|---|---|---|---|---|
| mortalite_x_only / E0_aucune | S_all | 0.304 | 0.270 | 0.000 | 0.027 | 0.058 | 0.011 | 0.105 |
| mortalite_x_only / E1_moyenne | S_all | 0.304 | 0.217 | -0.009 | -0.030 | 0.057 | 0.015 | 0.101 |
| mortalite_x_only / EM | S_all | 1.794 | 0.889 | -86.469 | 0.861 | 1.548 | 0.921 | 2.276 |
| mortalite_x_only / BBSE | S_all | 2.176 | 0.950 | -129.258 | 1.256 | 1.930 | 1.199 | 2.744 |
| mortalite_x_only / S_all | S_all | 0.246 | 0.191 | 0.595 | -0.022 | 0.000 | 0.000 | 0.000 |
| mortalite_x_only / S_all+EM | S_all | 0.243 | 0.180 | 0.625 | -0.024 | -0.003 | -0.010 | 0.003 |
| mortalite_x_obs / E0_aucune | S_all | 0.344 | 0.256 | 0.000 | 0.084 | 0.088 | 0.037 | 0.135 |
| mortalite_x_obs / E1_moyenne | S_all | 0.328 | 0.264 | -0.044 | -0.030 | 0.072 | 0.029 | 0.117 |
| mortalite_x_obs / EM | S_all | 1.516 | 0.625 | -61.335 | 0.666 | 1.261 | 0.683 | 1.952 |
| mortalite_x_obs / BBSE | S_all | 1.672 | 0.630 | -84.792 | 0.841 | 1.416 | 0.772 | 2.175 |
| mortalite_x_obs / S_all | S_all | 0.256 | 0.169 | 0.394 | -0.017 | 0.000 | 0.000 | 0.000 |
| mortalite_x_obs / S_all+EM | S_all | 0.257 | 0.167 | 0.388 | -0.019 | 0.001 | -0.004 | 0.008 |
| mortalite_grud / E0_aucune | S_all | 0.356 | 0.288 | 0.000 | 0.062 | 0.109 | 0.056 | 0.159 |
| mortalite_grud / E1_moyenne | S_all | 0.350 | 0.279 | -0.047 | -0.030 | 0.103 | 0.055 | 0.150 |
| mortalite_grud / EM | S_all | 1.546 | 0.665 | -59.544 | 0.692 | 1.299 | 0.700 | 1.978 |
| mortalite_grud / BBSE | S_all | 1.709 | 0.718 | -65.533 | 0.877 | 1.462 | 0.813 | 2.214 |
| mortalite_grud / S_all | S_all | 0.247 | 0.173 | 0.589 | -0.020 | 0.000 | 0.000 | 0.000 |
| mortalite_grud / S_all+EM | S_all | 0.249 | 0.189 | 0.579 | -0.021 | 0.002 | -0.005 | 0.009 |
| lactate_x_only / E0_aucune | S_mech_fixe | 0.841 | 0.710 | 0.000 | 0.075 | 0.121 | -0.032 | 0.273 |
| lactate_x_only / E1_moyenne | S_mech_fixe | 0.825 | 0.752 | -0.118 | -0.204 | 0.105 | -0.044 | 0.262 |
| lactate_x_only / EM | S_mech_fixe | 3.012 | 1.458 | -21.260 | 1.906 | 2.292 | 1.559 | 3.091 |
| lactate_x_only / BBSE | S_mech_fixe | 3.350 | 1.456 | -22.539 | 2.298 | 2.630 | 1.871 | 3.479 |
| lactate_x_only / S_all | S_mech_fixe | 0.743 | 0.641 | 0.292 | -0.264 | 0.023 | -0.096 | 0.148 |
| lactate_x_only / S_all+EM | S_mech_fixe | 0.746 | 0.644 | 0.279 | -0.269 | 0.026 | -0.094 | 0.151 |
| lactate_x_only / S_mech_fixe | S_mech_fixe | 0.720 | 0.675 | 0.332 | -0.078 | 0.000 | 0.000 | 0.000 |
| lactate_x_only / S_mech | S_mech_fixe | 0.692 | 0.680 | 0.264 | -0.124 | -0.028 | -0.089 | 0.036 |
| lactate_x_obs / E0_aucune | S_mech_fixe | 0.728 | 0.718 | 0.000 | 0.096 | 0.124 | -0.031 | 0.263 |
| lactate_x_obs / E1_moyenne | S_mech_fixe | 0.728 | 0.539 | -0.092 | -0.242 | 0.124 | -0.012 | 0.266 |
| lactate_x_obs / EM | S_mech_fixe | 2.688 | 1.097 | -37.226 | 1.750 | 2.083 | 1.356 | 2.884 |
| lactate_x_obs / BBSE | S_mech_fixe | 2.300 | 1.036 | -33.381 | 1.477 | 1.695 | 1.020 | 2.502 |
| lactate_x_obs / S_all | S_mech_fixe | 0.678 | 0.627 | 0.325 | -0.252 | 0.073 | -0.027 | 0.176 |
| lactate_x_obs / S_all+EM | S_mech_fixe | 0.679 | 0.614 | 0.323 | -0.255 | 0.074 | -0.028 | 0.178 |
| lactate_x_obs / S_mech_fixe | S_mech_fixe | 0.604 | 0.553 | 0.704 | -0.101 | 0.000 | 0.000 | 0.000 |
| lactate_x_obs / S_mech | S_mech_fixe | 0.583 | 0.482 | 0.636 | -0.157 | -0.021 | -0.076 | 0.033 |
| aki_x_only / E0_aucune | S_mech_fixe | 0.432 | 0.371 | 0.000 | -0.044 | 0.002 | -0.021 | 0.025 |
| aki_x_only / E1_moyenne | S_mech_fixe | 0.439 | 0.327 | -0.177 | -0.125 | 0.008 | 0.001 | 0.015 |
| aki_x_only / EM | S_mech_fixe | 5.169 | 5.588 | -370.951 | 3.223 | 4.739 | 3.902 | 5.594 |
| aki_x_only / BBSE | S_mech_fixe | 5.845 | 7.817 | -567.567 | 3.119 | 5.414 | 4.478 | 6.330 |
| aki_x_only / S_all | S_mech_fixe | 0.448 | 0.362 | 0.196 | -0.166 | 0.017 | -0.023 | 0.057 |
| aki_x_only / S_all+EM | S_mech_fixe | 0.449 | 0.355 | 0.173 | -0.166 | 0.019 | -0.022 | 0.059 |
| aki_x_only / S_mech_fixe | S_mech_fixe | 0.431 | 0.330 | -0.155 | -0.124 | 0.000 | 0.000 | 0.000 |
| aki_x_only / S_mech | S_mech_fixe | 0.433 | 0.330 | -0.293 | -0.128 | 0.002 | -0.010 | 0.013 |

## Permutation

| tâche / ensemble | permutations | R2_tau_observe | nul_mediane | nul_q95 | p_valeur |
|---|---|---|---|---|---|
| mortalite_x_only / S_all | 500 | 0.595 | -0.019 | 0.034 | 0.002 |
| mortalite_grud / S_all | 200 | 0.589 | -0.062 | -0.031 | 0.005 |
| mortalite_x_obs / S_all | 200 | 0.394 | -0.065 | -0.028 | 0.005 |
| lactate_x_only / S_mech_fixe | 200 | 0.332 | -1.454 | -0.643 | 0.005 |

## Partitions aléatoires et leave-one-hospital-out

| tâche / ensemble | R2_tau_protocole | partitions_mediane | partitions_q05 | partitions_q95 | part_R2_ge_seuil | LOHO_R2_tau | LOHO_mean_abs_citl |
|---|---|---|---|---|---|---|---|
| mortalite_x_only / S_all | 0.595 | 0.384 | 0.247 | 0.561 | 0.940 | 0.535 | 0.247 |
| mortalite_grud / S_all | 0.589 | 0.431 | 0.297 | 0.579 | 1.000 | 0.594 | 0.237 |
| mortalite_x_obs / S_all | 0.394 | 0.227 | 0.088 | 0.397 | 0.440 | 0.387 | 0.253 |
| lactate_x_only / S_mech_fixe | 0.332 | 0.372 | 0.307 | 0.415 | 1.000 | 0.370 | 0.715 |

## Ablation

| tâche / ensemble | descripteurs | R2_tau | delta_vs_S_all | mean_abs_citl |
|---|---|---|---|---|
| mortalite_x_only / S_all | 45 | 0.595 | 0.000 | 0.246 |
| mortalite_x_only / S_all − obs | 33 | 0.020 | -0.575 | 0.308 |
| mortalite_x_only / S_all − case | 22 | 0.394 | -0.201 | 0.285 |
| mortalite_x_only / S_all − struct | 37 | 0.392 | -0.202 | 0.255 |
| mortalite_x_only / S_all − model | 43 | 0.429 | -0.166 | 0.268 |
| mortalite_x_only / obs + case | 35 | 0.314 | -0.280 | 0.265 |
| mortalite_x_only / obs + struct | 20 | 0.354 | -0.241 | 0.295 |
| mortalite_x_only / obs + model | 14 | 0.296 | -0.299 | 0.295 |
| mortalite_x_only / case + struct | 31 | -0.018 | -0.613 | 0.304 |
| mortalite_x_only / case + model | 25 | -0.017 | -0.611 | 0.302 |
| mortalite_x_only / struct + model | 10 | 0.097 | -0.498 | 0.304 |
| mortalite_x_only / S_all − exclus (gelé) | 44 | 0.608 | 0.013 | 0.244 |
| mortalite_grud / S_all | 45 | 0.589 | 0.000 | 0.247 |
| mortalite_grud / S_all − obs | 33 | 0.151 | -0.438 | 0.322 |
| mortalite_grud / S_all − case | 22 | 0.279 | -0.310 | 0.310 |
| mortalite_grud / S_all − struct | 37 | 0.261 | -0.327 | 0.285 |
| mortalite_grud / S_all − model | 43 | 0.367 | -0.222 | 0.286 |
| mortalite_grud / obs + case | 35 | 0.165 | -0.424 | 0.300 |
| mortalite_grud / obs + struct | 20 | 0.183 | -0.406 | 0.328 |
| mortalite_grud / obs + model | 14 | 0.142 | -0.447 | 0.329 |
| mortalite_grud / case + struct | 31 | 0.024 | -0.565 | 0.335 |
| mortalite_grud / case + model | 25 | -0.037 | -0.626 | 0.341 |
| mortalite_grud / struct + model | 10 | 0.099 | -0.490 | 0.325 |
| mortalite_grud / S_all − exclus (gelé) | 44 | 0.601 | 0.012 | 0.245 |

## Transfert du méta-modèle entre modèles

Corrélation des a_h entre modèles :

|  | mortalite_x_only | mortalite_x_obs | mortalite_grud |
|---|---|---|---|
| mortalite_x_only | 1.000 | 0.912 | 0.916 |
| mortalite_x_obs | 0.912 | 1.000 | 0.975 |
| mortalite_grud | 0.916 | 0.975 | 1.000 |

| source / cible | R2_tau | mean_abs_citl | mean_resid |
|---|---|---|---|
| mortalite_x_only / mortalite_x_only | 0.595 | 0.246 | -0.022 |
| mortalite_x_only / mortalite_x_obs | 0.417 | 0.262 | 0.019 |
| mortalite_x_only / mortalite_grud | 0.450 | 0.280 | 0.004 |
| mortalite_x_obs / mortalite_x_only | 0.496 | 0.243 | -0.055 |
| mortalite_x_obs / mortalite_x_obs | 0.394 | 0.256 | -0.017 |
| mortalite_x_obs / mortalite_grud | 0.475 | 0.263 | -0.031 |
| mortalite_grud / mortalite_x_only | 0.574 | 0.236 | -0.044 |
| mortalite_grud / mortalite_x_obs | 0.514 | 0.241 | -0.007 |
| mortalite_grud / mortalite_grud | 0.589 | 0.247 | -0.020 |

## Spécification gelée

44 descripteurs ; exclus par construction : log_size ; comparateur publié retenu : E0_aucune ; k confirmatoire = 25.

## Contrôles

| controle | ok |
|---|---|
| Protocole identique (hash) | True |
| R²_τ principal du 06b reproduit à l'identique | True |
| Aucun hôpital verrouillé dans les cibles, descripteurs, sources ou comparateurs | True |
| Source du pli f = hôpitaux d'entraînement du pli f uniquement | True |
| EM et BBSE inchangés quand on permute les labels des hôpitaux tenus à l'écart | True |
| EM et BBSE retrouvent la prévalence sous un décalage de labels exact (simulation) | True |
| Spécification gelée : descripteurs exclus et APACHE absents | True |
| Test verrouillé : seuls hospitalid, role, n_val et n_test du manifest ont été lus | True |
