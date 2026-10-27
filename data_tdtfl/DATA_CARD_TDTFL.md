# Fiche de données — TDT-FL, protocole 1.1 (eICU-CRD)

Générée le 2026-10-26 14:03 par `notebooks/02_protocole_tdtfl.ipynb`. Hash du protocole : `0f91266774f979f1`.
Source : sorties du notebook 01 d'OP-FL (`..\..\data_v1`), lues sans modification.

## Hôpitaux
Éligibles : au moins 20 décès sur 2014-2015 ; strates par nombre de décès {'petit': (20, 59), 'moyen': (60, 149), 'grand': (150, None)}.
Réglage : 20% de chaque strate (cibles de réglage des hyperparamètres, sources pour tous). Évaluation : les autres.

| stratum | hopitaux | sejours | deces | reglage | evaluation | temporel |
|---|---|---|---|---|---|---|
| petit | 50 | 20595 | 1705 | 10 | 40 | 39 |
| moyen | 40 | 34900 | 3399 | 8 | 32 | 38 |
| grand | 11 | 24378 | 2511 | 2 | 9 | 11 |

Séjours retenus : 79873 ; décès : 7615 ; mortalité : 9.53%.

## Phénotypes (`apacheadmissiondx`, texte entre parenthèses retiré, priorité dans l'ordre)
| phenotype | sejours | deces | mortalite | operatoire |
|---|---|---|---|---|
| sepsis | 10323 | 1789 | 0.173 | 0.004 |
| cardiovasculaire | 25633 | 2177 | 0.085 | 0.348 |
| neurologique | 14501 | 1250 | 0.086 | 0.186 |
| respiratoire | 10252 | 1310 | 0.128 | 0.109 |
| autre | 19164 | 1089 | 0.057 | 0.256 |

Axe secondaire : opératoire si `unitadmitsource` ∈ ['Operating Room', 'PACU', 'Recovery Room']. Correspondance complète : `phenotype_map.csv`.

## Découpages (10 graines, stratifiés sur décès × phénotype, allocation par blocs)
- R1 statique : train / D / test = 60 / 20 / 20 dans chaque hôpital ; 5 plis internes du train.
- R2 temporel : hôpitaux à ≥ 10 décès par an ; 2014 -> train14 / D14 / test14 (60/20/20), 2015 -> D15 / test15 (50/50).
- R3 hôpital non vu : test = test R1 ; budgets [50, 100, 200] pris pour moitié dans un réservoir de calibration et pour moitié dans un réservoir D, dans un ordre d'acquisition stratifié ; fédération = hôpitaux hors du pli R3 de la cible (5 plis).
- R4 dérive simulée : lots tirés des réservoirs D et test de R1 (voir la spécification).

### Décès par hôpital dans D et le test (R1, moyenne sur les graines)
| stratum | hopitaux | deces_D_moyen | deces_D_min | deces_D_max | deces_test_moyen |
|---|---|---|---|---|---|
| petit | 50 | 6.8 | 3.7 | 11.6 | 6.8 |
| moyen | 40 | 17.0 | 11.8 | 30.1 | 17.0 |
| grand | 11 | 45.8 | 30.2 | 65.0 | 45.6 |

### Faisabilité de E2 (couples hôpital d'évaluation × phénotype)
| strate | couples | >= 5 décès dans D | >= 10 décès dans D |
|---|---|---|---|
| petit | 200 | 1% | 0% |
| moyen | 160 | 21% | 0% |
| grand | 45 | 87% | 31% |

### Régime temporel (graine 0)
| stratum | hopitaux | train14 | D14 | test14 | D15 | test15 |
|---|---|---|---|---|---|---|
| petit | 39 | 11.3 | 3.6 | 3.8 | 8.4 | 8.8 |
| moyen | 38 | 26.1 | 8.8 | 8.9 | 21.2 | 20.9 |
| grand | 11 | 70.1 | 23.6 | 23.5 | 55.4 | 55.7 |

### Budgets R3
| strate | b = 50 | b = 100 | b = 200 | décès attendus dans D (b = 100) |
|---|---|---|---|---|
| petit | 100% | 100% | 88% | 4.6 |
| moyen | 100% | 100% | 100% | 5.4 |
| grand | 100% | 100% | 100% | 5.3 |

## Variables (225 colonnes : 149 continues, 76 binaires)
- 29 variables temporelles d'OP-FL (log1p pour les variables asymétriques) : moyenne, minimum, maximum, dernière valeur, nombre d'observations, observée ou non ; diurèse totale.
- Statiques : âge, taille, poids, sexe, indicateurs de valeur manquante. One-hot : 20 diagnostics + autre + manquant (vocabulaire des hôpitaux de réglage), phénotype, type d'unité, provenance.
- Normalisation globale au chargement (`src/tdtfl_data.py`), sur le split train de la fédération du régime ; valeur manquante = 0 après z-score.
- Disponibilité : variable observée chez ≥ 5% des séjours de l'hôpital. Une variable indisponible chez la source est remise à manquant chez la cible avant d'appliquer le modèle de la source.

| index | hopitaux_indisponibles |
|---|---|
| lactate | 9 |
| bicarbonate | 5 |
| total bilirubin | 2 |
| pH | 4 |
| paO2 | 5 |
| paCO2 | 6 |
| FiO2 | 7 |
| systemicsystolic | 6 |
| systemicdiastolic | 6 |
| systemicmean | 6 |
| GCS Total | 18 |
| Eyes | 23 |
| Motor | 23 |
| Verbal | 23 |
| gcs_unable | 18 |
| urine_output | 4 |

## Usage des parties
- train : entraînement du modèle local ; recalibration de Platt des partenaires sur les patients de la cible.
- D : décisions uniquement (choix du partenaire, porte).
- test : mesure uniquement.
