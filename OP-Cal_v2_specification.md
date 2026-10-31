# OP-Cal v2 — spécification mathématique (projet, à geler par commit avant tout code)

Version de travail du 31/10/2026. Les 96 hôpitaux verrouillés sont exclus de toute estimation, sélection ou évaluation de la v2.

## 0. Trois sources d'incertitude, séparées dans les équations

| Source | Symbole | Nature | Estimée à partir de |
|---|---|---|---|
| Bruit des descripteurs | C_h | erreur sur les **entrées** : ẑ_h mesure z_h avec erreur | les séjours du site, sans label (méthode delta, comme au 08) |
| Incertitude sur la fonction | Var[f(z) \| données] | incertitude **épistémique**, qui grandit hors domaine | le processus gaussien |
| Hétérogénéité entre hôpitaux | τ² | variation **réelle** non expliquée par z | REML |
| Bruit de la cible | v_h | erreur d'estimation de a_h par c_h | 1 / Σ μ(1 − μ) |

## 1. Modèle probabiliste

Pour un site h :

- **Observation de la cible** : c_h = a_h + ε_h, avec ε_h ~ N(0, v_h). c_h est le CITL estimé, et n'existe que pour les sites d'entraînement.
- **Décalage vrai** : a_h = μ + f(z_h) + γ·(log r_h − m_r)·𝟙[label défini par un examen] + u_h, avec u_h ~ N(0, τ²).
- **Fonction** : f ~ GP(0, k).
- **Mesure des entrées** : ẑ_h = z_h + δ_h, avec δ_h ~ N(0, C_h).

Les descripteurs sont standardisés par la moyenne et l'écart-type des **sites d'entraînement du pli**. C_h est mis à la même échelle.

### 1.1 Noyau : une tendance linéaire amortie, plus un terme local

k(z, z') = σ²_L · (z·z') · exp(−‖z − z'‖² / 2ℓ²_L) + σ²_R · exp(−‖z − z'‖² / 2ℓ²_R)

- **Pourquoi pas « linéaire + RBF »** (la figure de la critique le montre) : un noyau linéaire non amorti prolonge la tendance à l'infini, donc la prédiction **ne revient pas** vers μ hors domaine.
- **Propriété de retour à la moyenne.** Pour un site z* tel que min_i ‖z* − z_i‖ → ∞, chaque k(z*, z_i) → 0, car le facteur gaussien domine le facteur polynomial (z*·z_i). La moyenne a posteriori μ + k*ᵀ(K + Σ)⁻¹(c − μ1) tend donc vers μ (plus le terme mécanistique). Le retour est démontré par la forme du noyau ; il n'est pas ajouté à la main.
- **Emboîtement de la v1.** Quand ℓ_L → ∞ et σ_R → 0, k → σ²_L z·z' : c'est la régression bayésienne ridge, soit SiteEB v1 avec σ²_L = s²_β. La v1 est un cas particulier, ce qui permet une ablation propre.
- ℓ_L est fixé **avant** l'analyse à la médiane des distances entre sites d'entraînement (heuristique classique, calculée dans chaque pli). On estime σ²_L, σ²_R, ℓ_R, τ² et μ.

### 1.2 Entrées bruitées : débruitage empirique bayésien des descripteurs

On suppose a priori z_h ~ N(m, Σ_z) entre sites. Σ_z s'estime sur les sites d'entraînement par Cov(ẑ) − moyenne(C_h), projetée sur les matrices semi-définies positives et rétrécie (Ledoit-Wolf).

- Entrée débruitée : z̄_h = E[z_h | ẑ_h] = m + Σ_z (Σ_z + C_h)⁻¹ (ẑ_h − m).
- Covariance résiduelle : P_h = Σ_z − Σ_z (Σ_z + C_h)⁻¹ Σ_z.
- Pour les sites d'entraînement **et** les nouveaux sites, le noyau est évalué en z̄_h. L'incertitude résiduelle s'ajoute au bruit au premier ordre : ∇f(z̄_h)ᵀ P_h ∇f(z̄_h), comme dans NIGP (McHutchon et Rasmussen 2011), avec une itération sur ∇f.
- **Version principale : Σ_z et C_h diagonaux**, par descripteur. Avec 44 descripteurs et 48 à 60 sites, une matrice pleine est instable. Sensibilité : matrice pleine rétrécie.
- Si f est linéaire, cette étape redonne exactement la calibration de régression du 08, en version multivariée. C'est cette étape qui rapproche la prédiction de la moyenne quand le site est **petit** (C_h grand). Le noyau fait de même quand il est **éloigné** (hors domaine).

### 1.3 Estimation

- Estimation par REML : μ et, s'il est estimé, γ sont des effets fixes intégrés ; on maximise la vraisemblance restreinte en (σ²_L, σ²_R, ℓ_R, τ²).
- Pourquoi REML plutôt que la vraisemblance marginale complète : τ² est moins biaisé avec 48 à 60 sites, et c'est le choix de la v1, ce qui garde la comparaison cohérente.
- Contre le sur-ajustement :
  - a priori faibles (log-normaux) sur ℓ_R et σ²_R, donc une estimation MAP de type II ;
  - ℓ_L fixé ;
  - pas de pertinence automatique par descripteur (ARD), qui ferait 44 paramètres.
  - Il reste **4 hyperparamètres** de variance ou d'échelle et 1 ou 2 effets fixes.
- Tout est réestimé **dans chaque pli**, y compris la standardisation, Σ_z, m et ℓ_L.

### 1.4 Prédiction pour un site nouveau, sans label

ã_h = μ̂ + k(z̄_h, Z̄)ᵀ (K + diag(v + τ² + bruit_entrées))⁻¹ (c − μ̂1) + terme mécanistique

On en tire aussi la variance prédictive, qui donne l'a priori N(ã_h, V_h) utilisé avec 0 label, avec un agrégat ou avec k labels, comme en v1.

## 2. Terme mécanistique (labels définis par un examen)

1. **Variable observée** : Y* = D·Y. L'événement n'est enregistré que si l'examen est fait (D = 1), par exemple l'hyperlactatémie avec la règle « non dosé = négatif ».
2. **Événement réel** : Y.
3. **Mécanisme supposé** : chez les vrais cas, P(D = 1 | x, Y = 1, site h) = r_h · ρ(x). L'effet du site est multiplicatif et séparable de x.
4. **Conséquence** : P(Y* = 1 | x) = r_h ρ(x) P(Y = 1 | x). Si l'événement est rare, logit P ≈ log P, d'où logit P(Y* | x, h) ≈ logit P(Y* | x, référence) + log(r_h / r_réf). Le CITL varie donc de log r_h avec un **coefficient 1**.
5. **Hypothèses à déclarer** : événement rare (vérifiable) ; propension à doser séparable ; r_h mesuré par le taux de dosage chez les séjours éligibles, sans label.
6. **Identifiabilité** : γ = 1 est fixé (aucune estimation). Pour la tâche concernée, test_rate et intensity du même examen sont **retirés de z**, pour que log r_h ne figure pas deux fois. Quand γ est estimé (diagnostic, comme le C4 de la v1), il est identifié parce que log r_h n'est pas dans z.
7. **Mortalité** : pas de terme mécanistique (Y observé directement).

## 3. Critères d'évaluation (fixés à l'avance)

Un décalage par site ne change ni l'ordre des patients **dans** un hôpital, ni la pente de calibration, ni l'AUROC intra-hôpital. Les critères ne retiennent donc que ce que la méthode peut changer.

- **Principal : Δℓ.** Δℓ = Σ_h Σ_i [ℓ(lp_i + ã_h, y_i) − ℓ(lp_i, y_i)] / Σ_h n_h, gain de log-vraisemblance par patient contre E0, sur les sites tenus à l'écart.
  - lp est fixé et seul le décalage par site varie : Δℓ mesure donc la calibration globale par site, pas la discrimination.
  - Le poids est par patient. On rapporte aussi la version à poids égal par hôpital.
- **Secondaire : MSE_débiaisé.** MSE_débiaisé = (1/H) Σ_h [(c_h − ã_h)² − v_h], estimateur sans biais de (1/H) Σ (a_h − ã_h)² si c_h est sans biais pour a_h et v_h correct.
  - Restreint aux sites avec au moins 10 événements, parce que le biais de c_h est en O(1/n).
- **Descriptifs** : Brier, |CITL| par hôpital (avec ses limites sur les petits sites), λ effectif, et gain selon la distance au domaine.
- **Comparaisons** : différences appariées par hôpital, IC par bootstrap des hôpitaux (2000 tirages).

## 4. Comparateurs et ablations

| Méthode | Rôle |
|---|---|
| E0 | aucune correction |
| E1 | décalage constant μ |
| OP-Cal v1 (SiteEB) | référence ; cas emboîté |
| v1 + rétrécissement fixe | un facteur réglé dans le pli : le comparateur simple le plus dur |
| v1 + bornage des descripteurs | bornage à la plage [min ; max] de l'entraînement, sans paramètre |
| v1 + débruitage seul | apport de C_h |
| GP sans débruitage | apport du noyau |
| **OP-Cal v2** (GP + débruitage) | méthode proposée |

## 5. Protocole de validation

1. **Plis par hôpital** : les 5 plis du protocole et 10 partitions aléatoires (celles du 06d). C'est le critère de « non-dommage ».
2. **Plis par groupe de case-mix** : k-moyennes (k = 5) sur les descripteurs de case-mix standardisés, sans label, ce qui permet de le faire sur les 60 sites. Chaque groupe est retiré tour à tour. Tous les paramètres sont estimés sur les groupes restants.
3. **Sous-échantillonnage** à la taille des petits hôpitaux (×1 et ×0,5, comme au 08), dans les schémas 1 et 2.

**Règle de décision interne, fixée à l'avance.** La v2 est retenue si, dans le schéma 2 (et le schéma 3 ×1) :
- Δℓ(v2) − max(Δℓ des comparateurs E1, v1, rétrécissement fixe, bornage) > 0, avec une borne basse de l'IC à 95 % > 0 ;
- et, dans le schéma 1, Δℓ(v2) ≥ Δℓ(v1) − 0,0005.

Sinon, la v2 n'est pas retenue, et on le rapporte tel quel.

## 6. Validation sur des sites retenus (si la v2 est retenue)

- **Cohorte** : les 49 hôpitaux eICU à moins de 100 séjours (1912 séjours), jamais utilisés. Fichiers construits avec le code du notebook 01, mêmes critères de cohorte, labels non consultés avant le plan.
- Les descripteurs **et** l'évaluation utilisent tous les séjours du site. Ce n'est pas une fuite : les descripteurs n'utilisent aucun label, et le modèle final n'a jamais vu ces sites.
- **Méta-modèle** : appris une fois sur les 60 sites de développement.
- **Test unique, plan commité avant** : Δℓ(v2 contre E0) > 0, unilatéral à 2,5 %, bootstrap des hôpitaux ; secondaire, Δℓ(v2) − Δℓ(v1).
- Rapporter le nombre de sites, de séjours et d'événements. Présenter ce jeu comme une **validation interne à eICU sur sites retenus**, pas comme une validation externe.
- **MIMIC-IV** : complément mono-centrique (un seul décalage, donc démonstratif seulement).

## 7. À vérifier avant de geler

- Le débruitage de la v2 reproduit la calibration de régression du 08 quand f est linéaire (test unitaire).
- Le noyau ramène bien la prédiction à μ loin des données (test unitaire synthétique).
- La puissance de la validation sur les 49 sites, simulée sur le développement comme au 06d.
- Une recherche bibliographique élargie (Scopus, Google Scholar) sur : GP à entrées incertaines en méta-régression, prédiction de calibration sans label, erreur de mesure dans les covariables de site.
