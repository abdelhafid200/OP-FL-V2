# Rapport 07 — confirmation d'OP-Cal sur le test verrouillé

Généré le 2026-10-28 13:45 par `notebooks/07_confirmation.ipynb`. Protocole `d92099ea7c11d517`. Agrégats uniquement.
Spécification `302a9b448a1adcf4…`, amendement 1 `cf4eceb83b8c6624…` (validé). Évaluation du 2026-10-28T13:44:34.

96 hôpitaux verrouillés ; mortalité : 7396 séjours, 608 décès ; hyperlactatémie : 4057 séjours, 68 événements.

## Critères confirmatoires (procédure graphique, unilatéral 2,5 %)

| critère | hypothèse et test | p unilatéral | rejetée |
|---|---|---|---|
| C1a | b > 0 (Knapp-Hartung) | 0.0002 | True |
| C4 | score efficace, permutation | 0.0010 | True |
| C1b | b > 0,5 (Knapp-Hartung) | 0.3910 | False |
| C2 | gain de log-vraisemblance vs E0, bootstrap | 0.4743 | False |

* C1 : b = 0.540 [0.252 ; 0.829] (Knapp-Hartung, 94 ddl) ; α = -0.069 ; R²_τ = 0.279 [-8.509 ; 1.000] ; bootstrap de b [0.232 ; 0.896].
* C2 : gain de log-vraisemblance par patient contre E0 = 0.00002 [-0.00221 ; 0.00215].
* C4 : γ = 0.775 [0.453 ; 1.195] ; l'IC contient 1 : True.

**Conclusions (formulation fixée par l'amendement 1) :**

* Le signal de calibration des sites se transporte (C1a).
* L'ampleur du gain reste incertaine sur ce jeu (C1b non rejeté).
* Mécanisme du dosage confirmé (C4).

## Descriptif — comparateurs (mortalité, x_only)

| méthode | \|CITL\| moyen | \|CITL\| médian | R2_tau | \|CITL\|(méthode) − \|CITL\|(OP-Cal) | IC_bas | IC_haut | gain log-vraisemblance OP-Cal vs méthode | gain_IC_bas | gain_IC_haut |
|---|---|---|---|---|---|---|---|---|---|
| E0 (aucune correction) | 0.4767 | 0.3690 | 0.0000 | -0.0145 | -0.0752 | 0.0441 | 0.0000 | -0.0022 | 0.0021 |
| E1 (constante du dév.) | 0.4999 | 0.3864 | 0.0000 | 0.0087 | -0.0500 | 0.0669 | 0.0006 | -0.0016 | 0.0027 |
| EM | 3.3049 | 1.6237 | -510.8057 | 2.8137 | 2.0869 | 3.4929 | 0.1617 | 0.1142 | 0.2127 |
| BBSE | 3.1244 | 1.5130 | -474.3036 | 2.6332 | 1.9364 | 3.3321 | 0.1466 | 0.1016 | 0.1961 |
| OP-Cal | 0.4912 | 0.3846 | 0.2788 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

GRU-D (S1) : b = 0.518 [0.271 ; 0.765] ; R²_τ = 0.061.
Lactate, terme mécanistique seul : |CITL| 1.282 (sans correction 0.774) ; R²_τ = nan.

C3 (k = 25, descriptif) :

| méthode | -1 | 0 | 25 |
|---|---|---|---|
| EB_descripteurs |  |  | 0.553 |
| EB_global |  |  | 0.580 |
| agrege_EB_descripteurs | 0.584 |  |  |
| agrege_local | 0.777 |  |  |
| aucune |  | 0.592 |  |
| descripteurs |  | 0.600 |  |
| local |  |  | 0.814 |
| moyenne |  | 0.609 |  |
| retrecissement_fixe |  |  | 0.580 |

Discrimination :

| jeu | AUROC poolée | AUROC médiane par hôpital | hôpitaux ≥ 5 décès |
|---|---|---|---|
| développement (plis, transfert) | 0.8467 | 0.8520 | 60 |
| test verrouillé (modèle final) | 0.8435 | 0.8499 | 57 |

## Note d'implémentation (avant l'ouverture des labels)

`site_descriptors` (gelé) ne crée que les colonnes des 6 types d'unité les plus fréquents parmi les hôpitaux qu'on lui passe. Pour les hôpitaux
verrouillés, les colonnes absentes (unit_neuro_icu) ont été calculées par leur nom, avec la même règle et le même
dénominateur. Le calcul est contrôlé sur le développement (identique au 06b). Cette correction a été faite en phase A, avant l'ouverture des labels (journal_07.json).

## Contrôles

| controle | ok |
|---|---|
| Labels et observation recalculés identiques au notebook 04 (hôpitaux de développement) | True |
| Descripteurs recalculés identiques au 06b (hôpitaux de développement) | True |
| Parts des 6 types d'unité gelés recalculées identiques au 06b (développement) | True |
| Décès de cohort_final identiques aux labels du notebook 02 | True |
| Pli final : 60 hôpitaux de développement à l'entraînement, 96 verrouillés en prédiction | True |
| Prédictions finales : chaque séjour verrouillé prédit par toutes les seeds | True |
| Fichiers d'entraînement : aucun label verrouillé (marqueur y = −1 pour le rôle transfer) | True |
| Prédictions gelées et empreintes enregistrées avant l'ouverture des labels | True |
| Empreintes des prédictions gelées inchangées depuis la phase A | True |
| Une seule ouverture des labels | True |
| τ² de C4 identique à l'amendement | True |
