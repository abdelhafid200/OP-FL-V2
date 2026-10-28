"""
opcal_amend — procédure confirmatoire de l'amendement 1 et sa puissance (OP-Cal).

Généré par notebooks/06d_amendement_puissance.ipynb (étape 1) : modifier le notebook, pas ce fichier.
Les fonctions de test sont celles que le notebook 07 appliquera au test verrouillé ; la simulation de
puissance les appelle telles quelles, pour que puissance et analyse finale suivent la même procédure.

Tous les tests sont unilatéraux au seuil 2,5 % (équivalent à un IC bilatéral à 95 %).
  C1a : b > 0      (le signal de calibration des sites se transporte) — affirmation principale
  C1b : b > 0,5    (sous le modèle linéaire et à moyenne correcte, l'erreur quadratique de calibration baisse de
                    (2b − 1)·Var(â) par rapport à la meilleure constante, qui est une référence théorique)
  C2  : Δℓ > 0     (gain de log-vraisemblance par patient d'OP-Cal contre E0, aucune correction ; comparaison
                    distincte de C1b : elle inclut aussi le décalage moyen)
  C4  : U > 0      (mécanisme Y* = D × Y : test exact par permutation du score du log du taux de dosage)
Multiplicité : procédure graphique (Bretz et al. 2009), voir GRAPH_WEIGHTS et GRAPH_EDGES.
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
# C4 : test exact par permutation (statistique du score) ; γ estimé à part (descriptif)
# ----------------------------------------------------------------------------------------------

def _o_minus_e(stays, z_by_h):
    """O_h − E_h par hôpital sous le modèle nul logit P(Y* = 1) = lp + alpha (alpha commun, MLE avec offset)."""
    s = stays[stays["hospitalid"].isin(z_by_h.dropna().index)]
    lp, y = s["lp"].to_numpy(), s["y"].to_numpy(float)
    alpha = oc.offset_fit(lp, y)[0]
    oe = pd.Series(y - oc.sigmoid(lp + alpha)).groupby(s["hospitalid"].to_numpy()).sum()
    return oe, z_by_h.reindex(oe.index).to_numpy(float)


def gamma_score_test(stays, z_by_h, n_perm=2000, seed=0):
    """C4 : U = Σ_h (z_h − z̄)·(O_h − E_h). « Les hôpitaux qui dosent plus ont plus d'événements enregistrés que prévu. »
    p = (1 + #{U* ≥ U}) / (B + 1), z permuté entre hôpitaux : test exact si le taux de dosage est indépendant des
    écarts O − E sous H0, quel que soit le nombre d'événements par hôpital."""
    oe, z = _o_minus_e(stays, z_by_h)
    R, zc = oe.to_numpy(), z - z.mean()
    U = float(zc @ R)
    rng = np.random.default_rng(seed)
    perms = np.argsort(rng.random((n_perm, len(zc))), axis=1)
    Ustar = zc[perms] @ R
    return {"U": U, "p_C4": float((1 + np.sum(Ustar >= U)) / (n_perm + 1)), "hopitaux": len(zc)}


def gamma_estimate(stays, z_by_h, n_boot=2000, seed=0):
    """γ (logistique avec offset lp, z centré) et IC percentile par bootstrap des hôpitaux : estimation, pas test."""
    s = stays[stays["hospitalid"].isin(z_by_h.dropna().index)]
    z = s["hospitalid"].map(z_by_h).to_numpy(float) - np.mean(z_by_h.dropna())
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
    lo, hi = float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))
    return {"gamma": float(est), "IC_bas": lo, "IC_haut": hi, "IC_contient_1": bool(lo <= 1 <= hi)}


# ----------------------------------------------------------------------------------------------
# Multiplicité : procédure graphique (Bretz, Maurer, Brannath et Posch 2009), unilatérale à 2,5 %
#   poids initiaux : C1a 1/2, C4 1/2 ; arêtes C4 → C1a, C1a → C1b, C1b → C2, C2 → C4 (poids 1).
#   Les conclusions de mortalité ne dépendent pas de C4 : si C4 échoue, C1a, C1b et C2 sont testés à 1,25 % ;
#   si C4 est rejeté, son seuil passe à C1a (2,5 %). Contrôle fort du risque global d'erreur (Bonferroni pondéré).
# ----------------------------------------------------------------------------------------------

GRAPH_WEIGHTS = {"C1a": 0.5, "C4": 0.5, "C1b": 0.0, "C2": 0.0}
GRAPH_EDGES = {("C4", "C1a"): 1.0, ("C1a", "C1b"): 1.0, ("C1b", "C2"): 1.0, ("C2", "C4"): 1.0}


def graph_test(p, weights=GRAPH_WEIGHTS, edges=GRAPH_EDGES, alpha=ALPHA):
    """Algorithme 1 de Bretz et al. (2009). p : dict hypothèse -> p unilatéral. Retourne dict hypothèse -> rejetée."""
    H = list(weights)
    w = dict(weights)
    G = {(i, j): edges.get((i, j), 0.0) for i in H for j in H if i != j}
    active, rej = set(H), {h: False for h in H}
    while True:
        cand = [h for h in active if w[h] > 0 and p[h] <= w[h] * alpha]
        if not cand:
            return rej
        i = min(cand, key=lambda h: p[h])
        rej[i] = True
        active.discard(i)
        for j in active:
            w[j] += w[i] * G[(i, j)]
        w[i] = 0.0
        newG = {}
        for j in active:
            for k in active:
                if j != k:
                    d = 1.0 - G[(j, i)] * G[(i, j)]
                    newG[(j, k)] = (G[(j, k)] + G[(j, i)] * G[(i, k)]) / d if d > 1e-12 else 0.0
        G.update(newG)


# ----------------------------------------------------------------------------------------------
# Simulation de puissance : mêmes fonctions et mêmes nombres de tirages que l'analyse finale
# ----------------------------------------------------------------------------------------------

def _sample_lp(pools, n, rng):
    """lp d'un hôpital simulé : tirage avec remise dans les patients d'un hôpital de développement pris au hasard."""
    pool = pools[rng.integers(0, len(pools))]
    return pool[rng.integers(0, len(pool), n)]


def simulate_mortality(n_eval, lp_pools, b, tau2, var_ahat, n_rep=500, n_boot=2000, seed=0, k_lab=25, n0_fixed=10.0):
    """Réplications du test verrouillé : â_h ~ N(0, var_ahat) (dispersion des prédictions du développement),
    a_h = b·â_h + u_h avec Var(a_h) = tau2 (si b²·var_ahat ≤ tau2). p de C1a, C1b (Knapp-Hartung), C2 (bootstrap
    de n_boot hôpitaux, comme l'analyse finale), et puissance des C1 et C3 tels que gelés au 06c."""
    rng = np.random.default_rng(seed)
    K = len(n_eval)
    s2u = max(tau2 - b ** 2 * var_ahat, 1e-4)
    out = []
    for r in range(n_rep):
        ahat = rng.normal(0, np.sqrt(var_ahat), K)
        a = b * ahat + rng.normal(0, np.sqrt(s2u), K)
        c, v, gain = np.empty(K), np.empty(K), np.empty(K)
        reg = np.full((K, 3), np.nan)      # C3 gelé : |CITL| déploiement (local, rétrécissement fixe, EB OP-Cal)
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
        _, _, _, p2 = ratio_boot(gain, n_eval, n_boot, int(rng.integers(1e9)))
        t_raw = oc.random_effects(c, v)["tau2"]
        r2 = 1 - oc.random_effects(c - ahat, v)["tau2"] / t_raw if t_raw > 0 else np.nan
        diff = np.abs(c) - np.abs(c - ahat)          # C1 gelé : E1 = moyenne vraie (nulle dans la simulation)
        bs = diff[rng.integers(0, K, (n_boot, K))].mean(1)
        ok = np.isfinite(reg[:, 0])
        comp = 0 if np.nanmean(reg[:, 0]) <= np.nanmean(reg[:, 1]) else 1
        d3 = reg[ok, comp] - reg[ok, 2]
        c3 = bool(ok.sum() > 2 and np.quantile(d3[rng.integers(0, ok.sum(), (n_boot, ok.sum()))].mean(1), 0.025) > 0)
        out.append({"rep": r, "b_est": res["b"], "p_C1a": p_slope(res, 0.0), "p_C1b": p_slope(res, 0.5), "p_C2": p2, "C3_gele": c3,
                    "C1_gele": bool(np.isfinite(r2) and r2 >= 0.25 and np.quantile(bs, 0.025) > 0), "R2_tau": r2,
                    "largeur_IC": 2 * stats.t.ppf(0.975, res["df"]) * res["se_b"]})
    return pd.DataFrame(out)


def simulate_gamma(n_eval48, lp_pools, z_pool, gamma, tau2_resid, n_rep=500, n_perm=2000, seed=0):
    """Réplications de C4 : z_h tiré parmi les log taux de dosage du développement ; Y* ~ lp + γ·(z − z̄) + u_h.
    Test exact par permutation (n_perm, comme l'analyse finale) ; γ estimé par MLE (sans bootstrap)."""
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
        zs = pd.Series(z, index=range(K))
        t = gamma_score_test(st, zs, n_perm, int(rng.integers(1e9)))
        g_est = oc.offset_slope_fit(st["lp"].to_numpy(), st["y"].to_numpy(float),
                                    st["hospitalid"].map(zs).to_numpy(float) - z.mean())[1]
        out.append({"rep": r, "gamma_est": g_est, "p_C4": t["p_C4"], "evenements": int(st["y"].sum())})
    return pd.DataFrame(out)


def mc_ci(k, n, level=0.95):
    """IC exact (Clopper-Pearson) d'une proportion de Monte Carlo."""
    a = (1 - level) / 2
    lo = stats.beta.ppf(a, k, n - k + 1) if k > 0 else 0.0
    hi = stats.beta.ppf(1 - a, k + 1, n - k) if k < n else 1.0
    return float(lo), float(hi)


def procedure_table(sim_m, sim_g, true_null=(), alpha=ALPHA, seed=0):
    """Procédure complète (graphe) sur des réplications de mortalité appariées au hasard avec des réplications de C4
    (indépendantes). Puissance de chaque hypothèse, puissance de chaque test seul, et proportion de réplications avec
    au moins un rejet à tort parmi `true_null` (risque global d'erreur, IC de Clopper-Pearson)."""
    rng = np.random.default_rng(seed)
    pg = sim_g["p_C4"].to_numpy()[rng.integers(0, len(sim_g), len(sim_m))]
    dec = [graph_test({"C1a": a, "C4": g, "C1b": b, "C2": c}, alpha=alpha)
           for a, g, b, c in zip(sim_m["p_C1a"], pg, sim_m["p_C1b"], sim_m["p_C2"])]
    n = len(dec)
    out = {"C1_gele": float(np.mean(sim_m["C1_gele"])), "C3_gele": float(np.mean(sim_m["C3_gele"])),
           "C1a_seul": float(np.mean(sim_m["p_C1a"] <= alpha)), "C1b_seul": float(np.mean(sim_m["p_C1b"] <= alpha)),
           "C2_seul": float(np.mean(sim_m["p_C2"] <= alpha)), "C4_seul": float(np.mean(sim_g["p_C4"] <= alpha))}
    for h in ("C1a", "C4", "C1b", "C2"):
        out[f"{h}_confirme"] = float(np.mean([d[h] for d in dec]))
    if true_null:
        k = int(sum(any(d[h] for h in true_null) for d in dec))
        out["erreur_globale"] = k / n
        out["erreur_globale_IC_bas"], out["erreur_globale_IC_haut"] = mc_ci(k, n)
    out.update({"b_estime_median": float(sim_m["b_est"].median()), "largeur_IC_mediane": float(sim_m["largeur_IC"].median()),
                "R2_tau_median": float(np.nanmedian(sim_m["R2_tau"]))})
    return out
