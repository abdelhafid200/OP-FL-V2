# Rapport H1 — baselines fédérées (mortalité)

Protocole `d92099ea7c11d517` | 4 modèles × 5 plis × 3 seeds | {'rounds': 30, 'client_frac': 0.5, 'local_epochs': 1, 'lr': 0.001, 'batch_size': 64, 'hidden': 64, 'head': 32, 'dropout': 0.1, 'grad_clip': 1.0}

## Synthèse (moyenne ± écart-type sur plis × seeds)
```
                             auroc            auprc            brier              ece        cal_slope         cal_citl      macro_auroc      worst_auroc
intra    x_only    0.8510 ± 0.0020  0.4519 ± 0.0052  0.0664 ± 0.0007  0.0105 ± 0.0027  0.9680 ± 0.0371  0.0767 ± 0.0973  0.8454 ± 0.0031  0.5407 ± 0.0904
         obs_only  0.7704 ± 0.0046  0.2994 ± 0.0082  0.0757 ± 0.0009  0.0106 ± 0.0036  1.0071 ± 0.0211  0.0698 ± 0.0946  0.7742 ± 0.0053  0.5464 ± 0.0462
         x_obs     0.8553 ± 0.0017  0.4566 ± 0.0058  0.0661 ± 0.0008  0.0129 ± 0.0039  0.9694 ± 0.0256  0.1244 ± 0.1235  0.8539 ± 0.0023  0.5816 ± 0.0722
         grud      0.8523 ± 0.0022  0.4539 ± 0.0058  0.0664 ± 0.0007  0.0123 ± 0.0032  0.9536 ± 0.0343  0.1068 ± 0.1215  0.8504 ± 0.0022  0.5555 ± 0.0868
transfer x_only    0.8455 ± 0.0082  0.4429 ± 0.0271  0.0671 ± 0.0028  0.0129 ± 0.0038  0.9401 ± 0.0421  0.0626 ± 0.1053  0.8408 ± 0.0105  0.7128 ± 0.0891
         obs_only  0.7693 ± 0.0137  0.2996 ± 0.0224  0.0762 ± 0.0036  0.0203 ± 0.0054  1.0163 ± 0.0518  0.0888 ± 0.2402  0.7740 ± 0.0173  0.6577 ± 0.0458
         x_obs     0.8502 ± 0.0078  0.4517 ± 0.0298  0.0665 ± 0.0025  0.0131 ± 0.0043  0.9546 ± 0.0305  0.1310 ± 0.1492  0.8491 ± 0.0127  0.7222 ± 0.0859
         grud      0.8468 ± 0.0080  0.4456 ± 0.0280  0.0670 ± 0.0026  0.0145 ± 0.0040  0.9289 ± 0.0315  0.1074 ± 0.1580  0.8448 ± 0.0110  0.7129 ± 0.0896
```

## Critères H1
```
                                critère    valeur                 IC95 plis > 0  rempli
   H1a  signal intra (gain AUROC x_obs)  0.004243    [0.0030 ; 0.0055]      5/5    True
             H1b-1 écart de transport G -0.000509   [-0.0027 ; 0.0017]      2/5   False
 H1b-2 hétérogénéité entre hôpitaux (Q)  0.001071 I² = 0.01, p = 0.447        —   False
 H1b-3 obs_only plus spécifique au site -0.004399                           2/5   False
H1b-4 calibration en transfert (|CITL|)  0.068346                           3/5   False
```

GRU-D vs x_only (intra) : +0.0013 [0.0002 ; 0.0024]

**Verdict : PARTIEL : le canal d'observation aide et se transporte bien sur la mortalité -> tester le niveau 2, renforcer AKI et calibration.**
