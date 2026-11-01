"""
opcal_v2eval — validation interne d'OP-Cal v2 (notebook 10), hôpitaux de développement uniquement.

Généré par notebooks/10_validation_v2.ipynb (étape 1) : modifier le notebook, pas ce fichier.
Spécification : OP-Cal_v2_specification.md, révision 0.3 (sections 5 à 7).

- fit_methods : les 8 méthodes de la section 6, apprises sur les sites d'entraînement d'un pli ; renvoie un
  prédicteur pour des sites tenus à l'écart (descripteurs ẑ et variances d'échantillonnage C, sans label).
- run_scheme : plis × (taille complète ou sous-échantillonnage) ; une observation par hôpital (moyenne sur les
  répétitions où il est tenu à l'écart).
- decide : bootstrap des hôpitaux avec maximum des comparateurs recalculé à chaque tirage.
"""
import numpy as np
import pandas as pd

import opcal_feas as oc
import opcal_amend as am
import opcal_size as osz
from opcal_gp import SiteGP

METHODS = ["E0", "E1", "v1", "v1_retreci", "v1_borne", "v1_debruite", "GP_sans_debruitage", "v2"]
COMPARATEURS = ["E1", "v1", "v1_retreci", "v1_borne"]          # maximum de la règle de décision (section 7)
KAPPA = np.round(np.linspace(0, 1, 11), 2)                     # grille du rétrécissement fixe
CASE_PREFIX = ("age_mean", "female_share", "src_", "dx_")


def site_gain(lp, y, a):
    return am.loglik(lp + a, y) - am.loglik(lp, y)


def kmeans(X, k, seed, n_init=10, iters=200):
    """k-moyennes (initialisation k-means++), meilleure inertie sur n_init départs ; sans label."""
    rng = np.random.default_rng(seed)
    best, best_in = None, np.inf
    for _ in range(n_init):
        cen = [X[rng.integers(len(X))]]
        for _ in range(1, k):
            d2 = np.min(((X[:, None] - np.array(cen)[None]) ** 2).sum(2), 1)
            cen.append(X[rng.choice(len(X), p=d2 / d2.sum())])
        cen = np.array(cen)
        for _ in range(iters):
            lab = np.argmin(((X[:, None] - cen[None]) ** 2).sum(2), 1)
            new = np.array([X[lab == j].mean(0) if (lab == j).any() else cen[j] for j in range(k)])
            if np.allclose(new, cen):
                break
            cen = new
        inertia = ((X - cen[lab]) ** 2).sum()
        if inertia < best_in and len(np.unique(lab)) == k:
            best, best_in = lab, inertia
    return best


def _denoise(Ztr, Ctr, Z, C):
    """Débruitage diagonal (spécification 2.A) en unités d'origine : z̄ = m + λ (ẑ − m), λ = s²/(s² + C)."""
    with np.errstate(all="ignore"):
        fill = np.nanmean(Ztr, 0)
    fill = np.where(np.isfinite(fill), fill, 0.0)
    Zt = np.where(np.isfinite(Ztr), Ztr, fill)
    m, var = Zt.mean(0), Zt.var(0)
    s2 = np.maximum(var - np.nan_to_num(Ctr).mean(0), 0.05 * np.maximum(var, 1e-12))
    out = lambda Zx, Cx: m + s2 / (s2 + np.nan_to_num(Cx)) * (np.where(np.isfinite(Zx), Zx, fill) - m)
    return out(Ztr, Ctr), out(Z, C) if Z is not None else None, out


def fit_methods(Ztr, Ctr, c, v, ev_tr, inner_seed):
    """Apprend les méthodes sur les sites d'entraînement. ev_tr : liste (lp, y) par site d'entraînement (pour le
    réglage du rétrécissement fixe, validation croisée interne à 5 plis). Renvoie (predict, info)."""
    e1 = oc.SiteEB().fit(np.zeros((len(c), 0)), c, v)
    v1 = oc.SiteEB().fit(Ztr, c, v)
    # rétrécissement fixe : κ réglé par validation croisée interne sur le gain de log-vraisemblance
    rng = np.random.default_rng(inner_seed)
    inner = np.empty(len(c), int)
    inner[rng.permutation(len(c))] = np.arange(len(c)) % 5
    gains = np.zeros(len(KAPPA))
    for g in range(5):
        a_, b_ = inner != g, inner == g
        mi = oc.SiteEB().fit(Ztr[a_], c[a_], v[a_])
        ahat = mi.predict(Ztr[b_])[0]
        idx = np.flatnonzero(b_)
        for k_, kap in enumerate(KAPPA):
            gains[k_] += sum(site_gain(*ev_tr[i], mi.mu + kap * (ah - mi.mu)) for i, ah in zip(idx, ahat))
    kappa = float(KAPPA[int(np.argmax(gains))])
    lo, hi = np.nanmin(Ztr, 0), np.nanmax(Ztr, 0)
    Zd_tr, _, den = _denoise(Ztr, Ctr, None, None)
    v1d = oc.SiteEB().fit(Zd_tr, c, v)
    gp0 = SiteGP(denoise=False).fit(Ztr, Ctr, c, v)
    gp = SiteGP().fit(Ztr, Ctr, c, v)
    info = {"kappa": kappa, "gp_converge": gp.converged, "gp_borne": gp.at_bound, "gp0_converge": gp0.converged,
            "tau2": gp.tau2, "s2L": gp.s2L, "s2R": gp.s2R, "ellR": gp.ellR, "ellL": gp.ell_L}

    def predict(Z, C):
        a1 = v1.predict(Z)[0]
        out = {"E0": np.zeros(len(Z)), "E1": np.full(len(Z), e1.mu), "v1": a1,
               "v1_retreci": v1.mu + kappa * (a1 - v1.mu),
               "v1_borne": v1.predict(np.where(np.isfinite(Z), np.clip(Z, lo, hi), Z))[0],
               "v1_debruite": v1d.predict(den(Z, C))[0],
               "GP_sans_debruitage": gp0.predict(Z, C)[0] if gp0.converged else a1,      # repli fixé à l'avance
               "v2": gp.predict(Z, C)[0] if gp.converged else a1}
        return out
    return predict, info


def run_scheme(arr, cal, cols, fold_sets, pairs=None, modes=(0,), seed=2026, log=print):
    """fold_sets : liste de tableaux de plis alignés sur cal.index. modes : nombres de tirages ; 0 = taille complète,
    k > 0 = k sous-échantillonnages des sites tenus à l'écart à la taille des hôpitaux verrouillés (tirages du 08).
    Les méthodes sont apprises une fois par pli et servent à tous les modes.
    Renvoie ({mode: par_hopital}, infos) ; par_hopital : moyennes par hôpital de G, n et de l'erreur débiaisée."""
    hosp = cal.index.to_numpy()
    H, M = len(hosp), len(METHODS)
    site = [arr.site(h) for h in hosp]
    Zf = np.array([s_[0] for s_ in site]); Cf = np.array([np.diag(s_[1]) for s_ in site])
    c, v = cal["citl"].to_numpy(), cal["var_citl"].to_numpy()
    evf = [arr.eval(h) for h in hosp]
    acc = {md: {"G": np.zeros((H, M)), "N": np.zeros(H), "SQ": np.zeros((H, M)), "K": np.zeros(H)} for md in modes}
    infos = []
    for r, fold in enumerate(fold_sets):
        preds = {}
        for f in np.unique(fold):
            tr = np.flatnonzero(fold != f)
            p_, inf = fit_methods(Zf[tr], Cf[tr], c[tr], v[tr], [evf[i] for i in tr], seed + 1000 * r + int(f))
            preds[f] = p_
            infos.append({"repetition": r, "pli": int(f), **inf})
        for md in modes:
            a_ = acc[md]
            for d in ([None] if md == 0 else range(md)):
                if d is None:
                    Z, C, tg, ev = Zf, Cf, np.column_stack([c, v]), evf
                else:
                    rng = np.random.default_rng([seed, r, d])
                    Zs, Cs, tg, (lp, y, row), _ = osz._draw(arr, hosp, pairs, 1.0, osz.SCENARIOS["tout"], rng)
                    Z, C = Zs, np.array([np.diag(x) for x in Cs])
                    ev = [(lp[row == i], y[row == i]) for i in range(H)]
                for f, pr in preds.items():
                    te = np.flatnonzero(fold == f)
                    out = pr(Z[te], C[te])
                    for j, mth in enumerate(METHODS):
                        for i, a in zip(te, out[mth]):
                            a_["G"][i, j] += site_gain(*ev[i], a)
                            a_["SQ"][i, j] += (tg[i, 0] - a) ** 2 - tg[i, 1]
                    for i in te:
                        a_["N"][i] += len(ev[i][0]); a_["K"][i] += 1
        log(f"  répétition {r + 1}/{len(fold_sets)} terminée")
    ev_n = np.array([e[1].sum() for e in evf])
    per = {md: {"G": a_["G"] / a_["K"][:, None], "n": a_["N"] / a_["K"], "SQ": a_["SQ"] / a_["K"][:, None], "evenements": ev_n}
           for md, a_ in acc.items()}
    return per, pd.DataFrame(infos)


def scheme_table(per, min_events=10):
    """Δℓ (poids patients et poids égaux par hôpital) et erreur quadratique débiaisée, par méthode."""
    G, n = per["G"], per["n"]
    keep = per["evenements"] >= min_events
    return pd.DataFrame({"Δℓ (par patient)": G.sum(0) / n.sum(), "Δℓ (moyenne par hôpital)": (G / n[:, None]).mean(0),
                         "MSE débiaisé": per["SQ"][keep].mean(0)}, index=METHODS)


def boot_max(per, n_boot=2000, seed=2026):
    """D = Δℓ(v2) − max des comparateurs, maximum recalculé à chaque tirage ; et Δℓ(v2) − Δℓ(v1)."""
    G, n = per["G"], per["n"]
    j = {m: i for i, m in enumerate(METHODS)}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(n), (n_boot, len(n)))
    dl = G[idx].sum(1) / n[idx].sum(1)[:, None]                                     # (B, M)
    Dmax = dl[:, j["v2"]] - dl[:, [j[m] for m in COMPARATEURS]].max(1)
    Dv1 = dl[:, j["v2"]] - dl[:, j["v1"]]
    full = G.sum(0) / n.sum()
    est_max = full[j["v2"]] - max(full[j[m]] for m in COMPARATEURS)
    return {"D_max": est_max, "D_max_bas": np.quantile(Dmax, 0.025), "D_max_haut": np.quantile(Dmax, 0.975),
            "meilleur_comparateur": max(COMPARATEURS, key=lambda m: full[j[m]]),
            "D_v1": full[j["v2"]] - full[j["v1"]], "D_v1_bas": np.quantile(Dv1, 0.025), "D_v1_haut": np.quantile(Dv1, 0.975)}
