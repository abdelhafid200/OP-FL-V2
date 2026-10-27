# OP-FL v2 — Contexte du projet pour Claude Code

Projet de thèse de doctorat. Objectif : un **article méthodologique** dans une revue indexée Clarivate / Scopus
(cibles : IEEE JBHI, Artificial Intelligence in Medicine, Computer Methods and Programs in Biomedicine ;
plan B : JAMIA, Journal of Biomedical Informatics, npj Digital Medicine).

Langue de travail : **français** (explications et commentaires en français, noms de variables en anglais).

**Répartition du travail** : Claude écrit le code, les fichiers et la documentation, et analyse les résultats
(sorties enregistrées dans les notebooks, CSV de `results/`). **L'utilisateur exécute tout sur sa machine** :
Claude n'exécute pas le code du projet.

Avant toute décision méthodologique, lire `docs/CONTEXTE_PROJET.md` (historique, anciens résultats,
diagnostic, journal des décisions). Les anciens rapports et l'ancien code sont dans `docs/archives/`
(à consulter, **ne pas réutiliser tel quel** : l'ancien prétraitement contenait des fuites et des bugs).

## Question de recherche
Apprentissage fédéré (FL) sur dossiers patients de réanimation (eICU-CRD v2.0), **1 client = 1 hôpital réel**.
Le processus d'observation (quels examens sont mesurés, quand, combien de fois) varie entre hôpitaux :
P_k(O | X, Y) dépend du site k, avec O = (M, Δ, C).
Hypothèse : ce qui se transporte d'un hôpital à l'autre n'est pas « l'examen a été fait », mais
« l'examen a été fait plus (ou moins) que d'habitude dans cet hôpital, pour un patient comparable ».

## Architecture OP-FL v2 : observation relative au site
- Encodeur physiologique sur X → Zx.
- Modèle de propension π_k(M_t | X_<t, S) : tronc fédéré + petite partie locale par site
  (FedBN ou biais par site et par variable). Entraîné **sans label** → adaptable à un hôpital nouveau
  avec ses seules données non labellisées.
- Résidus d'observation r = M − π_k (peuvent être négatifs) ; encodeur d'observation sur (r, Δ, C) → Zr.
- Tête : concaténation [Zx ‖ Zr ‖ S] → prédiction.
- Abandonnés (sans effet mesurable en v1) : dCor entre Zx et Zm, porte α, fingerprint calculé avec les labels.
- S = variables statiques du **patient**. Les caractéristiques de l'hôpital n'entrent **jamais**
  dans la tête de prédiction (seulement dans la partie locale de π_k).
- Régularisation éventuelle : invariance de P(Y | Zr) entre sites (IRM, V-REx ou GroupDRO fédéré).

Échelle d'ablation (cœur de l'article) :

| Niveau | Canal d'observation | Rôle |
|---|---|---|
| 0 | aucun (X seul) | test de H1 |
| 1 | M, Δ, C bruts (≈ GRU-D) | baseline |
| 2 | M, C centrés sur le taux du site par variable | test rapide et décisif |
| 3 | résidus de propension conditionnels au patient | modèle complet |

Plus une expérience **semi-synthétique** : politiques d'observation simulées par site (vérité connue),
pour montrer que le niveau 1 apprend le raccourci de site et que le niveau 3 y résiste.

## Règles inviolables
1. **Ne jamais re-tirer le protocole.** `data_v1/splits/protocol.json` (hash `bfdd2cb8c54b2e72`) est figé.
2. **Test verrouillé** (96 hôpitaux) : évalué **une seule fois**, à la fin, avec le modèle entraîné sur
   tous les hôpitaux de développement (`fold="final"`). Jamais pour choisir un hyperparamètre.
   `opfl_federated.load_fold` refuse `fold="final"` sans `allow_locked=True`.
3. Sélection de modèle et hyperparamètres : **uniquement** sur le split `val` des hôpitaux d'entraînement du pli.
4. Hôpital tenu à l'écart (pli ou test verrouillé) : son split `train` sert seulement à l'adaptation
   **sans label** (normalisation locale, propension) ; évaluation sur `val + test`.
5. Aucune statistique utilisée en entrée (normalisation, propension, fingerprint) ne dépend des labels.
6. APACHE IVa (`apache_pred`) : comparateur clinique uniquement, jamais une entrée.
7. Charger les données **uniquement** via `src/opfl_data.py`. Ce fichier est généré par l'étape 11
   de `notebooks/01_donnees_v1.ipynb` : modifier le notebook, pas le fichier.
8. Toute comparaison de modèles : mêmes plis, même prétraitement, même backbone, ≥ 5 seeds.
9. Les critères Go / No-Go d'une expérience sont écrits dans `docs/` **avant** de voir ses résultats.

## Données V1.1 (figées le 20/10/2026)
- Cohorte : adultes, 1re unité du séjour hospitalier, durée ≥ 24 h, statut de sortie connu,
  **premier séjour éligible de chaque patient**, hôpitaux ≥ 100 séjours, 1 hôpital exclu (246 : monitorage absent).
  Total : **92 944 séjours, 157 hôpitaux**.
- Développement : **61 hôpitaux** (≥ 500 séjours), 68 304 séjours, 5 plis *leave-hospitals-out*
  (12–13 hôpitaux par pli). Mortalité 9,5 %.
- Test verrouillé : **96 hôpitaux** (101–499 séjours), 24 640 séjours. Mortalité 8,2 %.
- Dans chaque hôpital : split par patient 70 / 10 / 20 stratifié sur la mortalité (seed 42).
- 29 variables temporelles, T = 24 pas horaires (fenêtre 0–24 h) : 16 labos (lactate, pH, paO2, paCO2, FiO2
  + 11 de routine), 6 signes vitaux de monitorage (FC, SpO2, FR, PA invasive systolique/diastolique/moyenne),
  GCS total + 3 composantes + `gcs_unable` (sédation), température, diurèse.
- Labels : `y_mortality` ; `y_aki` (KDIGO ≥ 2 simplifié, défini si `aki_ascertained`, 3,7 %) ; `y_los_gt7`.
- Absence **structurelle** fréquente (variable non utilisée par l'hôpital, `avail = 0`) : PA invasive dans
  34 hôpitaux, GCS dans 26 (composantes 41), gaz du sang 11–13, lactate 12.
- Détails et chiffres : `data_v1/DATA_CARD.md`, `data_v1/reports/`, `docs/CONTEXTE_PROJET.md` § 4.

Utilisation :
```python
import sys; sys.path.insert(0, "../src")
import opfl_data as od
DATA = "../data_v1"
norm = od.load_normalizer(DATA, fold=0)                  # 0..4, ou "final" pour le test verrouillé
train_h, heldout_h = od.fold_hospitals(DATA, 0)
c = od.load_client(DATA, train_h[0], norm, mode="global") # ou mode="local"
tr = od.select(c, "train")   # clés : X, M, C, Delta, S, avail, y_mortality, y_aki, aki_ascertained, ...
```
Formes : X, M, C, Delta (n, 24, 29) ; S (n, 21) ; avail (29,).

Pour les expériences fédérées : `opfl_federated.load_fold(DATA, fold)` charge un pli entier
(clients d'entraînement, val / test des hôpitaux d'entraînement, val + test des hôpitaux tenus à l'écart).

## Code
| Fichier | Contenu |
|---|---|
| `src/opfl_data.py` | chargement et normalisation (généré par le notebook 01) |
| `src/opfl_models.py` | modèles de l'échelle d'ablation (GRU 64, tête MLP 32) |
| `src/opfl_federated.py` | chargement d'un pli, FedAvg, prédiction |
| `src/opfl_metrics.py` | AUROC, AUPRC, Brier, ECE, calibration, bootstrap apparié, méta-analyse |

## Conventions de code
- Notebooks numérotés `notebooks/NN_nom.ipynb`. **Une étape = une seule cellule de code**, précédée d'une
  cellule markdown qui explique l'étape. En-tête de cellule : `# === ÉTAPE k — TITRE ===`.
- Code réutilisable (modèles, boucle fédérée, métriques) dans `src/`.
- Graines fixées partout (`random`, `numpy`, `torch`). Résultats sauvegardés dans `results/NN_nom/`
  (prédictions par run, puis CSV par seed, par pli, par hôpital).
- Machine Windows, exécution **CPU** : modèles légers (GRU 64 unités), chemins avec `pathlib`.
- Chaque notebook se termine par une cellule de contrôles qui échoue si un contrôle ne passe pas.

## Protocole d'évaluation
- Métriques : AUROC, AUPRC, Brier, calibration (ECE *equal-mass*, pente et intercept), par hôpital et agrégées ;
  macro-AUROC et pire hôpital ; IC à 95 % par bootstrap ; seuil choisi sur `val` (Youden).
- Test verrouillé : métriques poolées + méta-analyse à effets aléatoires des AUROC par hôpital
  (petits hôpitaux, souvent < 20 décès).
- Baselines : centralisé, local seul, FedAvg (X seul / X + M), GRU-D fédéré, FedProx, FedBN, Ditto ou FedRep,
  une méthode de généralisation de domaine, APACHE IVa.

## État d'avancement
- [x] 01 — Données V1.1 (20/10/2026) : 19 contrôles OK, protocole figé.
- [ ] 02 — Baselines fédérées sur les 5 plis : X seul, X + M, X + M + Δ + C, GRU-D. **Test de H1 (Go/No-Go)** :
      code écrit (20/10/2026), critères pré-enregistrés dans `docs/02_baselines.md`, **à exécuter**.
- [ ] 03 — Niveau 2 : masque centré par site. Go si le transfert vers les hôpitaux tenus à l'écart s'améliore.
- [ ] 04 — E0 refait sur V1.1 (information mutuelle + test par permutation, matrice de disponibilité).
- [ ] 05 — Niveau 3 (propension) + expérience semi-synthétique.
- [ ] 06 — AKI, calibration, baselines complètes, MIMIC-IV (validation externe), test verrouillé.

Mettre à jour cette section (et le journal des décisions de `docs/CONTEXTE_PROJET.md`) à la fin de chaque session.
