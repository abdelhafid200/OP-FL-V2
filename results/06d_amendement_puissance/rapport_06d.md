# Rapport 06d (version 2) — puissance du test verrouillé et amendement 1

Généré le 2026-10-27 15:42 par `notebooks/06d_amendement_puissance.ipynb`. Protocole `d92099ea7c11d517`. Agrégats uniquement.

**Amendement 1 : statut « proposé (à valider avant dépôt) »** — SHA-256 `7b74d3fa394112a8e0741a1f931ab6e75506baea3be71ba8484c6549c6e7e795`.
Spécification gelée inchangée — SHA-256 `302a9b448a1adcf481802ce6827e95e8c9afb623c3b7cf39ac3ca9f9eead25ae`.

**Motif :** Puissance insuffisante du C1 gelé : 0.35 sous les estimations du développement (variance d'échantillonnage médiane de a_h ≈ 0.169 (environ 7 décès attendus par hôpital verrouillé) contre τ² ≈ 0.081 entre hôpitaux de développement). L'amendement précise aussi l'estimand, la portée de b > 1/2, les comparateurs et le contrôle de la multiplicité.

## Pente de calibration des sites (développement, 44 descripteurs gelés)

| schéma | b | b_IC_bas | b_IC_haut | alpha | p_C1a | p_C1b | R2_tau | var_ahat |
|---|---|---|---|---|---|---|---|---|
| plis du protocole | 1.162 | 0.772 | 1.552 | 0.055 | 0.000 | 0.001 | 0.608 | 0.042 |
| leave-one-hospital-out | 0.968 | 0.628 | 1.309 | 0.057 | 0.000 | 0.004 | 0.556 | 0.057 |
| 50 partitions (médiane) | 0.916 | 0.756 | 1.085 | 0.058 | 0.000 | 0.024 | 0.399 | 0.047 |

Gain de log-vraisemblance par patient (développement) :

| contre | gain_par_patient | IC_bas | IC_haut | p_unilateral |
|---|---|---|---|---|
| E0 | 0.00162 | 0.00054 | 0.00286 | 0.00100 |
| E1 | 0.00154 | 0.00060 | 0.00271 | 0.00050 |

Lactate (développement) : γ = 0.928 [0.516 ; 1.346] ; test exact de permutation p = 0.0180.

## Puissance (96 hôpitaux verrouillés, médiane 70 patients d'évaluation ; procédure graphique)

Var(â) = 0.0470 ; τ² du développement = 0.0812 ; v_h médiane ≈ 0.169 ; k = 25 pour C3 ; 500 réplications par scénario (500 pour C4).
Les colonnes « _confirme » correspondent à la procédure complète ; « _seul » au test isolé à 2,5 %.

| scénario | b | tau2 | C1_gele | C3_gele | C1a_confirme | C4_confirme | C1b_confirme | C2_confirme | C1a_seul | C1b_seul | C2_seul | C4_seul | b_estime_median | largeur_IC_mediane |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b = 0,8 | 0.800 | 0.081 | 0.188 | 0.134 | 0.892 | 0.970 | 0.184 | 0.162 | 0.892 | 0.186 | 0.248 | 0.990 | 0.770 | 0.930 |
| b = 1 | 1.000 | 0.081 | 0.420 | 0.214 | 0.966 | 0.980 | 0.520 | 0.490 | 0.966 | 0.524 | 0.602 | 0.990 | 0.961 | 0.897 |
| b du dév. | 0.916 | 0.081 | 0.346 | 0.156 | 0.956 | 0.972 | 0.358 | 0.332 | 0.956 | 0.362 | 0.434 | 0.990 | 0.877 | 0.914 |
| b = 0,8 ; τ² = 0,12 | 0.800 | 0.120 | 0.158 | 0.072 | 0.792 | 0.986 | 0.158 | 0.140 | 0.792 | 0.160 | 0.190 | 0.990 | 0.741 | 1.017 |
| b = 1 ; τ² = 0,12 | 1.000 | 0.120 | 0.366 | 0.212 | 0.950 | 0.980 | 0.402 | 0.386 | 0.950 | 0.406 | 0.486 | 0.990 | 0.938 | 0.975 |
| b du dév. ; τ² = 0,12 | 0.916 | 0.120 | 0.322 | 0.174 | 0.916 | 0.982 | 0.334 | 0.310 | 0.916 | 0.336 | 0.410 | 0.990 | 0.877 | 0.986 |
| b du dév. ; γ = 0,5 | 0.916 | 0.081 | 0.346 | 0.156 | 0.942 | 0.608 | 0.324 | 0.300 | 0.956 | 0.362 | 0.434 | 0.704 | 0.877 | 0.914 |

## Risque global d'erreur de la procédure complète (cible ≤ 0,025)

| configuration nulle | hypothèses nulles vraies | erreur_globale | erreur_globale_IC_bas | erreur_globale_IC_haut |
|---|---|---|---|---|
| nul global : b = 0, γ = 0 | C1a, C1b, C2, C4 | 0.030 | 0.017 | 0.049 |
| b = 0 ; γ du dév. | C1a, C1b, C2 | 0.032 | 0.018 | 0.051 |
| b = 0,5 ; γ du dév. | C1b, C2 | 0.020 | 0.010 | 0.036 |
| b du dév. ; γ = 0 | C4 | 0.018 | 0.008 | 0.034 |

Erreur de type I de chaque test seul :

|  | taux | IC_bas | IC_haut |
|---|---|---|---|
| C1a sous b = 0 | 0.032 | 0.018 | 0.051 |
| C1b sous b = 0,5 | 0.020 | 0.010 | 0.036 |
| C2 sous b = 0,5 | 0.024 | 0.012 | 0.042 |
| C4 sous γ = 0 | 0.030 | 0.017 | 0.049 |

C4 (lactate) :

|  | C4 (p ≤ 2,5 %) | γ estimé médian | événements médians |
|---|---|---|---|
| γ = 0 | 0.030 | 0.008 | 104.000 |
| γ = 0,5 | 0.704 | 0.503 | 108.000 |
| γ du dév. | 0.990 | 0.936 | 115.000 |

## Journal d'accès aux fichiers

| groupe | fonction | lectures | hopitaux_verrouilles | colonnes_label | colonnes_demandees |
|---|---|---|---|---|---|
| ..\data_v1\clients\manifest.csv | read_csv | 1 | 96 |  | hospitalid, n_test, n_val, role |
| ..\data_v1\splits\protocol.json | read_text | 1 | 0 |  | toutes |
| ..\results\02_baselines\preds/*.parquet | read_parquet | 15 | 0 | y | toutes |
| ..\results\04_observation_label\stay_labels.parquet | read_parquet | 1 | 0 | aki_cc, aki_neg, cr_peak, hyper_cc, hyper_neg, la_peak, y_mortality | toutes |
| ..\results\05_raccourci_masquage\preds/*.parquet | read_parquet | 25 | 0 |  | toutes |
| ..\results\06b_faisabilite_opcal\descripteurs_site.csv | read_csv | 1 | 0 |  | toutes |
| ..\results\06c_robustesse_opcal\rapport_06c.md | read_text | 1 | 0 |  | toutes |
| ..\results\06c_robustesse_opcal\specification_gelee.json | read_text | 1 | 0 |  | toutes |

## Contrôles

| controle | ok |
|---|---|
| Protocole identique (hash) | True |
| Spécification gelée inchangée depuis le 06c (empreinte du rapport 06c) | True |
| Modules opcal_feas et opcal_robust identiques à ceux de la spécification | True |
| Prédiction gelée du développement reproduite (R²_τ 0.6077 ; 06c 0.6077) | True |
| Journal d'accès : aucun fichier lu ne contient à la fois une ligne d'hôpital verrouillé et une colonne de label | True |
| Journal d'accès : manifest lu uniquement avec hospitalid, role, n_val, n_test | True |
| Journal d'accès : aucun fichier hospital_*.npz ouvert | True |
| Journal d'accès : seul le manifest (colonnes d'effectifs) contient des lignes d'hôpitaux verrouillés | True |
| Erreur de type I de chaque test compatible avec ≤ 2,5 % (borne basse de l'IC de Monte Carlo) | True |
| Risque global de la procédure compatible avec ≤ 2,5 % sous les 4 configurations nulles | True |
| Amendement lié à l'empreinte complète de la spécification | True |
