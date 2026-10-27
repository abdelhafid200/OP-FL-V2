# Rapport — niveau 2 et test de stress (mortalité)

Protocole `d92099ea7c11d517` | seeds [11, 22, 33] | alpha = 50.0 | {'rounds': 30, 'client_frac': 0.5, 'local_epochs': 1, 'lr': 0.001, 'batch_size': 64, 'hidden': 64, 'head': 32, 'dropout': 0.1, 'grad_clip': 1.0}

## Plis LOHO
```
                                  auroc      macro_auroc            auprc            brier         cal_citl        cal_slope
intra    x_only         0.8510 ± 0.0020  0.8454 ± 0.0031  0.4519 ± 0.0052  0.0664 ± 0.0007  0.0767 ± 0.0973  0.9680 ± 0.0371
         obs_only       0.7704 ± 0.0046  0.7742 ± 0.0053  0.2994 ± 0.0082  0.0757 ± 0.0009  0.0698 ± 0.0946  1.0071 ± 0.0211
         x_obs          0.8553 ± 0.0017  0.8539 ± 0.0023  0.4566 ± 0.0058  0.0661 ± 0.0008  0.1244 ± 0.1235  0.9694 ± 0.0256
         grud           0.8523 ± 0.0022  0.8504 ± 0.0022  0.4539 ± 0.0058  0.0664 ± 0.0007  0.1068 ± 0.1215  0.9536 ± 0.0343
         x_obs_site     0.8553 ± 0.0019  0.8521 ± 0.0030  0.4581 ± 0.0052  0.0658 ± 0.0008  0.0941 ± 0.0962  0.9577 ± 0.0303
         obs_site_only  0.7785 ± 0.0031  0.7784 ± 0.0047  0.3087 ± 0.0061  0.0750 ± 0.0009  0.0496 ± 0.1017  1.0046 ± 0.0281
transfer x_only         0.8455 ± 0.0082  0.8408 ± 0.0105  0.4429 ± 0.0271  0.0671 ± 0.0028  0.0626 ± 0.1053  0.9401 ± 0.0421
         obs_only       0.7693 ± 0.0137  0.7740 ± 0.0173  0.2996 ± 0.0224  0.0762 ± 0.0036  0.0888 ± 0.2402  1.0163 ± 0.0518
         x_obs          0.8502 ± 0.0078  0.8491 ± 0.0127  0.4517 ± 0.0298  0.0665 ± 0.0025  0.1310 ± 0.1492  0.9546 ± 0.0305
         grud           0.8468 ± 0.0080  0.8448 ± 0.0110  0.4456 ± 0.0280  0.0670 ± 0.0026  0.1074 ± 0.1580  0.9289 ± 0.0315
         x_obs_site     0.8499 ± 0.0088  0.8472 ± 0.0133  0.4505 ± 0.0276  0.0665 ± 0.0025  0.0887 ± 0.1096  0.9373 ± 0.0318
         obs_site_only  0.7761 ± 0.0121  0.7771 ± 0.0180  0.3084 ± 0.0209  0.0754 ± 0.0033  0.0572 ± 0.1732  1.0017 ± 0.0551
```
```
              comparaison  n_hop  abs_citl_a  abs_citl_b  mediane_diff  p_wilcoxon
          x_obs vs x_only     60      0.3065      0.3458        0.0391      0.0192
           grud vs x_only     60      0.3065      0.3592        0.0508      0.0029
      x_obs_site vs x_obs     60      0.3458      0.3255       -0.0076      0.3691
     x_obs_site vs x_only     60      0.3065      0.3255        0.0181      0.0701
obs_site_only vs obs_only     60      0.3759      0.3249       -0.0765      0.0615
```
```
        comparaison  k  pooled  ci_low  ci_high  tau2    tau     I2       Q  Q_pvalue
     x_obs - x_only 60  0.0044  0.0020   0.0067   0.0 0.0011 0.0129 59.7713    0.4475
 x_obs_site - x_obs 60  0.0007 -0.0009   0.0024   0.0 0.0012 0.0337 61.0558    0.4019
x_obs_site - x_only 60  0.0050  0.0024   0.0076   0.0 0.0000 0.0000 55.2769    0.6135
```

## Test de stress
```
                                                auroc      macro_auroc          cal_citl
split         role     model                                                            
bas_vers_haut intra    grud           0.8542 ± 0.0020  0.8549 ± 0.0018   0.0327 ± 0.0695
                       obs_only       0.7853 ± 0.0004  0.7949 ± 0.0006   0.0557 ± 0.0962
                       obs_site_only  0.7914 ± 0.0008  0.7936 ± 0.0007   0.1335 ± 0.0690
                       x_obs          0.8567 ± 0.0012  0.8585 ± 0.0008   0.0853 ± 0.0648
                       x_obs_site     0.8540 ± 0.0012  0.8543 ± 0.0014   0.0131 ± 0.0861
                       x_only         0.8530 ± 0.0020  0.8491 ± 0.0026  -0.0278 ± 0.0705
              transfer grud           0.8411 ± 0.0013  0.8416 ± 0.0019   0.1844 ± 0.0817
                       obs_only       0.7526 ± 0.0011  0.7560 ± 0.0024   0.0756 ± 0.0845
                       obs_site_only  0.7682 ± 0.0013  0.7654 ± 0.0015   0.4299 ± 0.0653
                       x_obs          0.8440 ± 0.0009  0.8441 ± 0.0015   0.2180 ± 0.0618
                       x_obs_site     0.8443 ± 0.0019  0.8439 ± 0.0026   0.2074 ± 0.0645
                       x_only         0.8385 ± 0.0003  0.8363 ± 0.0006   0.0943 ± 0.0640
haut_vers_bas intra    grud           0.8450 ± 0.0015  0.8407 ± 0.0024   0.0898 ± 0.0944
                       obs_only       0.7584 ± 0.0037  0.7603 ± 0.0029   0.1322 ± 0.0043
                       obs_site_only  0.7712 ± 0.0007  0.7655 ± 0.0008   0.0904 ± 0.0752
                       x_obs          0.8486 ± 0.0018  0.8459 ± 0.0017   0.1718 ± 0.0468
                       x_obs_site     0.8506 ± 0.0016  0.8443 ± 0.0019   0.0204 ± 0.0613
                       x_only         0.8443 ± 0.0020  0.8375 ± 0.0027   0.0256 ± 0.0859
              transfer grud           0.8476 ± 0.0010  0.8458 ± 0.0015  -0.1226 ± 0.1023
                       obs_only       0.7799 ± 0.0038  0.7874 ± 0.0032   0.0940 ± 0.0207
                       obs_site_only  0.7805 ± 0.0022  0.7820 ± 0.0019  -0.2269 ± 0.0813
                       x_obs          0.8521 ± 0.0008  0.8517 ± 0.0005   0.0231 ± 0.0538
                       x_obs_site     0.8506 ± 0.0008  0.8464 ± 0.0008  -0.2123 ± 0.0459
                       x_only         0.8483 ± 0.0011  0.8422 ± 0.0017  -0.1235 ± 0.0921
```
```
         sens        modèle  chute modèle  chute x_only  différence de différences
haut_vers_bas      obs_only       -0.0215       -0.0039                    -0.0176
haut_vers_bas         x_obs       -0.0035       -0.0039                     0.0004
haut_vers_bas obs_site_only       -0.0094       -0.0039                    -0.0054
haut_vers_bas    x_obs_site        0.0000       -0.0039                     0.0039
bas_vers_haut      obs_only        0.0326        0.0145                     0.0181
bas_vers_haut         x_obs        0.0128        0.0145                    -0.0017
bas_vers_haut obs_site_only        0.0232        0.0145                     0.0087
bas_vers_haut    x_obs_site        0.0096        0.0145                    -0.0049
```
```
              comparaison  n_hop  abs_citl_a  abs_citl_b  mediane_diff  p_wilcoxon
          x_obs vs x_only     60      0.3119      0.3561        0.0297      0.0334
           grud vs x_only     60      0.3119      0.3598        0.0361      0.0234
      x_obs_site vs x_obs     60      0.3561      0.3398       -0.0188      0.6694
     x_obs_site vs x_only     60      0.3119      0.3398        0.0524      0.0520
obs_site_only vs obs_only     60      0.3575      0.4024        0.1234      0.2925
```
```
             comparaison  k  pooled  ci_low  ci_high   tau2    tau     I2       Q  Q_pvalue
          x_obs - x_only 60  0.0061  0.0036   0.0086 0.0000 0.0028 0.0795 64.0928    0.3026
      x_obs_site - x_obs 60 -0.0002 -0.0020   0.0016 0.0000 0.0023 0.1108 66.3518    0.2384
     x_obs_site - x_only 60  0.0055  0.0028   0.0082 0.0000 0.0023 0.0456 61.8198    0.3757
obs_site_only - obs_only 60  0.0040 -0.0008   0.0088 0.0001 0.0108 0.3708 93.7718    0.0027
```

## Critères
```
code                                   critère                                                                valeur  rempli
  N1           |CITL| LOHO x_obs_site vs x_obs                                            médiane -0.0076, p = 0.369   False
  N2             AUROC LOHO x_obs_site - x_obs                                           +0.0007 [-0.0009 ; +0.0024]    True
  S1 obs_only plus fragile que x_only (stress)                          haut_vers_bas -0.0176, bas_vers_haut +0.0181   False
  S2             |CITL| stress x_obs vs x_only                                           médiane +0.0297, p = 0.0334    True
  S3         stress : x_obs_site corrige x_obs |CITL| médiane -0.0188, p = 0.669 ; AUROC -0.0002 [-0.0020 ; +0.0016]   False
```

**Verdict : PROBLÈME SANS SOLUTION : le problème existe mais le centrage par site ne le corrige pas.**
