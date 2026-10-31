# Rapport 09 — domaine des hôpitaux verrouillés et dispersion des prédictions (descriptif, sans label)

Généré le 2026-10-31 10:52. Protocole `d92099ea7c11d517`. Plan `plan_09.json` du 2026-10-31T10:52:46 (`b48ac5129f32b13c…`).
**Exploratoire et descriptif.** Des hôpitaux verrouillés, seuls les fichiers gelés en phase A du 07 sont lus (descripteurs, lp sans label, â_h).

Var(â) : développement (modèle final, en échantillon) 0.0714 ; verrouillés 0.1083 (rapport 1.52).

## Quel groupe porte l'excès de dispersion ?

|  | développement Var(c_g) | développement Cov(c_g, â) | verrouillés Var(c_g) | verrouillés Cov(c_g, â) | excès Δ Cov(c_g, â) | excès part de l'excès |
|---|---|---|---|---|---|---|
| case-mix | 0.0152 | 0.0123 | 0.0375 | 0.0372 | 0.0249 | 0.6751 |
| observation | 0.0353 | 0.0386 | 0.0440 | 0.0505 | 0.0119 | 0.3235 |
| modèle | 0.0110 | 0.0086 | 0.0183 | 0.0138 | 0.0052 | 0.1399 |
| types d'unité | 0.0029 | 0.0017 | 0.0002 | -0.0000 | -0.0017 | -0.0461 |
| structure | 0.0108 | 0.0102 | 0.0137 | 0.0068 | -0.0034 | -0.0923 |
| total | 0.0753 | 0.0714 | 0.1137 | 0.1083 | 0.0369 | 1.0000 |

Descripteurs dont la contribution augmente le plus :

|  | groupe | Cov dév. | Cov verrouillés | Δ |
|---|---|---|---|---|
| dx_ami | case-mix | 0.0017 | 0.0149 | 0.0132 |
| test_rate_creatinine | observation | 0.0006 | 0.0132 | 0.0126 |
| dx_overdose | case-mix | 0.0008 | 0.0054 | 0.0046 |
| mean_lp | modèle | 0.0003 | 0.0046 | 0.0042 |
| intensity_creatinine | observation | 0.0012 | 0.0046 | 0.0035 |
| dx_arrest | case-mix | 0.0055 | 0.0088 | 0.0033 |
| dx_gi_bleed | case-mix | 0.0007 | 0.0038 | 0.0031 |
| cov_urine | observation | 0.0017 | 0.0037 | 0.0020 |
| dx_chf | case-mix | -0.0004 | 0.0010 | 0.0014 |
| region_west | structure | 0.0010 | 0.0020 | 0.0010 |

## Domaine du développement

| lecture | valeur | vrai |
|---|---|---|
| E2 | 40% des verrouillés hors domaine (D² > 73.6, P95 leave-one-out du dév. ; attendu ≈ 5 %) | True |
| E3 | Var(â) verrouillés dans le domaine 0.0700 ; hors domaine 0.1371 ; développement 0.0714 | True |

Corrélation de Spearman entre D² et |â − moyenne| chez les verrouillés : 0.03.

Parts hors plage [min ; max] du développement, par groupe :

| groupe | part hors plage | \|z\| moyen verrouillés |
|---|---|---|
| case-mix | 0.115 | 1.178 |
| modèle | 0.089 | 1.065 |
| observation | 0.083 | 0.940 |
| structure | 0.039 | 0.890 |
| types d'unité | 0.019 | 0.717 |

Descripteurs les plus souvent hors plage :

|  | groupe | part hors plage | \|z\| moyen verrouillés |
|---|---|---|---|
| cov_invasive_bp | observation | 0.396 | 1.287 |
| female_share | case-mix | 0.323 | 1.489 |
| src_or | case-mix | 0.281 | 1.157 |
| beds_cat | structure | 0.271 | 1.801 |
| dx_arrest | case-mix | 0.260 | 1.303 |
| dx_respiratory | case-mix | 0.219 | 1.740 |
| src_ed | case-mix | 0.167 | 1.215 |
| src_direct | case-mix | 0.156 | 0.745 |
| dx_chf | case-mix | 0.146 | 1.330 |
| dx_overdose | case-mix | 0.135 | 1.470 |
| dx_dka | case-mix | 0.125 | 1.678 |
| cov_urine | observation | 0.125 | 0.865 |

## Lecture : **extrapolation compatible**

Groupe portant le plus l'excès de dispersion : **case-mix**. Il s'agit d'une description compatible ou non avec une
extrapolation du méta-modèle, pas d'une démonstration causale ; une dispersion plus forte peut aussi refléter une hétérogénéité réelle.

## Contrôles

| controle | ok |
|---|---|
| â_h verrouillés reproduits à l'identique (phase A du 07) | True |
| Décomposition exacte : μ + Σ contributions = predict() | True |
| Aucun label ni cible de test verrouillé lu (fichiers de phase A uniquement, sans colonne y) | True |
| Plan inchangé pendant l'exécution | True |
