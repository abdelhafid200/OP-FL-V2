# OP-FL v2 — Observation relative au site (eICU-CRD)

Apprentissage fédéré sur dossiers de réanimation, **1 client = 1 hôpital réel**, avec un canal d'observation
*relatif au site* : ce qui se transporte d'un hôpital à l'autre n'est pas « l'examen a été fait », mais « l'examen a
été fait plus (ou moins) que d'habitude dans cet hôpital, pour un patient comparable ».

## Documentation

| Fichier | Contenu |
|---|---|
| `CLAUDE.md` | résumé opérationnel : question, architecture, règles inviolables, conventions, état d'avancement |
| `docs/CONTEXTE_PROJET.md` | historique (v1), diagnostic, corrections des données, chiffres clés, journal des décisions |
| `docs/02_baselines.md` | expérience 02 : plan, critères Go / No-Go pré-enregistrés, résultats |
| `data_v1/DATA_CARD.md` | fiche de données (générée par le notebook 01) |

## État d'avancement

| # | Notebook | Statut | Résultat clé |
|---|---|---|---|
| 01 | `01_donnees_v1.ipynb` | ✅ terminé (20/10/2026) | 92 944 séjours, 157 hôpitaux, protocole figé `bfdd2cb8c54b2e72`, 19 contrôles OK |
| 02 | `02_baselines.ipynb` | 📝 écrit, à exécuter | test de H1 (Go / No-Go) |
| 03 | niveau 2 : masque centré par site | à faire | — |
| 04 | E0 refait (information mutuelle + permutation) | à faire | — |
| 05 | niveau 3 (propension) + semi-synthétique | à faire | — |
| 06 | AKI, calibration, baselines complètes, test verrouillé | à faire | — |

## Structure

```
OP-FL-v2/
├── README.md, CLAUDE.md
├── docs/                       contexte, journal des décisions, une fiche par expérience
├── notebooks/
│   ├── 01_donnees_v1.ipynb     données V1.1 (une cellule par étape)
│   └── 02_baselines.ipynb      baselines fédérées, test de H1
├── src/
│   ├── opfl_data.py            chargement (écrit par l'étape 11 du notebook 01 : ne pas modifier à la main)
│   ├── opfl_models.py          modèles de l'échelle d'ablation
│   ├── opfl_federated.py       chargement d'un pli, FedAvg, prédiction
│   └── opfl_metrics.py         métriques, bootstrap apparié, méta-analyse
├── data_v1/                    créé par le notebook 01
│   ├── interim/  splits/  clients/  normalizers/  reports/
│   ├── features.json
│   └── DATA_CARD.md
└── results/
    └── 02_baselines/           prédictions par run, métriques, analyse H1, figure
```

## Installation

Paquets : `numpy`, `pandas`, `pyarrow`, `jupyter` (notebook 01) ; en plus pour les expériences :
`torch` (CPU), `scikit-learn`, `scipy`, `matplotlib`.

```
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install scikit-learn scipy matplotlib
```

## Utilisation dans un notebook

```python
import sys; sys.path.insert(0, "../src")
import opfl_data as od, opfl_federated as ofl
DATA = "../data_v1"
norm = od.load_normalizer(DATA, fold=0)                # ou fold="final" pour le test verrouillé
train_h, heldout_h = od.fold_hospitals(DATA, 0)
client = od.load_client(DATA, train_h[0], norm, mode="global")   # ou mode="local"
train = od.select(client, "train")

fd = ofl.load_fold(DATA, 0)    # pli entier : clients, val, test (hôpitaux d'entraînement), heldout
```

## Protocole (figé)

| Ensemble | Hôpitaux | Usage |
|---|---|---|
| Développement | 61 hôpitaux ≥ 500 séjours, 5 plis *leave-hospitals-out* | entraînement fédéré, sélection de modèle |
| Test final verrouillé | 96 hôpitaux de 100 à 499 séjours | **évalué une seule fois**, à la fin |

Dans chaque hôpital : split par patient 70 / 10 / 20 stratifié sur la mortalité.
Pour un hôpital tenu à l'écart : `train` = adaptation sans label, `val + test` = évaluation.
Les corrections par rapport à l'ancienne implémentation sont détaillées dans `docs/CONTEXTE_PROJET.md` § 3.

## Résultats

*Aucun résultat d'expérience pour l'instant.* Chaque expérience terminée ajoute ici son résultat clé
et renvoie vers sa fiche dans `docs/`.
