# 02 — Baselines fédérées : test de H1

Notebook : `notebooks/02_baselines.ipynb`. Résultats : `results/02_baselines/`.
Statut : **pré-enregistré le 20/10/2026, pas encore exécuté.** Les critères ci-dessous ont été fixés avant tout résultat.

## Question

**H1.** Le canal d'observation brut (M, Δ, C) apporte une information sur la mortalité *à l'intérieur*
de la fédération, mais cette information dépend du site : son bénéfice varie d'un hôpital à l'autre, ou se dégrade
quand le modèle est appliqué à un hôpital qui n'a pas participé à l'entraînement.

Si H1 est vraie, OP-FL a un problème réel à résoudre (niveaux 2 et 3). Si le canal d'observation n'aide pas,
ou aide partout de la même façon, l'argument « observation relative au site » perd sa base empirique → plan B.

## Plan expérimental

| Élément | Choix |
|---|---|
| Tâche | mortalité hospitalière (`y_mortality`), fenêtre 0–24 h |
| Plis | 5 plis *leave-hospitals-out* du protocole `bfdd2cb8c54b2e72` (61 hôpitaux de dév.) |
| Seeds | 5 (0–4) ; graine du run = 1000 × pli + seed, identique pour tous les modèles (mêmes clients tirés) |
| Normalisation | mode `global` (statistiques du split train des hôpitaux d'entraînement du pli) |
| Fédération | FedAvg, 30 rounds, 50 % des clients par round, 1 époque locale, Adam 1e-3 réinitialisé à chaque round, batch 32, clipping 1,0 |
| Backbone | GRU 64 → [h_T ‖ S] → MLP 32 (ReLU, dropout 0,1) → logit |
| Sélection | meilleur round selon l'AUROC du split val des hôpitaux d'entraînement |
| Test verrouillé | **non utilisé** |

Les hyperparamètres sont ceux de la v1, sans recherche : le but est une comparaison à configuration égale.

| Modèle | Niveau | Entrées temporelles |
|---|---|---|
| `x_only` (référence) | 0 | X |
| `x_m` | 1 | X, M |
| `x_mdc` | 1 | X, M, Δ, C (concaténation) |
| `grud` | 1 | GRU-D : décroissance apprise de l'entrée et de l'état caché, entrée [x̂ ‖ m] |

Note sur GRU-D : X arrive déjà forward-fillé et normalisé (0 = moyenne du pli si jamais observé), donc
x̂ = m·x + (1 − m)·(γx·x_last + (1 − γx)·0) = X·(m + (1 − m)·γx).

## Ensembles d'évaluation

Chaque hôpital de développement est client d'entraînement dans 4 plis et tenu à l'écart dans 1 pli.
On compare les deux situations **sur les mêmes patients** (split test de l'hôpital) :

- **intra** : prédiction moyennée sur les 4 plis où l'hôpital est client × 5 seeds (20 modèles) ;
- **transfert** : prédiction moyennée sur les 5 seeds du pli où l'hôpital est tenu à l'écart.

Ce contraste apparié élimine l'effet de case-mix entre ensembles d'évaluation. Les métriques classiques
par run (intra = test des hôpitaux d'entraînement, heldout = val + test des hôpitaux tenus à l'écart) sont aussi
rapportées (étape 4).

## Critères Go / No-Go (pré-enregistrés)

Pour chaque modèle de niveau 1 contre `x_only`, ΔAUROC = AUROC(modèle) − AUROC(`x_only`) :

| Critère | Définition | Statistique |
|---|---|---|
| **C1** bénéfice intra-site | ΔAUROC intra poolé > 0 | borne basse IC 95 % > 0 (bootstrap apparié, 1 000 tirages, stratifié par hôpital) |
| **C2a** hétérogénéité entre sites | les ΔAUROC intra par hôpital varient plus que le bruit | test Q de la méta-analyse DerSimonian-Laird, p < 0,05 |
| **C2b** dégradation en transfert | ΔAUROC transfert − ΔAUROC intra < 0 | borne haute IC 95 % < 0 (même bootstrap) |

**Go** si C1 et (C2a ou C2b). Hôpitaux inclus dans l'analyse par hôpital : ≥ 5 décès et ≥ 5 survivants dans leur split test.

Lecture des cas :
- C1 faux : le canal d'observation n'aide pas ; OP-FL n'a pas de signal à exploiter → plan B (article de caractérisation).
- C1 vrai, C2a et C2b faux : le canal aide de façon homogène et se transporte ; un modèle de niveau 1 suffit,
  les niveaux 2–3 n'ont pas de raison d'être → plan B, ou repositionnement sur la robustesse.
- C1 vrai, C2a ou C2b vrai : **Go** pour le notebook 03 (niveau 2).

Analyses secondaires (ne décident pas) : ΔAUROC run par run (25 paires pli × seed, nombre de runs gagnés) ;
macro-AUROC et pire hôpital ; calibration ; corrélation de rang (Spearman) entre le bénéfice par hôpital et la
couverture moyenne des variables de l'hôpital (intensité d'observation) — exploratoire.

## Limites connues

- Même `x_only` voit une trace de la missingness (0 = moyenne si jamais observé, plateaux du forward-fill).
  Le contraste mesure donc l'apport d'un canal d'observation **explicite**.
- Test Q peu puissant : beaucoup d'hôpitaux ont ~10 décès dans leur split test ; un C2a négatif n'exclut pas une
  hétérogénéité modérée.
- Les prédictions intra moyennent 20 modèles et les prédictions en transfert 5 : l'effet d'ensemble est un peu plus
  fort en intra. Il touche les deux modèles comparés de la même façon, donc le ΔAUROC reste comparable ; à
  vérifier si l'écart observé est très faible.

## Résultats

*À remplir après exécution.*
