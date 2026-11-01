# Rapport 10 — validation interne d'OP-Cal v2 (mortalité, 60 hôpitaux de développement)

Généré le 2026-10-31 21:35. Spécification 0.3 ; `opcal_gp.py` `052802442a27c1f7…` ; plan `plan_10.json` du 2026-10-31T21:24:54.
Aucune donnée des 96 hôpitaux verrouillés, hormis leurs effectifs du manifest (taille des sous-échantillons).

## Décision : **OP-Cal v2 NON RETENUE**

| condition | valeur | vraie |
|---|---|---|
| S3 : borne basse IC de D > 0 | D = 0.00017 [-0.00030 ; 0.00037] (meilleur comparateur : v1_borne) | False |
| S2 : D > 0 | D = 0.00000 [-0.00048 ; 0.00020] (meilleur comparateur : v1_borne) | True |
| S1 : borne basse IC de Δℓ(v2) − Δℓ(v1) > −0,0005 | -0.00023 [-0.00051 ; 0.00002] | False |

## S1 — plis par hôpital (taille complète)

|  | Δℓ (par patient) | Δℓ (moyenne par hôpital) | MSE débiaisé |
|---|---|---|---|
| E0 | 0.00000 | 0.00000 | 0.09856 |
| E1 | -0.00004 | -0.00005 | 0.10289 |
| v1 | 0.00122 | 0.00160 | 0.05925 |
| v1_retreci | 0.00102 | 0.00130 | 0.06666 |
| v1_borne | 0.00127 | 0.00166 | 0.05679 |
| v1_debruite | 0.00116 | 0.00152 | 0.06090 |
| GP_sans_debruitage | 0.00100 | 0.00132 | 0.06636 |
| v2 | 0.00099 | 0.00130 | 0.06707 |

## S2 — retrait d'un groupe de case-mix (taille complète)

|  | Δℓ (par patient) | Δℓ (moyenne par hôpital) | MSE débiaisé |
|---|---|---|---|
| E0 | 0.00000 | 0.00000 | 0.09856 |
| E1 | 0.00002 | 0.00001 | 0.10095 |
| v1 | 0.00020 | 0.00059 | 0.08862 |
| v1_retreci | -0.00009 | 0.00020 | 0.09987 |
| v1_borne | 0.00034 | 0.00074 | 0.08417 |
| v1_debruite | 0.00012 | 0.00056 | 0.09001 |
| GP_sans_debruitage | 0.00027 | 0.00059 | 0.08805 |
| v2 | 0.00035 | 0.00069 | 0.08553 |

## S3 — retrait d'un groupe de case-mix, taille des petits hôpitaux

|  | Δℓ (par patient) | Δℓ (moyenne par hôpital) | MSE débiaisé |
|---|---|---|---|
| E0 | 0.00000 | 0.00000 | 0.10208 |
| E1 | 0.00002 | 0.00001 | 0.11178 |
| v1 | 0.00034 | 0.00033 | 0.10973 |
| v1_retreci | -0.00004 | -0.00004 | 0.12106 |
| v1_borne | 0.00055 | 0.00054 | 0.10086 |
| v1_debruite | 0.00063 | 0.00062 | 0.09701 |
| GP_sans_debruitage | 0.00049 | 0.00048 | 0.10299 |
| v2 | 0.00072 | 0.00072 | 0.09359 |

Δℓ : gain de log-vraisemblance par patient contre E0 (une observation par hôpital). Le MSE débiaisé n'a de sens qu'à taille complète (sites ≥ 10 événements).

## Diagnostics d'estimation

| schema | plis | gp_non_converge | gp_aux_bornes | kappa_median | tau2_med | s2L_med | s2R_med | ellR_med |
|---|---|---|---|---|---|---|---|---|
| S1 | 55 | 0 | 0 | 0.9000 | 0.0130 | 0.5335 | 0.0226 | 4.8214 |
| S2/S3 | 50 | 0 | 0 | 0.9000 | 0.0122 | 0.5896 | 0.0232 | 4.9366 |

## Contrôles

| controle | ok |
|---|---|
| Descripteurs recalculés identiques au 06b | True |
| Aucun hôpital verrouillé analysé | True |
| Module opcal_gp inchangé pendant l'exécution | True |
