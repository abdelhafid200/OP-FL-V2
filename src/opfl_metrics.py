# %%writefile ../src/opfl_metrics.py
"""
opfl_metrics — métriques de discrimination, de calibration et méta-analyse (OP-FL).

Généré par notebooks/02_baselines_h1.ipynb (étape 1) : modifier le notebook, pas ce fichier.
"""
import numpy as np
from scipy import stats
from sklearn.metrics import roc_auc_score, average_precision_score


def both_classes(y, min_each=1):
    y = np.asarray(y)
    k = int(np.sum(y))
    return len(y) > 0 and k >= min_each and (len(y) - k) >= min_each


def auroc(y, p):
    return float(roc_auc_score(y, p)) if both_classes(y) else np.nan


def auprc(y, p):
    return float(average_precision_score(y, p)) if both_classes(y) else np.nan


def brier(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(np.mean((p - y) ** 2)) if len(y) else np.nan


def ece_equal_mass(y, p, n_bins=10):
    y, p = np.asarray(y, float), np.asarray(p, float)
    if len(y) < 2 * n_bins:
        return np.nan
    order = np.argsort(p, kind="stable")
    return float(sum(len(b) * abs(y[b].mean() - p[b].mean())
                     for b in np.array_split(order, n_bins)) / len(y))


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _logistic_irls(X, y, offset=0.0, n_iter=100):
    beta = np.zeros(X.shape[1])
    for _ in range(n_iter):
        mu = 1.0 / (1.0 + np.exp(-np.clip(X @ beta + offset, -30, 30)))
        w = np.clip(mu * (1 - mu), 1e-9, None)
        step = np.linalg.solve((X * w[:, None]).T @ X + 1e-8 * np.eye(X.shape[1]), X.T @ (y - mu))
        beta = beta + step
        if np.max(np.abs(step)) < 1e-8:
            break
    return beta


def calibration_slope_citl(y, p):
    """Pente de calibration (idéal 1) et calibration-in-the-large (intercept avec offset logit(p), idéal 0)."""
    y = np.asarray(y, float)
    if not both_classes(y):
        return np.nan, np.nan
    lp = _logit(p)
    slope = _logistic_irls(np.column_stack([np.ones_like(lp), lp]), y)[1]
    citl = _logistic_irls(np.ones((len(y), 1)), y, offset=lp)[0]
    return float(slope), float(citl)


def summarize(y, p, n_bins=10):
    y, p = np.asarray(y, float), np.asarray(p, float)
    slope, citl = calibration_slope_citl(y, p)
    return {"n": int(len(y)), "events": int(y.sum()),
            "prevalence": float(y.mean()) if len(y) else np.nan,
            "mean_pred": float(p.mean()) if len(p) else np.nan,
            "auroc": auroc(y, p), "auprc": auprc(y, p), "brier": brier(y, p),
            "ece": ece_equal_mass(y, p, n_bins), "cal_slope": slope, "cal_citl": citl}


def paired_auroc_diff_boot(y, p_a, p_b, n_boot=200, seed=0):
    """Différence d'AUROC (b - a) sur les mêmes patients et sa variance par bootstrap stratifié."""
    y = np.asarray(y)
    rng = np.random.default_rng(seed)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    diffs = []
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))])
        diffs.append(roc_auc_score(y[idx], p_b[idx]) - roc_auc_score(y[idx], p_a[idx]))
    return float(roc_auc_score(y, p_b) - roc_auc_score(y, p_a)), float(np.var(diffs, ddof=1))


def random_effects(effects, variances):
    """Méta-analyse DerSimonian-Laird : effet poolé, IC 95 %, tau², I², test Q d'hétérogénéité."""
    y, v = np.asarray(effects, float), np.asarray(variances, float)
    ok = np.isfinite(y) & np.isfinite(v) & (v > 0)
    y, v = y[ok], v[ok]
    k = len(y)
    w = 1 / v
    mu_fe = np.sum(w * y) / np.sum(w)
    Q = float(np.sum(w * (y - mu_fe) ** 2))
    c = np.sum(w) - np.sum(w ** 2) / np.sum(w)
    tau2 = max(0.0, (Q - (k - 1)) / c) if k > 1 else 0.0
    w_re = 1 / (v + tau2)
    mu = float(np.sum(w_re * y) / np.sum(w_re))
    se = float(np.sqrt(1 / np.sum(w_re)))
    return {"k": k, "pooled": mu, "ci_low": mu - 1.96 * se, "ci_high": mu + 1.96 * se,
            "tau2": float(tau2), "tau": float(np.sqrt(tau2)),
            "I2": float(max(0.0, (Q - (k - 1)) / Q)) if Q > 0 else 0.0,
            "Q": Q, "Q_pvalue": float(stats.chi2.sf(Q, k - 1)) if k > 1 else np.nan}


def mean_ci_t(x):
    """Moyenne et IC 95 % de Student (utilisé sur les 5 plis)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    m = float(np.mean(x))
    if len(x) < 2:
        return m, np.nan, np.nan
    h = float(stats.t.ppf(0.975, len(x) - 1) * np.std(x, ddof=1) / np.sqrt(len(x)))
    return m, m - h, m + h