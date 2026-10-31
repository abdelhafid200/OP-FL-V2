"""
opcal_size — analyse exploratoire du notebook 08 : la petite taille des hôpitaux verrouillés explique-t-elle la baisse
de la pente b entre le développement et le test verrouillé ?

Généré par notebooks/08_taille_sites.ipynb (étape 1) : modifier le notebook, pas ce fichier.
Hôpitaux de développement uniquement. Des hôpitaux verrouillés, seuls les effectifs du manifest (n_train, n_val + n_test)
sont utilisés, pour fixer la taille des sous-échantillons.

- DevArrays : recalcule les descripteurs gelés sur n'importe quel sous-ensemble de séjours, avec les règles de
  opcal_feas.site_descriptors et du notebook 01, et donne leur covariance d'échantillonnage (fonctions d'influence,
  méthode delta). Ce calcul n'utilise aucun label : un hôpital pourrait le faire localement.
- fit_folds / predict : SiteEB par pli, appris à taille complète comme opcal_feas.crossfit_prior ; correction de
  fiabilité de â (étape 5, fixée avant l'analyse, sans paramètre à régler).
- run : sous-échantillonnage répété, puis critères du protocole (c1_analysis, gain de log-vraisemblance, |CITL|).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

import opcal_feas as oc
import opcal_amend as am

AVAIL_MIN_COVERAGE = 0.05          # notebook 01 : variable disponible si >= 5 % des séjours train l'observent
OBS_SUBSET = ("test_rate_lactate", "test_rate_creatinine", "intensity_lactate", "intensity_creatinine")
MODEL = ("mean_lp", "sd_lp")
# scénario -> (split train sous-échantillonné, groupe « modèle » sur l'évaluation sous-échantillonnée,
#              cibles a_h et gains sur l'évaluation sous-échantillonnée)
SCENARIOS = {"complet": (False, False, False), "descripteurs": (True, False, False),
             "groupe_modele": (False, True, False), "cibles": (False, False, True), "tout": (True, True, True)}


def _subset_mean(z, P, k, sel, x):
    """Moyenne de x sur les séjours `sel` (valeurs finies) et sa fonction d'influence (estimateur de ratio)."""
    s = sel & np.isfinite(x)
    if s.any():
        zk = float(x[s].mean())
        z[k] = zk
        P[:, k] = np.where(s, x - zk, 0.0) / s.mean()


class DevArrays:
    """Tableaux par hôpital de développement.
    st : stay_labels (index stay_id, développement) ; cohort : cohort_final (développement) avec patientunitstayid,
    age_num, gender, apacheadmissiondx, unittype, unitadmitsource ; transfer : stay_id, hospitalid, lp, y (patients
    d'évaluation, modèle du pli) ; struct : descripteurs de structure (index hospitalid) ; cols : descripteurs gelés."""

    def __init__(self, data_dir, st, cohort, transfer, struct, cols):
        data_dir = Path(data_dir)
        feats = json.loads((data_dir / "features.json").read_text(encoding="utf-8"))["features"]
        fidx = {f: i for i, f in enumerate(feats)}
        self.cols = list(cols)
        pos = self.pos = {c: i for i, c in enumerate(self.cols)}
        groups = [(n, [fidx[v] for v in vs if v in fidx]) for n, vs in oc.OBS_COV.items()]
        groups.append(("mean_coverage", list(range(len(feats)))))
        self.groups = [(pos[n], ii) for n, ii in groups if n in pos and ii]
        self.share_cols = [c for c in self.cols if c == "female_share" or c.startswith(("unit_", "src_", "dx_"))]
        self.share_idx = np.array([pos[c] for c in self.share_cols], int)
        known = set(oc.OBS_COV) | {"n_unavailable", "mean_coverage", "age_mean", *OBS_SUBSET, *MODEL, *self.share_cols}
        self.struct_cols = [c for c in self.cols if c not in known]
        unknown = [c for c in self.struct_cols if not c.startswith(("beds_cat", "teaching", "region_")) or c not in struct.columns]
        assert not unknown, f"Descripteurs gelés de nature inconnue (ni patient ni structure) : {unknown}"
        self.struct_idx = np.array([pos[c] for c in self.struct_cols], int)
        self.model_idx = np.array([pos[c] for c in MODEL if c in pos], int)
        coh = cohort.set_index("patientunitstayid")
        self.H, self._full = {}, {}
        for h, ev in transfer.groupby("hospitalid"):
            h = int(h)
            z = np.load(data_dir / "clients" / f"hospital_{h}.npz")
            tr = np.asarray(z["split"]) == 0
            ids = np.asarray(z["stay_id"])[tr]
            obs = np.asarray(z["M"])[tr].any(axis=1)                          # (n_train, F) : observé en 24 h
            c = coh.reindex(ids)
            unit = "unit_" + c["unittype"].astype(str).str.lower().str.replace(r"[^0-9a-z]+", "_", regex=True).str.strip("_")
            src = c["unitadmitsource"].map(oc.SRC_GROUPS).fillna("src_other")
            dx = c["apacheadmissiondx"].fillna("").astype(str).str.lower()

            def share(col):
                if col == "female_share":
                    return (c["gender"] == "Female").to_numpy(float)
                if col.startswith("unit_"):
                    return (unit == col).to_numpy(float)
                if col.startswith("src_"):
                    return (src == col).to_numpy(float)
                return dx.str.contains(oc.DX_KEYS[col], regex=True).to_numpy(float)

            s = st.reindex(ids)
            ev = ev.sort_values("stay_id")
            self.H[h] = {
                "obs": obs, "G": np.column_stack([obs[:, ii].mean(1) for _, ii in self.groups]),
                "S": np.column_stack([share(col) for col in self.share_cols]) if self.share_cols else np.zeros((len(ids), 0)),
                "age": c["age_num"].to_numpy(float),
                "p48": s["present48"].fillna(False).astype(bool).to_numpy(),
                "obs_la": s["obs_la"].astype(float).to_numpy(), "la_rate": s["la_rate"].astype(float).to_numpy(),
                "crb": s["cr_base"].notna().to_numpy(),
                "obs_cr": s["obs_cr"].astype(float).to_numpy(), "cr_rate": s["cr_rate"].astype(float).to_numpy(),
                "struct": struct.loc[h, self.struct_cols].to_numpy(float),
                "lp": ev["lp"].to_numpy(float), "y": ev["y"].to_numpy(float)}

    def n_tr(self, h):
        return len(self.H[h]["obs"])

    def n_ev(self, h):
        return len(self.H[h]["lp"])

    def _train_part(self, h, itr):
        a, m, p = self.H[h], len(itr), len(self.cols)
        z, P = np.full(p, np.nan), np.zeros((m, p))
        cov_raw = a["obs"][itr].mean(0)
        cov = np.round(cov_raw, 4)                                            # comme local_stats.json
        G = a["G"][itr]
        for j, (k, ii) in enumerate(self.groups):
            z[k] = cov[ii].mean()
            P[:, k] = G[:, j] - G[:, j].mean()
        if "n_unavailable" in self.pos:                                       # discret : pas de variance delta
            z[self.pos["n_unavailable"]] = float(np.sum(cov_raw < AVAIL_MIN_COVERAGE))
        p48 = a["p48"][itr]
        for name, sel, x in (("test_rate_lactate", p48, a["obs_la"][itr]),
                             ("test_rate_creatinine", p48 & a["crb"][itr], a["obs_cr"][itr]),
                             ("intensity_lactate", p48, a["la_rate"][itr]),
                             ("intensity_creatinine", p48, a["cr_rate"][itr]),
                             ("age_mean", np.ones(m, bool), a["age"][itr])):
            if name in self.pos:
                _subset_mean(z, P, self.pos[name], sel, x)
        if len(self.share_idx):
            S = a["S"][itr]
            mu = S.mean(0)
            z[self.share_idx] = mu
            P[:, self.share_idx] = S - mu
        z[self.struct_idx] = a["struct"]
        return z, P.T @ P / m ** 2

    def _eval_part(self, h, iev):
        lp = self.H[h]["lp"][iev]
        k, p = len(lp), len(self.cols)
        z, P = np.full(p, np.nan), np.zeros((k, p))
        mu, sd = float(lp.mean()), float(lp.std())
        if "mean_lp" in self.pos:
            z[self.pos["mean_lp"]] = mu
            P[:, self.pos["mean_lp"]] = lp - mu
        if "sd_lp" in self.pos:
            z[self.pos["sd_lp"]] = sd
            P[:, self.pos["sd_lp"]] = ((lp - mu) ** 2 - sd ** 2) / (2 * sd) if sd > 0 else 0.0
        return z, P.T @ P / k ** 2

    def site(self, h, itr=None, iev=None):
        """Descripteurs gelés (ordre `cols`) et leur covariance d'échantillonnage, pour un sous-ensemble des séjours
        train (itr) et des patients d'évaluation (iev, groupe « modèle ») ; None = tous."""
        if h not in self._full:
            self._full[h] = (self._train_part(h, np.arange(self.n_tr(h))), self._eval_part(h, np.arange(self.n_ev(h))))
        (zt, Ct), (ze, Ce) = self._full[h]
        if itr is not None:
            zt, Ct = self._train_part(h, itr)
        if iev is not None:
            ze, Ce = self._eval_part(h, iev)
        z = zt.copy()
        z[self.model_idx] = ze[self.model_idx]
        return z, Ct + Ce

    def target(self, h, iev=None):
        """a_h (CITL) et sa variance, comme opcal_feas.hospital_calibration."""
        lp, y = self.eval(h, iev)
        return oc.citl(lp, y)

    def eval(self, h, iev=None):
        a = self.H[h]
        return (a["lp"], a["y"]) if iev is None else (a["lp"][iev], a["y"][iev])


def make_partitions(n, n_folds, n_part, seed):
    """Partitions aléatoires des hôpitaux en plis, générées comme au notebook 06d."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_part):
        f = np.empty(n, int)
        f[rng.permutation(n)] = np.arange(n) % n_folds
        out.append(f)
    return out


def fit_folds(D, cal, fold, cols, C_full):
    """Pour chaque pli : SiteEB (descripteurs gelés) et E1 (moyenne REML) appris sur les hôpitaux des autres plis, à
    taille complète, exactement comme opcal_feas.crossfit_prior. Garde aussi ce qu'il faut pour la correction :
    w = β / σ (poids linéaires de â), q̄ = bruit moyen de â chez les hôpitaux d'entraînement et
    σ²_a = variance de â entre hôpitaux d'entraînement − q̄ (variance du signal)."""
    hosp = cal.index.to_numpy()
    fits = []
    for f in sorted(np.unique(fold)):
        tr, te = hosp[fold != f], hosp[fold == f]
        c, v = cal.loc[tr, "citl"].to_numpy(), cal.loc[tr, "var_citl"].to_numpy()
        Ztr = D.loc[tr, cols].to_numpy(float)
        m = oc.SiteEB().fit(Ztr, c, v)
        e1 = oc.SiteEB().fit(np.zeros((len(tr), 0)), c, v)
        w = m.beta / m.sz
        q_tr = np.einsum("i,hij,j->h", w, np.stack([C_full[h] for h in tr]), w)
        a_tr = m.predict(Ztr)[0]
        fits.append({"rows": np.searchsorted(hosp, te), "m": m, "e1": float(e1.mu), "w": w, "qbar": float(q_tr.mean()),
                     "s2a": max(float(np.var(a_tr, ddof=1) - q_tr.mean()), 0.0)})
    return fits


def reliability(f, q):
    """λ_h = (σ²_a + q̄) / (σ²_a + q_h). Le méta-modèle a été appris sur des descripteurs mesurés avec le bruit du
    développement (q̄) : il est déjà calibré pour ce niveau de bruit, et λ_h = 1 pour un hôpital de même taille.
    Un hôpital plus petit (q_h > q̄) a des prédictions rapprochées de μ (calibration de régression)."""
    tot = f["s2a"] + q
    return np.divide(f["s2a"] + f["qbar"], tot, out=np.ones_like(tot, dtype=float), where=tot > 0)


def predict(fits, Z, C=None):
    """â (OP-Cal), â corrigé (si C), E1 et bruit q_h = w' C_h w, pour des hôpitaux rangés comme cal.index.
    Correction de fiabilité : â_corr = μ + λ_h (â − μ), λ_h = (σ²_a + q̄) / (σ²_a + q_h) (voir reliability)."""
    H = len(Z)
    a, ac, e1, q = (np.full(H, np.nan) for _ in range(4))
    for f in fits:
        r = f["rows"]
        a[r] = f["m"].predict(Z[r])[0]
        e1[r] = f["e1"]
        if C is not None:
            q[r] = np.einsum("i,hij,j->h", f["w"], C[r], f["w"])
            ac[r] = f["m"].mu + reliability(f, q[r]) * (a[r] - f["m"].mu)
    return a, ac, e1, q


def metrics(c, v, a, e1, ev):
    """Critères du protocole pour une réplication. c, v : cibles ; ev : (lp, y, rang de l'hôpital) des patients
    d'évaluation. Signal : b, p de C1a, R²_τ. Correction : p de C1b, gains de log-vraisemblance, |CITL|."""
    r = am.c1_analysis(pd.DataFrame({"citl": c, "var_citl": v}), pd.Series(a))
    lp, y, row = ev
    n, l_a = len(lp), am.loglik(lp + a[row], y)
    out = {k: r[k] for k in ("b", "se_b", "p_C1a", "p_C1b", "R2_tau", "var_ahat")}
    out.update(gain_E0=(l_a - am.loglik(lp, y)) / n, gain_E1=(l_a - am.loglik(lp + e1[row], y)) / n,
               abs_opcal=float(np.mean(np.abs(c - a))), abs_E0=float(np.mean(np.abs(c))),
               abs_E1=float(np.mean(np.abs(c - e1))), gain_theorique=(2 * r["b"] - 1) * r["var_ahat"])
    return out


def _draw(arr, hosp, pairs, scale, flags, rng):
    """Un tirage : chaque hôpital reçoit les effectifs (n_train, n_eval) d'un hôpital verrouillé pris au hasard, × scale.
    Les nombres aléatoires sont tirés dans le même ordre pour tous les scénarios : tirages appariés."""
    sub_tr, sub_mod, sub_tgt = flags
    Z, C, tg, lps, ys, rows, ntot, capped = [], [], [], [], [], [], [], []
    for i, h in enumerate(hosp):
        nt_av, ne_av = arr.n_tr(h), arr.n_ev(h)
        want = np.round(pairs[rng.integers(len(pairs))] * scale).astype(int)
        nt, ne = int(min(max(want[0], 2), nt_av)), int(min(max(want[1], 2), ne_av))
        itr = np.sort(rng.choice(nt_av, nt, replace=False))
        iev = np.sort(rng.choice(ne_av, ne, replace=False))
        z, c_ = arr.site(h, itr if sub_tr else None, iev if sub_mod else None)
        ie = iev if sub_tgt else None
        lp, y = arr.eval(h, ie)
        Z.append(z), C.append(c_), tg.append(oc.citl(lp, y)), lps.append(lp), ys.append(y), rows.append(np.full(len(lp), i))
        ntot.append((nt if sub_tr else nt_av) + (ne if (sub_mod or sub_tgt) else ne_av))
        capped.append(bool((sub_tr and want[0] > nt_av) or ((sub_mod or sub_tgt) and want[1] > ne_av)))
    ev = (np.concatenate(lps), np.concatenate(ys), np.concatenate(rows))
    return np.array(Z), np.stack(C), np.array(tg), ev, {"sejours_median": float(np.median(ntot)), "plafonnes": float(np.mean(capped))}


def run(arr, cal, D_full, fits_list, pairs, configs, n_draw, seed, correction=False):
    """Une ligne par (configuration, tirage, partition).
    configs : (scénario, échelle) ; échelle None = taille complète, un seul tirage.
    pairs : effectifs (n_train, n_val + n_test) des hôpitaux verrouillés.
    lambda_eff = Cov(â complet, â) / Var(â) : atténuation prédite sans label (erreur de mesure classique).
    bruit_ratio (avec correction) : moyenne de (â − â complet)² / (q − q complet), ≈ 1 si le modèle de bruit est juste."""
    hosp = cal.index.to_numpy()
    Zf = D_full.loc[hosp, arr.cols].to_numpy(float)
    Cf = np.stack([arr.site(h)[1] for h in hosp])
    tg_f = np.array([arr.target(h) for h in hosp])
    ev_f = (np.concatenate([arr.eval(h)[0] for h in hosp]), np.concatenate([arr.eval(h)[1] for h in hosp]),
            np.concatenate([np.full(arr.n_ev(h), i) for i, h in enumerate(hosp)]))
    n_full = float(np.median([arr.n_tr(h) + arr.n_ev(h) for h in hosp]))
    base = [predict(fits, Zf, Cf) for fits in fits_list]
    out = []
    for scen, scale in configs:
        name = scen if scale is None else f"{scen} ×{scale:g}"
        for d in range(1 if scale is None else n_draw):
            if scale is None:
                Z, C, tg, ev, info = Zf, Cf, tg_f, ev_f, {"sejours_median": n_full, "plafonnes": 0.0}
            else:
                rng = np.random.default_rng([seed, d, int(round(scale * 100))])
                Z, C, tg, ev, info = _draw(arr, hosp, pairs, scale, SCENARIOS[scen], rng)
            for p, fits in enumerate(fits_list):
                a, ac, e1, q = predict(fits, Z, C if correction else None)
                a0, q0 = base[p][0], base[p][3]
                row = {"config": name, "scenario": scen, "echelle": np.nan if scale is None else scale, "tirage": d,
                       "partition": p, **info, **metrics(tg[:, 0], tg[:, 1], a, e1, ev)}
                va = np.var(a)
                row["lambda_eff"] = float(np.cov(a0, a, ddof=0)[0, 1] / va) if va > 0 else np.nan
                if correction:
                    row.update({f"corr_{k}": x for k, x in metrics(tg[:, 0], tg[:, 1], ac, e1, ev).items()})
                    ok = q > q0 * (1 + 1e-9) + 1e-12
                    row["bruit_ratio"] = float(np.mean((a[ok] - a0[ok]) ** 2 / (q[ok] - q0[ok]))) if ok.any() else np.nan
                    row["lambda_moyen"] = float(np.mean(np.concatenate([reliability(f, q[f["rows"]]) for f in fits])))
                out.append(row)
    return pd.DataFrame(out)


def summarize(rep, cols, order=None):
    """Médiane et 5e–95e centiles par configuration."""
    g = rep.groupby("config", sort=False)
    parts = {}
    for c in cols:
        parts[c] = g[c].median()
        parts[c + " P5"] = g[c].quantile(0.05)
        parts[c + " P95"] = g[c].quantile(0.95)
    out = pd.DataFrame(parts)
    return out.reindex(order) if order is not None else out
