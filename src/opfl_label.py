"""
opfl_label — observation du label (OP-FL).

Généré par notebooks/04_observation_label.ipynb (étape 1) : modifier le notebook, pas ce fichier.

- summarize_post : nombre de dosages et pic par séjour dans une fenêtre d'observation.
- aki_labels / threshold_labels : labels en cas complets et en « non dosé = négatif ».
- site_offset : décalage (log-odds) d'un site par rapport à une propension commune, et sa variance.
- thin_interval / thin_bernoulli : éclaircissement des dosages (politique « au plus un dosage toutes les H heures »,
  ou conservation aléatoire avec une probabilité par séjour).
"""
import numpy as np
import pandas as pd


def summarize_post(post, stays):
    """post : DataFrame [stay_id, offset, value] déjà restreint à la fenêtre ; stays : index des séjours."""
    g = post.groupby("stay_id")["value"]
    out = pd.DataFrame({"n_post": g.size(), "peak": g.max()}).reindex(stays)
    out["n_post"] = out["n_post"].fillna(0).astype(int)
    return out


def aki_labels(base, peak, n_post, ratio=2.0):
    """Cas complets : défini si créatinine de base et redosage ; « non dosé = négatif » : défini si base."""
    base, peak, n_post = np.asarray(base, float), np.asarray(peak, float), np.asarray(n_post)
    has_base = ~np.isnan(base)
    obs = (n_post > 0) & has_base
    with np.errstate(divide="ignore", invalid="ignore"):
        pos = peak / base >= ratio
    cc = np.where(obs, pos.astype(float), np.nan)
    neg = np.where(has_base, np.where(obs, pos.astype(float), 0.0), np.nan)
    return obs, cc, neg


def threshold_labels(peak, n_post, thr):
    peak, n_post = np.asarray(peak, float), np.asarray(n_post)
    obs = n_post > 0
    pos = np.nan_to_num(peak, nan=-np.inf) >= thr
    return obs, np.where(obs, pos.astype(float), np.nan), np.where(obs, pos.astype(float), 0.0)


def site_offset(lp, d, max_iter=100):
    """a tel que somme(sigmoid(lp + a)) = somme(d) (d borné à [0,5 ; n - 0,5]) ; variance = 1 / information."""
    lp, d = np.asarray(lp, float), np.asarray(d, float)
    n = len(d)
    target = float(np.clip(d.sum(), 0.5, n - 0.5))
    a = 0.0
    for _ in range(max_iter):
        mu = 1.0 / (1.0 + np.exp(-np.clip(lp + a, -30, 30)))
        step = (mu.sum() - target) / max((mu * (1 - mu)).sum(), 1e-9)
        a -= step
        if abs(step) < 1e-9:
            break
    mu = 1.0 / (1.0 + np.exp(-np.clip(lp + a, -30, 30)))
    return float(a), float(1.0 / max((mu * (1 - mu)).sum(), 1e-9))


def thin_interval(post, hours, start=1440):
    """Garde le premier dosage de chaque tranche de H heures à partir de `start`."""
    b = ((post["offset"] - start) // (60 * hours)).astype(int)
    return (post.assign(_b=b).sort_values(["stay_id", "offset"], kind="stable")
                .drop_duplicates(["stay_id", "_b"]).drop(columns="_b"))


def thin_bernoulli(post, keep_prob, rng):
    """keep_prob : probabilité de conserver chaque dosage (tableau aligné sur post)."""
    return post[rng.random(len(post)) < np.asarray(keep_prob, float)]
