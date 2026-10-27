"""
tdtfl.metrics — métriques de TDT-FL (protocole 1.1).

Généré par notebooks/03_modeles_E0.ipynb (étape 1) : modifier le notebook, pas ce fichier.
Discrimination (AUROC, AUPRC), calibration (Brier, intercept de calibration globale, pente, ECE à classes de
même effectif), bootstrap par grappes d'hôpitaux.
"""
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

EPS = 1e-6


def _two_classes(y):
    s = float(np.sum(y))
    return 0 < s < len(y)


def auroc(y, p):
    return float(roc_auc_score(y, p)) if _two_classes(y) else np.nan


def auprc(y, p):
    return float(average_precision_score(y, p)) if _two_classes(y) else np.nan


def brier(y, p):
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def _logit(p):
    p = np.clip(np.asarray(p, dtype=np.float64), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def _irls(y, Z, offset, iters=100):
    beta = np.zeros(Z.shape[1])
    for _ in range(iters):
        eta = Z @ beta + offset
        mu = 0.5 * (1.0 + np.tanh(0.5 * eta))
        W = mu * (1 - mu) + 1e-10
        H = (Z * W[:, None]).T @ Z + 1e-8 * np.eye(Z.shape[1])
        step = np.linalg.solve(H, Z.T @ (y - mu))
        beta += step
        if np.max(np.abs(step)) < 1e-8:
            break
    return beta


def calibration(y, p):
    """(intercept de calibration globale, pente de calibration) ; idéal : (0, 1)."""
    y = np.asarray(y, dtype=np.float64)
    if not _two_classes(y):
        return np.nan, np.nan
    lp = _logit(p)
    a = _irls(y, np.ones((len(y), 1)), lp)[0]
    slope = _irls(y, np.column_stack([np.ones(len(y)), lp]), np.zeros(len(y)))[1]
    return float(a), float(slope)


def ece(y, p, n_bins=10):
    y = np.asarray(y, dtype=np.float64)
    p = np.asarray(p, dtype=np.float64)
    order = np.argsort(p, kind="stable")
    out = 0.0
    for b in np.array_split(order, n_bins):
        if len(b):
            out += len(b) / len(y) * abs(y[b].mean() - p[b].mean())
    return float(out)


def all_metrics(y, p):
    y = np.asarray(y, dtype=np.float64)
    p = np.asarray(p, dtype=np.float64)
    a, s = calibration(y, p)
    return {"n": int(len(y)), "events": int(y.sum()), "auroc": auroc(y, p), "auprc": auprc(y, p),
            "brier": brier(y, p), "cal_intercept": a, "cal_slope": s, "ece": ece(y, p)}


def cluster_bootstrap(groups, fn, n_boot=1000, seed=0):
    """Rééchantillonne les grappes (hôpitaux) avec remise ; fn(liste d'identifiants) -> statistique."""
    rng = np.random.default_rng(seed)
    groups = np.asarray(groups)
    return np.array([fn(rng.choice(groups, size=len(groups), replace=True)) for _ in range(n_boot)])
