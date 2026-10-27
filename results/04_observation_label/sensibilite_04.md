# Notebook 04 — analyses de sensibilité (descriptives)

## Propension de redosage
```
    examen                                           variante  séjours  hôpitaux  taux_redosage  auroc_val_test    tau     I2  Q_p
créatinine                                référence (étape 5)    35814        60         0.9589          0.7263 0.6075 0.8888  0.0
créatinine           + log(durée de présence dans la fenêtre)    35814        60         0.9589          0.8271 0.6453 0.8934  0.0
créatinine                                    présents à 72 h    22840        60         0.9860          0.7562 0.7049 0.7107  0.0
créatinine hors hôpitaux saturés (redosage <= 1 % ou >= 99 %)    35814        51         0.9589          0.7263 0.5483 0.8827  0.0
   lactate                                référence (étape 5)    38278        60         0.1614          0.7424 0.7034 0.9714  0.0
   lactate           + log(durée de présence dans la fenêtre)    38278        60         0.1614          0.7589 0.7106 0.9716  0.0
   lactate                                    présents à 72 h    24193        60         0.2042          0.7172 0.7256 0.9648  0.0
   lactate hors hôpitaux saturés (redosage <= 1 % ou >= 99 %)    38278        60         0.1614          0.7424 0.7034 0.9714  0.0
```
## C4 : IC 95 % de ρ (bootstrap hôpitaux)
```
                             rho  IC95_bas  IC95_haut
label                                                
AKI (créatinine)           0.356     0.101      0.572
hyperlactatémie (lactate)  0.829     0.704      0.910
```
## Masque du lactate à 24 h et label
```
                                      lactate dosé dans les 24 h  lactate non dosé dans les 24 h
part des séjours                                          0.3297                          0.6703
lactate redosé après 24 h                                 0.3693                          0.0592
hyperlactatémie (non dosé = négatif)                      0.0624                          0.0061
hyperlactatémie (cas complets)                            0.1689                          0.1027
```
AUROC du seul masque : {'non dosé = négatif': 0.7588280480775007, 'cas complets': 0.5474418679069044}
