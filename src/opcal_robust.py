# %%writefile ../src/opcal_robust.py
"""
opcal_robust — robustesse de la calibration de site sans label (OP-Cal) et comparateurs publiés.

Généré par notebooks/06c_robustesse_opcal.ipynb (étape 1) : modifier le notebook, pas ce fichier.
S'appuie sur src/opcal_feas.py (notebook 06b), qui n'est pas modifié.

Comparateurs sans label publiés, qui corrigent eux aussi l'intercept d'un site à partir des seules
prédictions sur ses patients (sans label) :
  - E0 : aucune correction = hypothèse d'un décalage de covariables pur avec un modèle bien spécifié ;
  - EM : ajustement de la prévalence sous décalage de labels (Saerens, Latinne et Decaestecker 2002),
         après recalibration de l'intercept sur la source (variante « bias-corrected », Alexandari et al. 2020) ;
  - BBSE : estimation de la prévalence par le moment E_t[q] = pi_t m1 + (1 - pi_t) m0 (Lipton et al. 2018,
           version à scores continus).
La source d'un pli f = les patients `val` des hôpitaux d'entraînement de ce pli (labels autorisés : ils sont
dans la fédération). Aucune de ces méthodes ne lit un label de l'hôpital tenu à l'écart.
"""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

import opcal_feas as oc


# ----------------------------------------------------------------------------------------------
# Prédictions d'un rôle donné (val = source du pli ; transfer = hôpitaux tenus à l'écart)
# ----------------------------------------------------------------------------------------------

def load_role(pred_dir, name, folds, role, seeds=None):
    """Prédictions d'un rôle, moyennées sur les seeds, une ligne par (pli, séjour)."""
    runs = oc.list_runs(pred_dir)
    r = runs[runs["name"] == name]
    if r.empty:
        raise FileNotFoundError(f"Aucune prédiction pour '{name}' dans {pred_dir}")
    if seeds is None:
        seeds = [s for s in sorted(r["seed"].unique()) if set(r.loc[r["seed"] == s, "fold"]) >= set(folds)]
    parts = []
    for _, row in r[r["seed"].isin(seeds) & r["fold"].isin(folds)].iterrows():
        d = pd.read_parquet(row["path"])
        d = d[d["role"] == role]
        cols = ["stay_id", "hospitalid", "p"] + (["y"] if "y" in d.columns else [])
        parts.append(d[cols].assign(fold=row["fold"], seed=row["seed"]))
    if not parts:
        raise RuntimeError(f"'{name}' : aucune ligne de rôle '{role}'")
    d = pd.concat(parts, ignore_index=True)
    agg = {"hospitalid": ("hospitalid", "first"), "p": ("p", "mean"), "n_seeds": ("seed", "nunique")}
    if "y" in d.columns:
        agg["y"] = ("y", "first")
    out = d.groupby(["fold", "stay_id"]).agg(**agg).reset_index()
    out["lp"] = oc.logit(out["p"].to_numpy())
    return out, seeds


def source_reference(val):
    """Par pli : décalage a_s qui calibre le score sur la source, prévalence pi_s,
    moyennes m1 = E_s[q | y = 1] et m0 = E_s[q | y = 0] du score recalibré q."""
    rows = {}
    for f, g in val.groupby("fold"):
        lp, y = g["lp"].to_numpy(), g["y"].to_numpy(float)
        a_s, _ = oc.offset_fit(lp, y)
        q = oc.sigmoid(lp + a_s)
        rows[int(f)] = {"a_s": a_s, "pi_s": float(y.mean()), "m1": float(q[y == 1].mean()),
                        "m0": float(q[y == 0].mean()), "n_source": len(g), "hopitaux_source": g["hospitalid"].nunique()}
    return pd.DataFrame(rows).T


def em_prior(q, pi_s, max_iter=1000, tol=1e-10):
    """EM de Saerens et al. (2002) pour un label binaire : prévalence cible pi_t à partir des
    probabilités a posteriori q (calibrées pour la prévalence source pi_s)."""
    q = np.clip(np.asarray(q, float), 1e-9, 1 - 1e-9)
    pi = float(pi_s)
    for _ in range(max_iter):
        r1, r0 = pi / pi_s, (1 - pi) / (1 - pi_s)
        new = float(np.mean(r1 * q / (r1 * q + r0 * (1 - q))))
        if abs(new - pi) < tol:
            pi = new
            break
        pi = new
    return float(np.clip(pi, 1e-5, 1 - 1e-5))


def label_shift_predictions(stays, ref):
    """Décalage d'intercept prédit sans label pour chaque hôpital tenu à l'écart :
    a = a_s + logit(pi_t) - logit(pi_s), avec pi_t estimé par EM ou par BBSE."""
    rows = []
    for h, g in stays.groupby("hospitalid"):
        f = int(g["fold"].iloc[0])
        s = ref.loc[f]
        q = oc.sigmoid(g["lp"].to_numpy() + s["a_s"])
        pi_em = em_prior(q, s["pi_s"])
        pi_bb = float(np.clip((q.mean() - s["m0"]) / max(s["m1"] - s["m0"], 1e-6), 1e-5, 1 - 1e-5))
        base = s["a_s"] - oc.logit(s["pi_s"])
        rows.append({"hospitalid": int(h), "fold": f, "a_EM": float(base + oc.logit(pi_em)),
                     "a_BBSE": float(base + oc.logit(pi_bb)), "a_source": float(s["a_s"]),
                     "pi_em": pi_em, "pi_bbse": pi_bb})
    return pd.DataFrame(rows).set_index("hospitalid").sort_index()


def as_prior(a_hat, index):
    return pd.DataFrame({"a_hat": pd.Series(a_hat, index=index).reindex(index).to_numpy(float),
                         "pred_var": np.nan, "tau2_raw": np.nan, "tau2_resid": np.nan, "hyper": np.nan, "mu": np.nan},
                        index=index)


def paired_abs(cal, prior_a, prior_b, n_boot=2000, seed=0):
    """Moyenne sur les hôpitaux de |résidu|(a) − |résidu|(b) (> 0 : b meilleur), IC bootstrap des hôpitaux."""
    ra = (cal["citl"] - prior_a["a_hat"].reindex(cal.index)).abs().to_numpy()
    rb = (cal["citl"] - prior_b["a_hat"].reindex(cal.index)).abs().to_numpy()
    return oc.boot_mean_diff(ra, rb, n_boot, seed)


# ----------------------------------------------------------------------------------------------
# Robustesse du régime 0
# ----------------------------------------------------------------------------------------------

def permutation_test(cal, D, cols, n_perm=500, seed=0, fixed_beta=None):
    """Permute les vecteurs de descripteurs entre hôpitaux (la structure entre descripteurs est gardée),
    refait toute la prédiction croisée, et compare R2_tau observé à sa distribution sous H0."""
    D = D.loc[cal.index]
    obs = oc.evaluate_prior(cal, oc.crossfit_prior(cal, D, cols, fixed_beta=fixed_beta))["R2_tau"]
    if not np.isfinite(obs):          # tau2 brut nul : aucune hétérogénéité à expliquer
        return float("nan"), np.full(n_perm, np.nan), float("nan")
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    vals = D.to_numpy()
    for b in range(n_perm):
        Dp = pd.DataFrame(vals[rng.permutation(len(D))], index=D.index, columns=D.columns)
        null[b] = oc.evaluate_prior(cal, oc.crossfit_prior(cal, Dp, cols, fixed_beta=fixed_beta))["R2_tau"]
    p = float((1 + np.sum(np.nan_to_num(null, nan=-np.inf) >= obs)) / (n_perm + 1))
    return float(obs), null, p


def repeated_partitions(cal, D, cols, n_rep=50, n_folds=5, seed=0, fixed_beta=None):
    """R2_tau quand le méta-modèle est croisé sur des partitions aléatoires des hôpitaux (les cibles a_h,
    elles, restent celles des plis du protocole)."""
    rng = np.random.default_rng(seed)
    out = []
    for r in range(n_rep):
        f = np.empty(len(cal), int)
        f[rng.permutation(len(cal))] = np.arange(len(cal)) % n_folds
        c2 = cal.copy()
        c2["fold"] = f
        out.append({"rep": r, **oc.evaluate_prior(cal, oc.crossfit_prior(c2, D, cols, fixed_beta=fixed_beta))})
    return pd.DataFrame(out)


def leave_one_hospital_out(cal, D, cols, fixed_beta=None):
    c2 = cal.copy()
    c2["fold"] = np.arange(len(cal))
    pr = oc.crossfit_prior(c2, D, cols, fixed_beta=fixed_beta)
    return oc.evaluate_prior(cal, pr), pr


def crossfit_transfer(cal_src, D_src, cal_tgt, D_tgt, cols):
    """Méta-modèle appris sur les a_h d'un modèle (source), appliqué aux descripteurs et évalué sur les a_h
    d'un autre modèle (cible), croisé par pli : la situation du test verrouillé, où le modèle final n'est pas
    celui des plis qui ont fourni les cibles d'apprentissage."""
    out = []
    for f in sorted(cal_tgt["fold"].unique()):
        tr = cal_src[cal_src["fold"] != f]
        te = cal_tgt.index[cal_tgt["fold"] == f]
        m = oc.SiteEB().fit(D_src.loc[tr.index, cols].to_numpy(float), tr["citl"].to_numpy(), tr["var_citl"].to_numpy())
        mean, var = m.predict(D_tgt.loc[te, cols].to_numpy(float))
        out.append(pd.DataFrame({"a_hat": mean, "pred_var": var, "tau2_raw": np.nan, "tau2_resid": m.tau2,
                                 "hyper": m.s2b, "mu": m.mu}, index=te))
    return pd.concat(out).sort_index()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()