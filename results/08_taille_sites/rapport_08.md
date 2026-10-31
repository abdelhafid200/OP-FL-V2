# Rapport 08 — taille des sites et pente de calibration (analyse exploratoire)

Généré le 2026-10-30 14:30 par `notebooks/08_taille_sites.ipynb`. Protocole `d92099ea7c11d517`. Agrégats uniquement.
**Statut : exploratoire, après l'ouverture du test verrouillé.** Plan d'analyse `plan_08.json` du 2026-10-30T14:29:19 (SHA-256 `870db4740ae0a7d2…`) ; module `opcal_size.py` `06381a89f46c1029…`.
Hôpitaux de développement uniquement ; des hôpitaux verrouillés, seuls les effectifs du manifest, le b publié du 07 et les â_h gelés (sans label) sont lus.

Effectifs médians : verrouillés train 163, évaluation 70 ; développement train 637,
évaluation 274. 50 tirages × 11 jeux de plis (protocole + 10 partitions du 06d).

## Pente b selon la taille

| configuration | b | b P5 | b P95 | part p_C1a ≤ 0,025 | lambda_eff | var_ahat | sejours_median | part plafonnée |
|---|---|---|---|---|---|---|---|---|
| complet | 0.953 | 0.792 | 1.107 | 1.000 | 1.000 | 0.047 | 910.500 | 0.000 |
| cibles ×1 | 0.947 | 0.572 | 1.425 | 0.955 | 1.000 | 0.047 | 702.500 | 0.000 |
| groupe_modele ×1 | 0.884 | 0.670 | 1.069 | 1.000 | 0.936 | 0.051 | 702.500 | 0.000 |
| descripteurs ×1 | 0.823 | 0.608 | 1.026 | 1.000 | 0.883 | 0.054 | 458.250 | 0.000 |
| tout ×1 | 0.826 | 0.441 | 1.319 | 0.896 | 0.832 | 0.057 | 240.500 | 0.000 |
| tout ×0.5 | 0.709 | 0.206 | 1.179 | 0.642 | 0.677 | 0.072 | 120.000 | 0.000 |
| tout ×2 | 0.914 | 0.645 | 1.197 | 0.998 | 0.933 | 0.052 | 449.000 | 0.139 |

## Hypothèse de taille : **non soutenue**

| critère | valeur | vrai |
|---|---|---|
| S1 | baisse simulée 0.128 ; baisse observée 0.413 (part 0.31) | False |
| S2 | b_07 = 0.540 ; P5–P95 sous « tout ×1 » = [0.441 ; 1.319] | True |
| S3 | baisse sous « cibles ×1 » = 0.007 (seuil 0.043) | True |

b_complet = 0.953 ; b_tout = 0.826 ; b_07 = 0.540 [0.252 ; 0.829].

**Lecture :** La petite taille des sites ne suffit pas à reproduire la baisse observée ; d'autres explications sont à examiner (domaine des hôpitaux verrouillés, modèle final, variabilité d'échantillonnage).

Dispersion des prédictions (sans label) :

| source | Var(â) |
|---|---|
| développement, taille complète (médiane) | 0.0472 |
| développement, taille des verrouillés (médiane) | 0.0573 |
| test verrouillé, â gelés (sans label) | 0.1083 |

## Signal et gain de calibration selon la taille

| configuration | gain_E0 | gain_E0 P5 | gain_E0 P95 | part gain_E0 > 0 | \|CITL\| E0 − OP-Cal | \|CITL\| E1 − OP-Cal | gain_theorique | part p_C1b ≤ 0,025 |
|---|---|---|---|---|---|---|---|---|
| complet | 0.0013 | 0.0008 | 0.0015 | 1.0000 | 0.0457 | 0.0519 | 0.0445 | 0.8182 |
| cibles ×1 | 0.0016 | 0.0004 | 0.0031 | 0.9800 | 0.0389 | 0.0396 | 0.0436 | 0.3582 |
| groupe_modele ×1 | 0.0011 | 0.0006 | 0.0015 | 1.0000 | 0.0417 | 0.0465 | 0.0395 | 0.4982 |
| descripteurs ×1 | 0.0009 | 0.0003 | 0.0015 | 0.9873 | 0.0352 | 0.0397 | 0.0345 | 0.2964 |
| tout ×1 | 0.0013 | -0.0001 | 0.0032 | 0.9400 | 0.0300 | 0.0316 | 0.0375 | 0.2000 |
| tout ×0.5 | 0.0010 | -0.0018 | 0.0030 | 0.7727 | 0.0103 | 0.0152 | 0.0295 | 0.0909 |
| tout ×2 | 0.0014 | 0.0005 | 0.0023 | 0.9982 | 0.0372 | 0.0381 | 0.0432 | 0.3945 |

## Correction de fiabilité : **non évaluée (hypothèse de taille non soutenue)**

Non évaluée.



Une correction retenue ici reste une **hypothèse** : elle n'est pas évaluée sur les 96 hôpitaux verrouillés (déjà utilisés) et demande une validation sur une autre source.

## Contrôles

| controle | ok |
|---|---|
| Descripteurs recalculés à taille complète identiques au 06b (44 colonnes) | True |
| Cibles a_h recalculées identiques à hospital_calibration | True |
| â_h par pli identiques à crossfit_prior (plis du protocole) | True |
| Aucun hôpital verrouillé dans les tableaux analysés | True |
| Plan d'analyse inchangé pendant l'exécution | True |
