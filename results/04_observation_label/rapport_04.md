# Rapport 04 — observation du label (sans entraînement)

Protocole `d92099ea7c11d517` | 60 hôpitaux de développement | présents à 48 h : 38278 séjours

## Population
```
                                         séjours  créatinine redosée après 24 h  lactate redosé après 24 h
tous les séjours de dév.                   66094                          0.687                      0.108
présents à 48 h                            38278                          0.897                      0.161
présents à 48 h avec créatinine de base    35814                          0.959                        NaN
                                      présents à 48 h
AKI (cas complets)                             0.0442
AKI (non dosé = négatif)                       0.0424
hyperlactatémie (cas complets)                 0.1526
hyperlactatémie (non dosé = négatif)           0.0246
dosages de créatinine / jour (moy.)            1.1235
dosages de lactate / jour (moy.)               0.1929
```
## Propension d'observation (C1, C2, C5)
```
                               n  taux_redosage  auroc_val_test  auroc_avec_observation_24h     tau      I2  Q_p  mortalite_si_redose  mortalite_si_non_redose
label                                                                                                                                                         
créatinine (AKI)           35814         0.9589          0.7263                       0.769  0.6075  0.8888  0.0               0.1249                   0.0733
lactate (hyperlactatémie)  38278         0.1614          0.7424                       0.834  0.7034  0.9714  0.0               0.2576                   0.0933
```
## Éclaircissement (C3)
```
label                            creatinine   lactate
hopitaux_tiers_haut                 20.0000   20.0000
hopitaux_tiers_bas                  20.0000   20.0000
intensite_haut                       1.3258    0.4053
intensite_bas                        0.9981    0.0565
evenements_initiaux                540.0000  454.0000
evenements_apres                   495.2500  154.0000
baisse_relative                      0.0829    0.6608
baisse_relative_sd                   0.0090    0.0195
positifs_devenus_negatifs            0.0734    0.1507
positifs_devenus_non_evaluables      0.0094    0.5101
redosage_avant                       0.9806    0.2764
redosage_apres                       0.9268    0.0843
     label politique  evenements  relatif  redosage
creatinine  observée      1518.0   1.0000    0.9589
creatinine      12 h      1491.0   0.9822    0.9589
creatinine      24 h      1408.0   0.9275    0.9589
creatinine      48 h      1083.0   0.7134    0.9589
creatinine      72 h       880.0   0.5797    0.9589
   lactate  observée       943.0   1.0000    0.1614
   lactate      12 h       900.0   0.9544    0.1614
   lactate      24 h       855.0   0.9067    0.1614
   lactate      48 h       781.0   0.8282    0.1614
```
## Observés / attendus (C4)
```
                           spearman_rho       p  hopitaux
label                                                    
AKI (créatinine)                 0.3560  0.0052        60
hyperlactatémie (lactate)        0.8291  0.0000        60
```
## Critères
```
code                                         critère                                                     valeur rempli
  C1                 dépendance au site (créatinine)                        τ = 0.607, I² = 0.89, Q p = 4.8e-77   True
  C2              dépendance au patient (créatinine)                                              AUROC = 0.726   True
  C3 label sensible à la politique (éclaircissement)                                       baisse = 8.3% ± 0.9%  False
  C4         observés / attendus suivent l'intensité                                       ρ = 0.36, p = 0.0052   True
  C5              lactate vs créatinine (descriptif) τ 0.70 vs 0.61 ; AUROC 0.74 vs 0.73 ; baisse 66.1% vs 8.3%   None
```
**Verdict : GO : l'observation du label dépend de l'hôpital et change le label -> notebook 05 (entraînement fédéré). Mécanisme(s) à traiter : label manquant non aléatoire (cas complets biaisés) ET label erroné.**
