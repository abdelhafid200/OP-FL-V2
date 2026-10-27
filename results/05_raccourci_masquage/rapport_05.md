# Rapport 05 — raccourci du masque et masquage contrôlé

Protocole `d92099ea7c11d517` | seeds A [11, 22, 33, 44, 55] | seeds B [11, 22, 33, 44, 55] | réglages du notebook 02

## Expérience A — lactate, hôpitaux tenus à l'écart
```
                    AUROC_neg AUROC_neg_par_seed  AUROC_cc  AUROC_D  AUROC_neg_nouv  AUPRC_neg  risque_moyen  prevalence_neg
config                                                                                                                      
A_lac_neg_x_only       0.8827    0.8777 ± 0.0059    0.8152   0.6686          0.7727     0.3903        0.0228          0.0249
A_lac_neg_x_obs        0.8943    0.8909 ± 0.0030    0.8196   0.6991          0.7983     0.4555        0.0206          0.0249
A_lac_neg_obs_only     0.7639    0.7576 ± 0.0106    0.6373   0.6808          0.6501     0.1212        0.0179          0.0249
A_lac_cc_x_only        0.8643    0.8576 ± 0.0018    0.8162   0.6147          0.7458     0.3586        0.0881          0.0249
A_lac_cc_x_obs         0.8963    0.8916 ± 0.0041    0.8257   0.6852          0.8105     0.4264        0.0800          0.0249
A_lac_cc_obs_only      0.7204    0.7011 ± 0.0261    0.6180   0.6499          0.6078     0.1169        0.1398          0.0249

                                                 estimation  IC95_bas  IC95_haut
gain du masque, label enregistré                     0.0115   -0.0029     0.0260
gain du masque, redosés (cc)                         0.0044   -0.0089     0.0201
A1 : différence des gains                            0.0071   -0.0007     0.0154
gain du masque pour prédire D, entraîné sur neg      0.0305    0.0124     0.0484
gain du masque pour prédire D, entraîné sur cc       0.0705    0.0559     0.0859
A2 : différence des gains pour prédire D            -0.0400   -0.0525    -0.0262
AUROC_D x_obs, neg − cc (descriptif)                 0.0139    0.0010     0.0270
```
Contraste AKI :
```
                    AUROC_neg  AUROC_cc  AUROC_D
config                                          
A_aki_neg_x_only       0.7031    0.6986   0.6387
A_aki_neg_x_obs        0.7120    0.7073   0.6341
A_aki_neg_obs_only     0.6626    0.6580   0.6014

                                        estimation  IC95_bas  IC95_haut
AKI : gain du masque, label enregistré      0.0089   -0.0117     0.0296
AKI : gain du masque, redosés (cc)          0.0087   -0.0120     0.0296
```
## Expérience B — masquage contrôlé (tiers haut)
```
                 scenario regime  modele  AUROC_ref  AUROC_ref_cc  AUPRC_ref     O/P
config                                                                              
B_ref_neg_x_only      ref    neg  x_only     0.8771        0.8273     0.4047  1.0508
B_ref_neg_x_obs       ref    neg   x_obs     0.8891        0.8388     0.4698  1.0712
B_ref_cc_x_only       ref     cc  x_only     0.8677        0.8403     0.4050  0.4036
B_ref_cc_x_obs        ref     cc   x_obs     0.8921        0.8493     0.4597  0.4618
B_mid_neg_x_only      mid    neg  x_only     0.8755        0.8260     0.4126  1.2180
B_mid_neg_x_obs       mid    neg   x_obs     0.8920        0.8399     0.4733  1.2671
B_mid_cc_x_only       mid     cc  x_only     0.8701        0.8406     0.3969  0.4427
B_mid_cc_x_obs        mid     cc   x_obs     0.8929        0.8478     0.4632  0.4821
B_low_neg_x_only      low    neg  x_only     0.8829        0.8311     0.4257  1.5743
B_low_neg_x_obs       low    neg   x_obs     0.8954        0.8368     0.4807  1.7537
B_low_cc_x_only       low     cc  x_only     0.8461        0.8240     0.3578  0.3572
B_low_cc_x_obs        low     cc   x_obs     0.8925        0.8386     0.4484  0.4176

                                             estimation  IC95_bas  IC95_haut
B1 : x_obs neg, bas − référence                  0.0063   -0.0177     0.0286
x_only neg, bas − référence                      0.0058   -0.0134     0.0179
B2 : perte x_obs − perte x_only (bas, neg)       0.0005   -0.0152     0.0162
B3 : x_obs cc (bas) − x_obs neg (référence)      0.0034   -0.0200     0.0242
x_obs neg, moyen − référence                     0.0029   -0.0051     0.0088
x_obs cc, référence − x_obs neg, référence       0.0030   -0.0081     0.0126
```
## Critères
```
code                                              critère                      valeur  rempli
  A1 le masque aide surtout à prédire le label enregistré +0.0071 [-0.0007 ; +0.0154]   False
  A2       le masque sert à prédire le dosage (neg vs cc) -0.0400 [-0.0525 ; -0.0262]   False
  B1     la politique change le classement appris (x_obs) +0.0063 [-0.0177 ; +0.0286]   False
  B2                          le masque amplifie la perte +0.0005 [-0.0152 ; +0.0162]   False
  B3             les cas complets atteignent la référence +0.0034 [-0.0200 ; +0.0242]   False
```
**Verdict : PLAN B : ni raccourci démontré ni perte de classement ; article de caractérisation (notebook 04).**
