# Rapport 06d — puissance du test verrouillé et amendement 1

Généré le 2026-10-27 10:54 par `notebooks/06d_amendement_puissance.ipynb`. Protocole `d92099ea7c11d517`. Agrégats uniquement.

**Amendement 1 : statut « proposé (à valider avant dépôt) »** — SHA-256 `a02997c2662a2fb725ea3baf4eee104afaabd6634e651cd4b20a62e36e268352`.
Spécification gelée inchangée — SHA-256 `302a9b448a1adcf481802ce6827e95e8c9afb623c3b7cf39ac3ca9f9eead25ae`.

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

## Puissance (vrais effectifs du test verrouillé : 96 hôpitaux, médiane 70 patients d'évaluation)

Paramètres : Var(â) = 0.0470 ; τ² du développement = 0.0812 ; variance d'échantillonnage médiane de a_h ≈ 0.169 ;
k = 25 pour C3 ; 500 réplications par scénario (150 pour C4).

**Motif de l'amendement :** Puissance insuffisante du C1 gelé : 0.31 sous les estimations du développement (variance d'échantillonnage médiane de a_h ≈ 0.169 (environ 7 décès attendus par hôpital verrouillé) contre τ² ≈ 0.081 entre hôpitaux de développement). Simulation sur les vrais effectifs, avec la procédure finale (tableau 'puissance'). L'amendement précise aussi l'estimand, le lien avec l'amélioration de la calibration (b > 1/2) et le contrôle de la multiplicité.

| scénario | b | tau2 | C1_gele | C3_gele | C1a_seul | C4_seul | famille1 | C1b_seul | C1b_confirme | C2_seul | C2_confirme | b_estime_median | largeur_IC_mediane |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nul : b = 0 | 0.000 | 0.081 | 0.000 | 0.006 | 0.024 | 0.047 | 0.002 | 0.000 | 0.000 | 0.000 | 0.000 | 0.008 | 0.981 |
| frontière C1b : b = 0,5 | 0.500 | 0.081 | 0.020 | 0.018 | 0.432 | 0.987 | 0.426 | 0.016 | 0.016 | 0.018 | 0.010 | 0.445 | 0.979 |
| b = 0,8 | 0.800 | 0.081 | 0.200 | 0.104 | 0.874 | 0.987 | 0.854 | 0.186 | 0.184 | 0.222 | 0.162 | 0.741 | 0.937 |
| b = 1 | 1.000 | 0.081 | 0.398 | 0.230 | 0.972 | 0.987 | 0.962 | 0.498 | 0.492 | 0.562 | 0.448 | 0.956 | 0.895 |
| b du dév. | 0.916 | 0.081 | 0.314 | 0.172 | 0.954 | 0.987 | 0.940 | 0.336 | 0.334 | 0.392 | 0.302 | 0.879 | 0.926 |
| b = 0,8 ; τ² = 0,12 | 0.800 | 0.120 | 0.158 | 0.112 | 0.818 | 0.987 | 0.810 | 0.174 | 0.172 | 0.240 | 0.160 | 0.760 | 1.003 |
| b = 1 ; τ² = 0,12 | 1.000 | 0.120 | 0.380 | 0.184 | 0.968 | 0.987 | 0.956 | 0.410 | 0.408 | 0.484 | 0.394 | 0.921 | 0.980 |
| b du dév. ; τ² = 0,12 | 0.916 | 0.120 | 0.270 | 0.152 | 0.934 | 0.987 | 0.918 | 0.288 | 0.284 | 0.358 | 0.254 | 0.853 | 0.996 |

C4 (lactate) :

|  | C4 (p ≤ 2,5 %) | γ estimé médian | événements médians |
|---|---|---|---|
| γ = 0 (nul) | 0.047 | -0.024 | 103.500 |
| γ = 0,5 | 0.727 | 0.457 | 107.000 |
| γ du dév. | 0.987 | 0.934 | 118.000 |

Erreur de type I (cible 0,025) : C1a sous b = 0 = 0.024, C1b sous b = 0,5 = 0.016, C4 sous γ = 0 = 0.047.

## Contrôles

| controle | ok |
|---|---|
| Protocole identique (hash) | True |
| Spécification gelée inchangée depuis le 06c (empreinte du rapport 06c) | True |
| Modules opcal_feas et opcal_robust identiques à ceux de la spécification | True |
| Prédiction gelée du développement reproduite (R²_τ 0.6077 ; 06c 0.6077) | True |
| Erreur de type I de C1a et C1b nominale (≤ 0,025 + 0.014) | True |
| Erreur de type I de C4 nominale (≤ 0,025 + 0.025) | True |
| Test verrouillé : seuls hospitalid, role, n_val et n_test du manifest ont été lus | True |
| Aucun hôpital verrouillé dans les cibles, descripteurs ou scores tirés pour la simulation | True |
| Amendement lié à l'empreinte complète de la spécification | True |
