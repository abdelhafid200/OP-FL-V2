"""
opcal_amend — procédure confirmatoire de l'amendement 1 et sa puissance (OP-Cal).

Généré par notebooks/06d_amendement_puissance.ipynb (étape 1) : modifier le notebook, pas ce fichier.
Les fonctions de test sont celles que le notebook 07 appliquera au test verrouillé ; la simulation de
puissance les appelle telles quelles, pour que puissance et analyse finale suivent la même procédure.

Tous les tests sont unilatéraux au seuil 2,5 % (équivalent à un IC bilatéral à 95 %).
  C1a : b > 0      (le signal de calibration des sites se transporte)
  C1b : b > 0,5    (amélioration : à moyenne correcte, l'erreur quadratique de calibration baisse de
                    (2b − 1)·Var(â) par rapport à la meilleure constante)
  C4  : γ > 0      (mécanisme Y* = D × Y : effet du log du taux de dosage, à score égal)
  C2  : Δℓ > 0     (gain de log-vraisemblance par patient d'OP-Cal par rapport à E0, aucune correction)
Famille 1 = {C1a, C4} (Holm) ; famille 2 = C1b puis C2 (séquence fixe), testée seulement si toute la
famille 1 est rejetée (gatekeeping séquentiel : risque global d'erreur contrôlé à 2,5 % unilatéral).
"""
import numpy as np
import pandas as pd
from scipy import optimize, stats

import opcal_feas as oc

ALPHA = 0.025   # unilatéral


# ----------------------------------------------------------------------------------------------
# C1 : méta-régression REML de a_h sur la prédiction gelée, IC de Knapp-Hartung
# ----------------------------------------------------------------------------------------------

def reml_metareg(y, x, v):
    """a_h = alpha + b·x_h + u_h + e_h, u_h ~ N(0, tau2), e_h ~ N(0, v_h) ; x_h = â_h − moyenne(â).
    tau2 par REML ; variance de b par Knapp-Hartung (sans troncature), t à k − 2 ddl."""
    y, x, v = (np.asarray(a, float) for a in (y, x, v))
    X = np.column_stack([np.ones(len(y)), x])

    def fit(t2):
        w = 1.0 / (v + t2)
        A = X.T @ (X * w[:, None])
        beta = np.linalg.solve(A, (X * w[:, None]).T @ y)
        return w, A, beta, y - X @ beta

    def nll(lt2):
        t2 = np.exp(lt2)
        w, A, beta, r = fit(t2)
        return 0.5 * (np.sum(np.log(v + t2)) + np.linalg.slogdet(A)[1] + np.sum(w * r ** 2))

    lt2 = optimize.minimize_scalar(nll, bounds=(np.log(1e-8), np.log(10.0)), method="bounded",
                                   options={"xatol": 1e-6}).x
    t2 = float(np.exp(lt2))
    w, A, beta, r = fit(t2)
    df = len(y) - 2
    s2 = float(np.sum(w * r ** 2) / df)
    se = float(np.sqrt(s2 * np.linalg.inv(A)[1, 1]))
    return {"alpha": float(beta[0]), "b": float(beta[1]), "se_b": se, "df": df, "tau2_resid": t2, "k": len(y)}


def p_slope(res, b0):
    """p unilatéral pour H0 : b ≤ b0 (Knapp-Hartung)."""
    return float(stats.t.sf((res["b"] - b0) / res["se_b"], res["df"]))


def ci_slope(res, level=0.95):
    q = stats.t.ppf(0.5 + level / 2, res["df"])
    return res["b"] - q * res["se_b"], res["b"] + q * res["se_b"]


def boot_slope(y, x, v, n_boot=2000, seed=0):
    """Sensibilité : bootstrap des hôpitaux, tau2 réestimé à chaque tirage."""
    y, x, v = (np.asarray(a, float) for a in (y, x, v))
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for i in range(n_boot):
        j = rng.integers(0, len(y), len(y))
        out[i] = reml_metareg(y[j], x[j] - x[j].mean(), v[j])["b"]
    return out


def c1_analysis(cal, ahat):
    """cal : citl, var_citl par hôpital ; ahat : prédiction gelée (même index)."""
    a = ahat.reindex(cal.index).to_numpy(float)
    res = reml_metareg(cal["citl"].to_numpy(), a - a.mean(), cal["var_citl"].to_numpy())
    lo, hi = ci_slope(res)
    raw = oc.random_effects(cal["citl"], cal["var_citl"])
    resid = oc.random_effects(cal["citl"].to_numpy() - a, cal["var_citl"].to_numpy())
    return {**res, "b_IC_bas": lo, "b_IC_haut": hi, "p_C1a": p_slope(res, 0.0), "p_C1b": p_slope(res, 0.5),
            "var_ahat": float(np.var(a)), "R2_tau": float(1 - resid["tau2"] / raw["tau2"]) if raw["tau2"] > 0 else np.nan}


# ----------------------------------------------------------------------------------------------
# C2 : gain de log-vraisemblance par patient (OP-Cal contre E0), bootstrap des hôpitaux
# ----------------------------------------------------------------------------------------------

def loglik(lp, y):
    p = np.clip(oc.sigmoid(lp), 1e-12, 1 - 1e-12)
    return float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def loglik_gain_by_hospital(stays, ahat, base=None):
    """Δℓ_h = ℓ(lp + â_h) − ℓ(lp + base_h) sur les patients d'évaluation ; base = 0 (E0) par défaut."""
    rows = []
    for h, g in stays.groupby("hospitalid"):
        lp, y = g["lp"].to_numpy(), g["y"].to_numpy(float)
        b0 = 0.0 if base is None else float(base.loc[h])
        rows.append({"hospitalid": h, "gain": loglik(lp + float(ahat.loc[h]), y) - loglik(lp + b0, y), "n": len(g)})
    return pd.DataFrame(rows).set_index("hospitalid")


def ratio_boot(num, den, n_boot=2000, seed=0):
    """Σ num / Σ den, IC percentile et p unilatéral (H0 : ≤ 0) par bootstrap des hôpitaux."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(num), (n_boot, len(num)))
    bs = num[idx].sum(1) / den[idx].sum(1)
    est = float(num.sum() / den.sum())
    return est, float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975)), float((1 + np.sum(bs <= 0)) / (n_boot + 1))


# ----------------------------------------------------------------------------------------------
# C4 : γ (log du taux de dosage), régression logistique avec offset, bootstrap des hôpitaux
# ----------------------------------------------------------------------------------------------

def gamma_test(stays, z_by_h, n_boot=2000, seed=0):
    """logit P(Y* = 1) = lp + alpha + γ·(z_h − moyenne) ; IC percentile et p unilatéral (H0 : γ ≤ 0)."""
    s = stays[stays["hospitalid"].isin(z_by_h.dropna().index)]
    z = s["hospitalid"].map(z_by_h).to_numpy(float)
    z = z - np.mean(z_by_h.dropna())
    g = s["hospitalid"].to_numpy()
    lp, y = s["lp"].to_numpy(), s["y"].to_numpy(float)
    est = oc.offset_slope_fit(lp, y, z)[1]
    hs = np.unique(g)
    rows = {h: np.flatnonzero(g == h) for h in hs}
    rng = np.random.default_rng(seed)
    bs = np.empty(n_boot)
    for b in range(n_boot):
        i = np.concatenate([rows[h] for h in rng.choice(hs, len(hs))])
        bs[b] = oc.offset_slope_fit(lp[i], y[i], z[i])[1]
    return {"gamma": float(est), "IC_bas": float(np.quantile(bs, 0.025)), "IC_haut": float(np.quantile(bs, 0.975)),
            "p_C4": float((1 + np.sum(bs <= 0)) / (n_boot + 1)), "IC_contient_1": bool(np.quantile(bs, 0.025) <= 1 <= np.quantile(bs, 0.975))}


# ----------------------------------------------------------------------------------------------
# Décision : Holm (famille 1), puis séquence fixe (famille 2)
# ----------------------------------------------------------------------------------------------

def decide(p_C1a, p_C4, p_C1b, p_C2, alpha=ALPHA):
    ps = sorted([("C1a", p_C1a), ("C4", p_C4)], key=lambda t: t[1])
    rej = {"C1a": False, "C4": False, "C1b": False, "C2": False}
    if ps[0][1] <= alpha / 2:
        rej[ps[0][0]] = True
        if ps[1][1] <= alpha:
            rej[ps[1][0]] = True
    if rej["C1a"] and rej["C4"]:
        if p_C1b <= alpha:
            rej["C1b"] = True
            if p_C2 <= alpha:
                rej["C2"] = True
    return rej


# ----------------------------------------------------------------------------------------------
# Simulation de puissance (mêmes fonctions que l'analyse finale)
# ----------------------------------------------------------------------------------------------

def _sample_lp(pools, n, rng):
    """lp d'un hôpital simulé : tirage avec remise dans les patients d'un hôpital de développement pris au hasard."""
    pool = pools[rng.integers(0, len(pools))]
    return pool[rng.integers(0, len(pool), n)]


def simulate_mortality(n_eval, lp_pools, b, tau2, var_ahat, n_rep=500, n_boot_c2=400, seed=0, k_lab=25, n0_fixed=10.0):
    """Réplications du test verrouillé : â_h ~ N(0, var_ahat) (dispersion des prédictions du développement),
    a_h = b·â_h + u_h avec Var(a_h) = tau2 (si b²·var_ahat ≤ tau2). Retourne p_C1a, p_C1b, p_C2, b estimé."""
    rng = np.random.default_rng(seed)
    K = len(n_eval)
    s2u = max(tau2 - b ** 2 * var_ahat, 1e-4)
    out = []
    for r in range(n_rep):
        ahat = rng.normal(0, np.sqrt(var_ahat), K)
        a = b * ahat + rng.normal(0, np.sqrt(s2u), K)
        c, v, gain = np.empty(K), np.empty(K), np.empty(K)
        reg = np.full((K, 3), np.nan)      # C3 tel que gelé : |CITL| déploiement (local, rétrécissement fixe, EB OP-Cal)
        for h in range(K):
            lp = _sample_lp(lp_pools, int(n_eval[h]), rng)
            y = (rng.random(len(lp)) < oc.sigmoid(lp + a[h])).astype(float)
            c[h], v[h] = oc.offset_fit(lp, y)
            gain[h] = loglik(lp + ahat[h], y) - loglik(lp, y)
            perm = rng.permutation(len(lp)); half = len(lp) // 2
            if half >= k_lab:
                L, Dp = perm[:half][:k_lab], perm[half:]
                res_ = lambda off: abs(oc.offset_fit(lp[Dp] + off, y[Dp])[0])
                reg[h] = (res_(oc.offset_fit(lp[L], y[L])[0]),
                          res_(oc.offset_fit(lp[L], y[L], prior_mean=0.0, prior_var=1.0 / n0_fixed)[0]),
                          res_(oc.offset_fit(lp[L], y[L], prior_mean=ahat[h], prior_var=s2u + 1e-3)[0]))
        res = reml_metareg(c, ahat - ahat.mean(), v)
        _, _, _, p2 = ratio_boot(gain, n_eval, n_boot_c2, int(rng.integers(1e9)))
        # C1 tel que gelé au 06c : R²_τ ≥ 0,25 et borne basse de l'IC du gain |CITL|(E1) − |CITL|(OP-Cal) > 0
        t_raw = oc.random_effects(c, v)["tau2"]
        r2 = 1 - oc.random_effects(c - ahat, v)["tau2"] / t_raw if t_raw > 0 else np.nan
        diff = np.abs(c) - np.abs(c - ahat)          # E1 = moyenne vraie, nulle dans la simulation
        bs = diff[rng.integers(0, K, (n_boot_c2, K))].mean(1)
        ok = np.isfinite(reg[:, 0])
        comp = 0 if np.nanmean(reg[:, 0]) <= np.nanmean(reg[:, 1]) else 1
        d3 = reg[ok, comp] - reg[ok, 2]
        c3 = bool(ok.sum() > 2 and np.quantile(d3[rng.integers(0, ok.sum(), (n_boot_c2, ok.sum()))].mean(1), 0.025) > 0)
        out.append({"rep": r, "b_est": res["b"], "p_C1a": p_slope(res, 0.0), "p_C1b": p_slope(res, 0.5), "p_C2": p2, "C3_gele": c3,
                    "C1_gele": bool(np.isfinite(r2) and r2 >= 0.25 and np.quantile(bs, 0.025) > 0), "R2_tau": r2,
                    "largeur_IC": 2 * stats.t.ppf(0.975, res["df"]) * res["se_b"]})
    return pd.DataFrame(out)


def simulate_gamma(n_eval48, lp_pools, z_pool, gamma, tau2_resid, n_rep=150, n_boot=300, seed=0):
    """Réplications de C4 : z_h tiré parmi les log taux de dosage du développement ; Y* ~ lp + γ·(z − z̄) + u_h."""
    rng = np.random.default_rng(seed)
    K = len(n_eval48)
    out = []
    for r in range(n_rep):
        z = rng.choice(z_pool, K)
        u = rng.normal(0, np.sqrt(max(tau2_resid, 1e-6)), K)
        parts = []
        for h in range(K):
            lp = _sample_lp(lp_pools, int(n_eval48[h]), rng)
            y = (rng.random(len(lp)) < oc.sigmoid(lp + gamma * (z[h] - z.mean()) + u[h])).astype(float)
            parts.append(pd.DataFrame({"hospitalid": h, "lp": lp, "y": y}))
        st = pd.concat(parts, ignore_index=True)
        t = gamma_test(st, pd.Series(z, index=range(K)), n_boot, int(rng.integers(1e9)))
        out.append({"rep": r, "gamma_est": t["gamma"], "p_C4": t["p_C4"], "evenements": int(st["y"].sum())})
    return pd.DataFrame(out)


def power_table(sim_m, sim_g, alpha=ALPHA, seed=0):
    """Puissance de chaque critère et de la procédure complète (réplications de mortalité appariées au hasard
    avec des réplications de C4, indépendantes)."""
    rng = np.random.default_rng(seed)
    pg = sim_g["p_C4"].to_numpy()[rng.integers(0, len(sim_g), len(sim_m))]
    dec = [decide(a, g, b, c, alpha) for a, g, b, c in zip(sim_m["p_C1a"], pg, sim_m["p_C1b"], sim_m["p_C2"])]
    return {"C1_gele": float(np.mean(sim_m["C1_gele"])), "C3_gele": float(np.mean(sim_m["C3_gele"])),
            "C1a_seul": float(np.mean(sim_m["p_C1a"] <= alpha)), "C1b_seul": float(np.mean(sim_m["p_C1b"] <= alpha)),
            "C2_seul": float(np.mean(sim_m["p_C2"] <= alpha)), "C4_seul": float(np.mean(sim_g["p_C4"] <= alpha)),
            "famille1": float(np.mean([d["C1a"] and d["C4"] for d in dec])),
            "C1b_confirme": float(np.mean([d["C1b"] for d in dec])), "C2_confirme": float(np.mean([d["C2"] for d in dec])),
            "b_estime_median": float(sim_m["b_est"].median()), "largeur_IC_mediane": float(sim_m["largeur_IC"].median()),
            "R2_tau_median": float(np.nanmedian(sim_m["R2_tau"]))}
