# Fiche de données — OP-FL V1.1 (eICU-CRD)

Générée le 2026-10-21 11:46 par `notebooks/01_donnees_v1.ipynb`. Hash du protocole : `d92099ea7c11d517`.

## Cohorte
| Étape | Séjours | Patients | Hôpitaux |
|---|---|---|---|
| Séjours en unité (eICU) | 200859 | 139367 | 208 |
| 1re unité du séjour hospitalier | 158442 | 133492 | 208 |
| Âge >= 18 ans | 157883 | 132994 | 208 |
| Durée en unité >= 24 h | 110257 | 95823 | 208 |
| Statut de sortie connu | 109218 | 95012 | 207 |
| 1er séjour éligible de chaque patient | 95012 | 95012 | 207 |
| Hôpitaux >= 100 séjours | 93100 | 93100 | 158 |
| Labo de routine et monitorage disponibles (2 hôpitaux exclus) | 90734 | 90734 | 156 |

Hôpitaux exclus pour absence structurelle de laboratoire ou de monitorage (< 50% des séjours) :

| hospitalid | role | n_stays | cov_routine_lab_any | cov_heartrate |
|---|---|---|---|---|
| 246 | locked | 156 | 0.891 | 0.083 |
| 443 | dev | 2210 | 0.986 | 0.3 |

## Protocole
- Développement : hôpitaux >= 500 séjours, 5 plis leave-hospitals-out équilibrés en taille.
- Test final verrouillé : hôpitaux de 100 à 499 séjours, évalués une seule fois.
- Au sein de chaque hôpital : split par patient {'train': 0.7, 'val': 0.1, 'test': 0.2}, stratifié sur la mortalité, seed 42.
- Hôpital tenu à l'écart : split train = adaptation sans label ; val + test = évaluation.

| groupe | hopitaux | sejours |
|---|---|---|
| pli 0 | 12 | 12709 |
| pli 1 | 12 | 12689 |
| pli 2 | 12 | 13949 |
| pli 3 | 12 | 12888 |
| pli 4 | 12 | 13859 |
| test verrouillé | 96 | 24640 |

## Variables temporelles (fenêtre 0-24 h, pas horaire, T = 24)
| idx | name | block | group | log | couverture_moy | hopitaux_non_dispo |
|---|---|---|---|---|---|---|
| 0 | lactate | lab | bloodgas | True | 0.259 | 12 |
| 1 | creatinine | lab | routine | True | 0.915 | 0 |
| 2 | BUN | lab | routine | True | 0.913 | 0 |
| 3 | sodium | lab | routine | False | 0.916 | 0 |
| 4 | potassium | lab | routine | False | 0.916 | 0 |
| 5 | bicarbonate | lab | routine | False | 0.866 | 5 |
| 6 | glucose | lab | routine | True | 0.907 | 0 |
| 7 | WBC x 1000 | lab | routine | True | 0.878 | 0 |
| 8 | Hgb | lab | routine | False | 0.885 | 0 |
| 9 | Hct | lab | routine | False | 0.89 | 0 |
| 10 | platelets x 1000 | lab | routine | True | 0.868 | 0 |
| 11 | total bilirubin | lab | routine | True | 0.445 | 3 |
| 12 | pH | lab | bloodgas | False | 0.334 | 11 |
| 13 | paO2 | lab | bloodgas | False | 0.336 | 11 |
| 14 | paCO2 | lab | bloodgas | False | 0.332 | 12 |
| 15 | FiO2 | lab | bloodgas | False | 0.35 | 13 |
| 16 | heartrate | monitor | monitor | False | 0.988 | 0 |
| 17 | sao2 | monitor | monitor | False | 0.978 | 0 |
| 18 | respiration | monitor | monitor | False | 0.911 | 1 |
| 19 | systemicsystolic | monitor | monitor | False | 0.2 | 34 |
| 20 | systemicdiastolic | monitor | monitor | False | 0.2 | 34 |
| 21 | systemicmean | monitor | monitor | False | 0.2 | 34 |
| 22 | GCS Total | nursing | gcs | False | 0.626 | 26 |
| 23 | Eyes | nursing | gcs | False | 0.536 | 42 |
| 24 | Motor | nursing | gcs | False | 0.536 | 42 |
| 25 | Verbal | nursing | gcs | False | 0.535 | 42 |
| 26 | gcs_unable | nursing | gcs | False | 0.626 | 26 |
| 27 | temperature | nursing | temperature | False | 0.928 | 0 |
| 28 | urine_output | nursing | urine | True | 0.66 | 3 |

Température : couverture 94.7% (train, dév.) -> incluse : True.
`hopitaux_non_dispo` : nombre d'hôpitaux où la variable est observée chez moins de 5% des séjours (absence structurelle).

## Définitions
- `X_raw` : moyenne horaire des valeurs plausibles (somme pour la diurèse), NaN si absente.
- `C` : nombre d'événements d'observation dans l'heure (une saisie GCS « non évaluable » compte ; doublons °C/°F de température retirés).
- `M = C > 0`.
- `Delta` : heures depuis l'observation précédente strictement avant t ; t + 1 si jamais observée.
- `S` : âge, taille, poids, sexe + diagnostic d'admission (top-15 du pli + autre + manquant).
- `avail` : disponibilité de la variable dans l'hôpital (>= 5% des séjours du split train).
- Normalisation au chargement (`src/opfl_data.py`) : log1p pour ['BUN', 'WBC x 1000', 'creatinine', 'glucose', 'lactate', 'platelets x 1000', 'total bilirubin', 'urine_output'],
  z-score avec les statistiques du split train des hôpitaux d'entraînement du pli (mode global) ou de l'hôpital lui-même (mode local),
  puis forward-fill ; valeur jamais observée = 0.

## Labels
| role | sejours | mortalite | aki_evaluable | aki_taux | los_gt7 |
|---|---|---|---|---|---|
| dev | 66094 | 0.0937 | 0.8079 | 0.0365 | 0.1106 |
| locked | 24640 | 0.0823 | 0.7948 | 0.0323 | 0.0877 |

- Mortalité : décès hospitalier.
- AKI : pic de créatinine [24 h, 7 j] / minimum sur 24 h >= 2, défini si dosée aux deux périodes.
- APACHE IVa : référence clinique uniquement, jamais une entrée.

## Contrôle qualité
```
{
 "qc_lab": {
  "fio2_fraction_converted": 10644,
  "dropped_out_of_range": {
   "FiO2": 3075,
   "potassium": 21,
   "platelets x 1000": 6,
   "creatinine": 61,
   "lactate": 13,
   "bicarbonate": 3,
   "Hct": 7,
   "Hgb": 11,
   "glucose": 13,
   "paO2": 10,
   "sodium": 10,
   "WBC x 1000": 63,
   "paCO2": 12,
   "pH": 10,
   "total bilirubin": 5,
   "BUN": 2
  }
 },
 "qc_nursing": {
  "gcs_empty_dropped": 37863,
  "gcs_unable": 13965,
  "gcs_numeric": 1750117,
  "gcs_other_text_dropped": 0,
  "temperature_C_F_duplicates_removed": 826663,
  "dropped_out_of_range": {
   "temperature": 490
  },
  "temperature_names": {
   "Temperature (C)": 826842,
   "Temperature (F)": 826738,
   "Temperature Location": 474655
  }
 },
 "qc_urine": {
  "dropped_out_of_range": {
   "urine_output": 3397
  },
  "top_labels": {
   "Urine": 454145,
   "URINE CATHETER": 43010,
   "Foley cath": 2148,
   "Voided Amount": 1799,
   "Foley": 637,
   "SN Urine Output(ml)": 372,
   "foley": 251,
   "Urine Output-Foley": 225,
   "Urine, void:": 178,
   "Urine Output (mL)-Urethral Catheter": 142,
   "Urine Output (mL)-Urethral Catheter  ": 129,
   "Urine Output (mL)-Urethral Catheter ": 84,
   "Urine Output-foley": 72,
   "FOLEY": 58,
   "Suprapubic Urine Output": 45,
   "OR urine": 41,
   "unmeasured voids": 33,
   "Number of Incontinent Voids": 32,
   "Foley Cath": 31,
   "urine incontinence": 22,
   "Foley catheter": 18,
   "Urine Output-FOLEY": 8,
   "Urine Incontinence": 5,
   "incontinent urine": 4,
   "Urine Output-Urine Output": 1
  },
  "excluded_labels": {
   "Urine Count": 1708,
   "Urine Occurrence": 277,
   "Mixed Urine/Stool Volume": 220,
   "urine count": 19
  }
 },
 "qc_vital": {
  "dropped_out_of_range": {
   "heartrate": 2610,
   "sao2": 3206,
   "respiration": 176784,
   "systemicsystolic": 5802,
   "systemicdiastolic": 9106,
   "systemicmean": 27306,
   "temperature": 4970
  }
 }
}
```
