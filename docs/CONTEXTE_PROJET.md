# OP-FL — Contexte complet, historique et décisions

Document de référence pour reprendre le projet (par une personne ou par Claude Code).
Le résumé opérationnel est dans `CLAUDE.md` à la racine ; ce fichier explique **pourquoi**.

---

## 1. Le projet en une page

**Titre de travail.** OP-FL : *Observation-Process-Aware Federated Learning* pour la prédiction clinique
sur dossiers patients hétérogènes (eICU-CRD).

**Constat de départ (revue systématique, 57 études 2019–2025).** Les méthodes de FL sur EHR traitent presque
toujours une seule dimension d'hétérogénéité ; plus de 80 % simulent la fédération en découpant un seul jeu de
données ; la *missingness* n'est l'objet central que d'une étude sur 57 ; l'hétérogénéité temporelle n'est
traitée dans aucune ; aucune ne rapporte de courbe de calibration ni d'ECE.

**Hypothèse.** Une part de la non-IID des EHR vient de processus d'observation hétérogènes : quels examens
sont prescrits, à quelle fréquence, pour quels patients. Formellement, P_k(Y | X, O) ≠ P_j(Y | X, O) même si
P(X) est proche, parce que P_k(O | X, Y) diffère d'un site à l'autre (O = M, Δ, C).

**Exemple.** Dans un hôpital où le lactate est dosé chez tout le monde, sa présence ne dit rien.
Dans un hôpital où il n'est dosé que sur suspicion, sa présence signale l'inquiétude du clinicien.
La même observation n'a pas la même valeur selon le site.

**Contributions visées.**
1. Méthodologique : un canal d'observation *relatif au site* (résidus de propension), entraînable en fédéré
   et adaptable sans label à un hôpital nouveau.
2. Empirique : caractérisation de l'hétérogénéité du processus d'observation sur 157 vrais hôpitaux
   (E0, disponibilité des variables, *ascertainment* de l'AKI de 0 à 97 % selon l'hôpital).
3. Clinique : évaluation sur hôpitaux jamais vus (5 plis + test verrouillé de 96 hôpitaux), avec calibration.

**Positionnement (déjà publié, à ne pas refaire).** FedWeight (npj Digital Medicine 2025, repondération pour le
covariate shift), FedRew (CMPB 2025, personnalisation hiérarchique sur eICU), EHRFL (Sci Rep 2026,
hétérogénéité de schéma), Molaei et al. (JBHI 2026, vues de features), imputation fédérée (FedIMPUTE, D3MI).
Références incontournables sur la missingness informative : GRU-D (Che et al., 2018), Agniel et al. (BMJ 2018).
La *gap matrix* des 57 articles et des travaux 2025–2026 reste à construire.

---

## 2. Historique : OP-FL v1 (avant octobre 2026)

### Architecture v1
```
X (24×27) ─► GRU(64) ─► Zx ─┐
                            ├─► Z = Zx + α ⊙ Zm ─► [Z ‖ S] ─► MLP(32) ─► logit
[M,Δ,C] (24×81) ─► GRU(64) ─► Zm ┘
Perte : BCE + λ1·dCor(Zx, Zm) + λ_var·L_var (anti-collapse) ; α global puis α_k = sigmoid(MLP(H_k))
H_k : fingerprint de 12 dimensions (taux de présence, I(M;Y) avec la mortalité, Δ moyen, par bloc)
FedAvg, 30 rounds, 50 % des clients par round, 1 époque locale, Adam 1e-3, batch 32.
64 hôpitaux d'entraînement + 5 hôpitaux « non vus » (184, 152, 165, 248, 167).
```

### Résultats v1 (mortalité, 3 seeds)

| Modèle | Val AUROC | Val AUPRC | Non vus AUROC | Non vus AUPRC |
|---|---|---|---|---|
| Zx seul | 0,813 ± 0,001 | 0,444 | 0,843 ± 0,003 | 0,378 |
| Zm seul | 0,768 ± 0,003 | 0,373 | 0,793 ± 0,001 | 0,293 |
| Zx + Zm (concaténation) | 0,819 ± 0,002 | 0,449 | 0,849 ± 0,005 | 0,387 |
| OP-FL v1 (α + dCor) | 0,815 ± 0,002 | 0,449 | 0,848 ± 0,004 | 0,376 |

- λ1 = 0 contre λ1 = 0,1 : 0,844 contre 0,846 sur les non vus (écart < écart-type inter-seeds).
- dCor appliquée seule → **collapse** de Zm (écart-type ≈ 3·10⁻⁵), corrigé par L_var et un warm-up de λ1.
- Fingerprint v2 : α_k varie peu (±5 à ±13 %), aucun gain ; un hôpital s'effondre avec une init agressive.
- Site probes : Zx était **plus** identifiable par site que Zm (0,30 contre 0,17–0,19).

### Diagnostic (octobre 2026)
1. Le mécanisme OP-FL v1 n'apporte rien au-delà d'une concaténation simple ; « ajouter le masque aide un peu »
   est déjà connu (GRU-D).
2. L'architecture ne modélisait pas l'hypothèse : la dCor force l'indépendance **Zx/Zm**, alors que le problème
   est la dépendance **Zm/site** ; α ne change pas ce que Zm *signifie* d'un site à l'autre.
3. Le fingerprint utilisait I(M;Y), donc les labels : inutilisable sur un hôpital nouveau (et fuite de labels).
4. Protocole compromis : les 5 sites « non vus » avaient servi à choisir λ1 et l'initialisation.
5. Bugs de prétraitement (détaillés au § 3), dont un majeur : un sodium jamais mesuré valait environ −35 après
   normalisation, ce qui faisait **fuir la missingness dans Zx**. Cela explique probablement pourquoi Zx
   identifiait le site mieux que Zm. **Les résultats v1 sont donc considérés comme non fiables.**

---

## 3. Données V1.1 : ce qui a été corrigé

| # | Ancienne version | V1.1 |
|---|---|---|
| 1 | Valeurs jamais observées mises à 0 avant le z-score, moyenne calculée sans les zéros | Stats sur valeurs observées, forward-fill après normalisation, jamais observé = 0 (= moyenne) |
| 2 | Normalisation sur train + val + test de chaque client | Stats du split train des hôpitaux d'entraînement du pli |
| 3 | Normalisation locale seule | Mode `global` par défaut (stats fédérées), `local` disponible |
| 4 | Code de tirage des splits absent | Tirage dans le notebook, figé par un hash |
| 5 | 5 sites « non vus » déjà consultés | 5 plis leave-hospitals-out + test verrouillé jamais consulté |
| 6 | Plusieurs séjours par patient, parfois dans plusieurs hôpitaux | Premier séjour éligible de chaque patient |
| 7 | GCS « non évaluable (sédation) » → M = 0 | M = 1 + variable `gcs_unable` |
| 8 | Température exclue (9 % dans vitalPeriodic) | vitalPeriodic + nurseCharting : 97 % des séjours |
| 9 | Pas de bornes de plausibilité ; FiO2 mélangée fraction / % | Bornes par variable ; FiO2 en % |
| 10 | Top-15 diagnostics et médianes de S sur toute la cohorte | Calculés par pli, hôpitaux d'entraînement seulement |
| 11 | Hôpitaux sans module gardés | Exclusion sans label avant le protocole (1 hôpital : 246) |
| 12 | — | Indicateur `avail` par hôpital et par variable |
| 13 | Température comptée deux fois (°C et °F de la même saisie) | 853 265 doublons retirés |
| 14 | « Urine Count / Occurrence / Stool » additionnés aux volumes | Exclus |

Validation : la présence des labos dans les hôpitaux de développement retrouve l'ancienne extraction à ±0,01.

---

## 4. Données V1.1 : chiffres clés (exécution du 20/10/2026)

**Flux de la cohorte**

| Étape | Séjours | Patients | Hôpitaux |
|---|---|---|---|
| Séjours en unité (eICU) | 200 859 | 139 367 | 208 |
| 1re unité du séjour hospitalier | 158 442 | 133 492 | 208 |
| Âge ≥ 18 ans | 157 883 | 132 994 | 208 |
| Durée en unité ≥ 24 h | 110 257 | 95 823 | 208 |
| Statut de sortie connu | 109 218 | 95 012 | 207 |
| 1er séjour éligible de chaque patient | 95 012 | 95 012 | 207 |
| Hôpitaux ≥ 100 séjours | 93 100 | 93 100 | 158 |
| Labo de routine et monitorage disponibles (1 exclu) | 92 944 | 92 944 | 157 |

**Protocole (hash `bfdd2cb8c54b2e72`)**

| Groupe | Hôpitaux | Séjours | Décès | Mortalité |
|---|---|---|---|---|
| pli 0 | 12 | 12 990 | 1 113 | 8,6 % |
| pli 1 | 12 | 12 890 | 1 357 | 10,5 % |
| pli 2 | 12 | 14 248 | 1 294 | 9,1 % |
| pli 3 | 13 | 13 854 | 1 368 | 9,9 % |
| pli 4 | 12 | 14 322 | 1 330 | 9,3 % |
| test verrouillé | 96 | 24 640 | 2 029 | 8,2 % |

**Labels.** Dév. : mortalité 9,46 %, AKI évaluable 81 %, AKI 3,7 %, LOS > 7 j 11,3 %, APACHE IVa disponible 88 %.
Test verrouillé : mortalité 8,23 %, AKI évaluable 79 %, AKI 3,2 %.
*Ascertainment* de l'AKI par hôpital : de 0 % à 97 % (écart-type 0,12).

**Disponibilité (hôpitaux où la variable est observée chez < 5 % des séjours)** : PA invasive 34, GCS composantes 41,
GCS total et `gcs_unable` 26, FiO2 13, lactate 12, paCO2 12, pH 11, paO2 11, bicarbonate 5, bilirubine 3,
diurèse 3, fréquence respiratoire 1.

---

## 5. Plan de travail et critères Go / No-Go

1. **02 — Baselines (H1).** FedAvg X seul, FedAvg X + M, GRU-D fédéré ; 5 plis, 5 seeds.
   *Go* si le masque aide en intra-site et que son bénéfice varie entre sites / se dégrade en transfert.
2. **03 — Niveau 2.** Masque et compteurs centrés sur le taux du site (statistiques sans label, split train).
   *Go* si le transfert vers les hôpitaux tenus à l'écart s'améliore, même faiblement.
3. **04 — E0 refait.** I(M_v ; Y) par hôpital avec test par permutation (le plug-in est biaisé ≈ 1/(2n)),
   corrélation de rang avec la prévalence, matrice de disponibilité (figure de l'article).
4. **05 — Niveau 3 + semi-synthétique.**
5. **06 — AKI** (tâche où le processus d'observation touche le label lui-même), calibration, baselines
   complètes, MIMIC-IV comme site externe, puis **une seule** évaluation du test verrouillé.

**Plan B** si 02 et 03 sont négatifs : article de caractérisation (E0 + disponibilité + *ascertainment* de l'AKI
+ calibration sous fédération réelle), cibles JAMIA, JBI, npj Digital Medicine.

---

## 6. Points ouverts et limites connues

- **Glucose capillaire** : eICU contient un `labname` distinct « bedside glucose ». Certains hôpitaux ont une
  couverture « glucose » très basse (jusqu'à 14 %), probablement parce qu'ils saisissent le glucose capillaire.
  Ajout possible plus tard (changer les variables ne change pas le protocole).
- **AKI** : au moins un hôpital a 0 % de patients évaluables (pas de créatinine après 24 h). Décider des hôpitaux
  inclus pour la tâche AKI dans son propre notebook, sans toucher au protocole.
- **Test verrouillé** : beaucoup d'hôpitaux ont moins de 20 décès ; métriques par hôpital instables
  → privilégier le poolé + méta-analyse à effets aléatoires.
- **Tables non utilisées en V1** (à ajouter seulement si une expérience l'exige) : vitalAperiodic (PA non invasive),
  microLab (instant du prélèvement), infusionDrug / treatment (vasopresseurs, sédation), respiratoryCharting,
  carePlanGeneral (limitations de soins : confondeur, analyse de sensibilité), hospital (région, statut universitaire).
  Ne jamais utiliser carePlanEOL (fuite du label).

---

## 7. Journal des décisions

| Date | Décision | Raison |
|---|---|---|
| 19/10/2026 | Abandon de dCor, α et du fingerprint avec labels | Aucun gain en v1 ; ne modélisent pas la dépendance au site |
| 19/10/2026 | Architecture « observation relative au site » (résidus de propension) | Modélise directement P_k(O \| X) |
| 19/10/2026 | Réimplémentation à zéro des données (dossier OP-FL-V2) | Fuites et bugs de l'ancien prétraitement |
| 19/10/2026 | 5 plis leave-hospitals-out + test verrouillé (hôpitaux 100–499 séjours) | Les 5 anciens sites non vus étaient compromis |
| 20/10/2026 | Premier séjour *éligible* par patient | La v1.0 perdait les patients dont le 1er séjour durait < 24 h |
| 20/10/2026 | Exclusion des hôpitaux sans labo ou monitorage (critère sans label) | Absence structurelle = identifiant de site |
| 20/10/2026 | Indicateur `avail` par hôpital et variable | Absences structurelles partielles fréquentes |
| 20/10/2026 | **Données V1.1 figées**, hash `bfdd2cb8c54b2e72` | 19 contrôles OK |
