# %%writefile ../src/opfl_site.py
"""
opfl_site — protocoles de transfert supplémentaires et observation relative au site (niveau 2).

Généré par notebooks/03_niveau2_stress.ipynb (étape 1) : modifier le notebook, pas ce fichier.

- make_normalizer : normalisation sur le split train d'une liste quelconque d'hôpitaux (= notebook 01, étape 10).
- load_split : comme opfl_fed.load_fold pour une liste quelconque d'hôpitaux ; charge aussi le split train des
  hôpitaux tenus à l'écart SANS label (M, Δ, C seulement), pour l'adaptation non supervisée.
- center_obs_ : niveau 2. M, Δ, C remplacés par leur écart à la moyenne de l'hôpital (par heure et par variable),
  calculée sur son split train sans label, rétrécie vers la moyenne des hôpitaux d'entraînement.
- metrics_from_preds, hospital_means, compare_abs_citl, meta_auroc_gain : analyses.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from scipy import stats

import opfl_data as od
from opfl_fed import _pack, LABEL_KEYS
from opfl_metrics import summarize, both_classes, paired_auroc_diff_boot, random_effects

OBS_KEYS = ("M", "D", "C")


def _mean_std(n, s, ss):
    n = np.asarray(n, float)
    mean = np.divide(s, n, out=np.zeros_like(n), where=n > 0)
    var = np.divide(ss, n, out=np.zeros_like(n), where=n > 0) - mean ** 2
    std = np.sqrt(np.clip(var, 0, None))
    std = np.where((n < 2) | (std < 1e-6), 1.0, std)
    return mean, std


def make_normalizer(data_dir, train_hospitals, heldout_hospitals=()):
    data_dir = Path(data_dir)
    feats = od.load_features(str(data_dir))
    log_mask = np.asarray(feats["log"], bool)
    n_dx = len(feats["dx_vocab"])
    missing_code = feats["dx_vocab"].index("missing") if "missing" in feats["dx_vocab"] else -1
    tot = None
    for h in train_hospitals:
        d = np.load(data_dir / "clients" / f"hospital_{int(h)}.npz")
        tr = d["split"] == 0
        x = d["X_raw"][tr].astype(np.float64)
        x[..., log_mask] = np.log1p(np.clip(x[..., log_mask], 0, None))
        s = d["S_num"][tr].astype(np.float64)
        st = {"n": (~np.isnan(x)).sum((0, 1)), "sum": np.nansum(x, (0, 1)), "sumsq": np.nansum(x ** 2, (0, 1)),
              "s_n": (~np.isnan(s)).sum(0), "s_sum": np.nansum(s, 0), "s_sumsq": np.nansum(s ** 2, 0),
              "dx": np.bincount(d["dx_code"][tr], minlength=n_dx)}
        tot = st if tot is None else {k: tot[k] + st[k] for k in st}
    xm, xs = _mean_std(tot["n"], tot["sum"], tot["sumsq"])
    sm, ss_ = _mean_std(tot["s_n"], tot["s_sum"], tot["s_sumsq"])
    dx_counts = tot["dx"].copy()
    if missing_code >= 0:
        dx_counts[missing_code] = 0
    top = [int(c) for c in np.argsort(-dx_counts, kind="stable")[:15] if dx_counts[c] > 0]
    return {"fold": "custom", "train_hospitals": sorted(int(h) for h in train_hospitals),
            "heldout_hospitals": sorted(int(h) for h in heldout_hospitals),
            "computed_from": "split train des hôpitaux d'entraînement uniquement",
            "features": feats["features"],
            "x_mean": xm.tolist(), "x_std": xs.tolist(), "x_count": tot["n"].astype(int).tolist(),
            "s_mean": sm.tolist(), "s_std": ss_.tolist(),
            "dx_top_codes": top, "dx_top_names": [feats["dx_vocab"][c] for c in top],
            "dx_missing_code": int(missing_code)}


def load_split(data_dir, train_h, held_h, norm, task="mortality"):
    label_key = LABEL_KEYS[task]
    locked = set(od.load_protocol(data_dir)["locked_test_hospitals"])
    if locked & {int(h) for h in list(train_h) + list(held_h)}:
        raise ValueError("Le test verrouillé ne se charge pas avec load_split.")
    if set(map(int, train_h)) & set(map(int, held_h)):
        raise ValueError("Un hôpital ne peut pas être à la fois d'entraînement et tenu à l'écart.")
    clients = {}
    for h in train_h:
        c = od.load_client(data_dir, h, norm, mode="global")
        clients[int(h)] = {s: _pack(c, s, label_key) for s in ("train", "val", "test")}
    for h in held_h:
        c = od.load_client(data_dir, h, norm, mode="global")
        unl = od.select(c, "train")                     # NON labellisé : seules M, Delta, C sont gardées
        clients[int(h)] = {"valtest": _pack(c, ["val", "test"], label_key),
                           "unlabeled": {"M": torch.from_numpy(unl["M"]), "D": torch.from_numpy(unl["Delta"]),
                                         "C": torch.from_numpy(unl["C"])}}
    first = clients[int(train_h[0])]["train"]
    return {"train_h": [int(h) for h in train_h], "held_h": [int(h) for h in held_h], "clients": clients,
            "n_feat": int(first["X"].shape[2]), "n_static": int(first["S"].shape[1]), "centered": False}


def site_obs_means(fd, alpha=50.0):
    """Moyenne de M, Δ, C par hôpital, heure et variable sur le split train (sans label), rétrécie vers la moyenne
    des hôpitaux d'entraînement : (somme_k + alpha * moyenne_globale) / (n_k + alpha)."""
    sums, ns = {}, {}
    for h, c in fd["clients"].items():
        src = c["train"] if "train" in c else c["unlabeled"]
        ns[h] = int(src["M"].shape[0])
        sums[h] = {k: src[k].double().sum(0) for k in OBS_KEYS}
    n_g = sum(ns[h] for h in fd["train_h"])
    glob = {k: sum(sums[h][k] for h in fd["train_h"]) / n_g for k in OBS_KEYS}
    return {h: {k: ((sums[h][k] + alpha * glob[k]) / (ns[h] + alpha)).float() for k in OBS_KEYS}
            for h in fd["clients"]}


def center_obs_(fd, alpha=50.0):
    """Niveau 2 (en place) : M, Δ, C -> écart à la moyenne de l'hôpital. Retourne les moyennes utilisées."""
    if fd.get("centered"):
        raise RuntimeError("Données déjà centrées.")
    means = site_obs_means(fd, alpha)
    for h, c in fd["clients"].items():
        c.pop("unlabeled", None)
        for data in c.values():
            for k in OBS_KEYS:
                data[k] = data[k] - means[h][k]
    fd["centered"] = True
    return means


def metrics_from_preds(preds, keys, min_events=5):
    run_rows, hosp_rows = [], []
    for key, g in preds.groupby(list(keys), sort=True):
        key = dict(zip(keys, key if isinstance(key, tuple) else (key,)))
        for role in ("intra", "transfer"):
            r = g[g["role"] == role]
            if r.empty:
                continue
            aucs = []
            for h, gh in r.groupby("hospitalid"):
                y, p = gh["y"].to_numpy(), gh["p"].to_numpy()
                met = summarize(y, p)
                met["evaluable"] = both_classes(y, min_events)
                if not met["evaluable"]:
                    met["auroc"] = np.nan
                hosp_rows.append({**key, "role": role, "hospitalid": h, **met})
                aucs.append(met["auroc"])
            aucs = np.array(aucs, float)
            run_rows.append({**key, "role": role, **summarize(r["y"].to_numpy(), r["p"].to_numpy()),
                             "macro_auroc": float(np.nanmean(aucs)), "worst_auroc": float(np.nanmin(aucs)),
                             "n_hosp": len(aucs), "n_hosp_eval": int(np.isfinite(aucs).sum())})
    return pd.DataFrame(run_rows), pd.DataFrame(hosp_rows)


def hospital_means(hosp, role, value="cal_citl"):
    """Valeur par hôpital évaluable, moyennée sur les seeds ; une colonne par modèle."""
    h = hosp[(hosp["role"] == role) & hosp["evaluable"]]
    return h.groupby(["model", "hospitalid"])[value].mean().unstack("model")


def compare_abs_citl(w, a, b):
    """|CITL| par hôpital de b comparé à a (différence > 0 : b plus décalibré). Wilcoxon apparié."""
    d = (w[b].abs() - w[a].abs()).dropna()
    return {"comparaison": f"{b} vs {a}", "n_hop": int(len(d)),
            "abs_citl_a": float(w[a].abs().mean()), "abs_citl_b": float(w[b].abs().mean()),
            "mediane_diff": float(d.median()), "p_wilcoxon": float(stats.wilcoxon(d).pvalue)}


def meta_auroc_gain(preds_role, base, other, min_events=5, n_boot=200):
    """Méta-analyse à effets aléatoires des différences d'AUROC par hôpital (other - base), prédictions moyennées sur les seeds."""
    ens = (preds_role[preds_role["model"].isin([base, other])]
           .groupby(["model", "hospitalid", "stay_id"], sort=False)
           .agg(y=("y", "first"), p=("p", "mean")).reset_index())
    g, v = [], []
    for h, gh in ens.groupby("hospitalid"):
        a = gh[gh["model"] == base].set_index("stay_id")
        if not both_classes(a["y"].to_numpy(), min_events):
            continue
        b = gh[gh["model"] == other].set_index("stay_id").loc[a.index]
        gi, vi = paired_auroc_diff_boot(a["y"].to_numpy(), a["p"].to_numpy(), b["p"].to_numpy(), n_boot, seed=int(h))
        g.append(gi)
        v.append(vi)
    return {"comparaison": f"{other} - {base}", **random_effects(g, v)}