# %%writefile ../src/opcal_feas.py
"""
opcal_feas — faisabilité de la calibration de site pour des hôpitaux nouveaux (OP-Cal).

Généré par notebooks/06b_faisabilite_opcal.ipynb (étape 1) : modifier le notebook, pas ce fichier.

Idée : un modèle fédéré transporté vers un hôpital h garde son classement mais se trompe surtout de
niveau de risque, d'une quantité a_h (calibration-in-the-large, log-odds). On teste si a_h est :
  - prévisible SANS label à partir de descripteurs du site (régime 0) ;
  - mieux estimé avec un taux agrégé (régime 1) ou k labels (régime 2) quand on part d'un a priori
    appris sur les autres hôpitaux (bayésien empirique) plutôt que de zéro ;
  - pour un label défini par un examen (lactate, créatinine), expliqué par le taux de dosage du site.

Aucune fonction ne lit un label pour construire un descripteur : les descripteurs utilisent les
entrées (couvertures, case-mix, structure, prédictions du modèle) et le fait qu'un examen ait été fait,
jamais son résultat ni le devenir du patient.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------------------------
# Outils numériques
# ----------------------------------------------------------------------------------------------

def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


def logit(p, eps=1e-6):
    p = np.clip(np.asarray(p, float), eps, 1 - eps)
    return np.log(p / (1 - p))


def offset_fit(lp, y=None, total=None, prior_mean=0.0, prior_var=np.inf, max_iter=100):
    """Décalage a (log-odds) à ajouter à lp. Données : labels individuels y, OU nombre total
    d'événements `total` (régime 1). Prior gaussien optionnel N(prior_mean, prior_var).
    Sans prior : correction de continuité (cible bornée à [0,5 ; n - 0,5]), comme site_offset.
    Retourne (a, variance a posteriori)."""
    lp = np.asarray(lp, float)
    n = len(lp)
    s = float(np.sum(y)) if y is not None else float(total)
    prec0 = 0.0 if not np.isfinite(prior_var) else 1.0 / max(prior_var, 1e-9)
    if prec0 == 0.0:
        s = float(np.clip(s, 0.5, n - 0.5))
    a = float(prior_mean) if prec0 > 0 else 0.0
    for _ in range(max_iter):
        mu = sigmoid(lp + a)
        g = s - mu.sum() - prec0 * (a - prior_mean)
        h = (mu * (1 - mu)).sum() + prec0
        step = float(np.clip(g / max(h, 1e-9), -5, 5))
        a += step
        if abs(step) < 1e-10:
            break
    mu = sigmoid(lp + a)
    return float(a), float(1.0 / max((mu * (1 - mu)).sum() + prec0, 1e-9))


def citl(lp, y):
    """Calibration-in-the-large : décalage qui recalibre lp sur y (> 0 = risque sous-estimé)."""
    return offset_fit(lp, y)


def cal_slope(lp, y, max_iter=50):
    lp, y = np.asarray(lp, float), np.asarray(y, float)
    if y.sum() < 2 or y.sum() > len(y) - 2:
        return np.nan, np.nan
    X = np.column_stack([np.ones(len(lp)), lp])
    b = np.array([0.0, 1.0])
    for _ in range(max_iter):
        mu = sigmoid(X @ b)
        H = (X * (mu * (1 - mu))[:, None]).T @ X + 1e-9 * np.eye(2)
        step = np.linalg.solve(H, X.T @ (y - mu))
        b += np.clip(step, -5, 5)
        if np.max(np.abs(step)) < 1e-9:
            break
    mu = sigmoid(X @ b)
    H = (X * (mu * (1 - mu))[:, None]).T @ X
    try:
        se = float(np.sqrt(np.linalg.inv(H)[1, 1]))
    except np.linalg.LinAlgError:
        se = np.nan
    return float(b[1]), se


def random_effects(beta, var):
    """Méta-analyse DerSimonian-Laird : mu, tau2, I2, Q, p(Q)."""
    from scipy import stats
    beta, var = np.asarray(beta, float), np.asarray(var, float)
    ok = np.isfinite(beta) & np.isfinite(var) & (var > 0)
    beta, var = beta[ok], var[ok]
    k = len(beta)
    if k < 3:
        return {"k": k, "mu": np.nan, "tau2": np.nan, "tau": np.nan, "I2": np.nan, "Q": np.nan, "Q_p": np.nan}
    w = 1 / var
    mu_fe = np.sum(w * beta) / np.sum(w)
    Q = float(np.sum(w * (beta - mu_fe) ** 2))
    C = np.sum(w) - np.sum(w ** 2) / np.sum(w)
    tau2 = max(0.0, (Q - (k - 1)) / C)
    ws = 1 / (var + tau2)
    return {"k": k, "mu": float(np.sum(ws * beta) / np.sum(ws)), "tau2": float(tau2),
            "tau": float(np.sqrt(tau2)), "I2": float(max(0.0, (Q - (k - 1)) / Q)) if Q > 0 else 0.0,
            "Q": Q, "Q_p": float(stats.chi2.sf(Q, k - 1))}


def boot_mean_diff(a, b, n_boot=2000, seed=0):
    """Moyenne de (a - b) sur les hôpitaux et IC 95 % par bootstrap des hôpitaux."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    d = a[ok] - b[ok]
    rng = np.random.default_rng(seed)
    bs = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(n_boot)])
    return float(d.mean()), float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))


# ----------------------------------------------------------------------------------------------
# Chargement des prédictions de transfert (notebooks 02 et 05)
# ----------------------------------------------------------------------------------------------

_PAT = re.compile(r"^(?P<name>.+)__fold(?P<fold>\d+)__seed(?P<seed>\d+)\.parquet$")


def list_runs(pred_dir):
    rows = []
    for p in Path(pred_dir).glob("*.parquet"):
        m = _PAT.match(p.name)
        if m:
            rows.append({"name": m["name"], "fold": int(m["fold"]), "seed": int(m["seed"]), "path": p})
    return pd.DataFrame(rows, columns=["name", "fold", "seed", "path"])


def load_transfer(pred_dir, name, folds):
    """Prédictions 'transfer' d'une configuration, moyennées sur les seeds disponibles pour TOUS les plis."""
    runs = list_runs(pred_dir)
    r = runs[runs["name"] == name]
    if r.empty:
        raise FileNotFoundError(f"Aucune prédiction pour '{name}' dans {pred_dir}")
    seeds = [s for s in sorted(r["seed"].unique()) if set(r.loc[r["seed"] == s, "fold"]) >= set(folds)]
    if not seeds:
        raise RuntimeError(f"'{name}' : aucune seed complète sur les plis {folds}")
    parts = []
    for _, row in r[r["seed"].isin(seeds) & r["fold"].isin(folds)].iterrows():
        d = pd.read_parquet(row["path"])
        d = d[d["role"] == "transfer"]
        cols = ["stay_id", "hospitalid", "p"] + (["y"] if "y" in d.columns else [])
        parts.append(d[cols].assign(fold=row["fold"], seed=row["seed"]))
    d = pd.concat(parts, ignore_index=True)
    agg = {"hospitalid": ("hospitalid", "first"), "fold": ("fold", "first"), "p": ("p", "mean"),
           "n_seeds": ("seed", "nunique")}
    if "y" in d.columns:
        agg["y"] = ("y", "first")
    out = d.groupby("stay_id").agg(**agg).reset_index()
    out["lp"] = logit(out["p"].to_numpy())
    return out, seeds


# ----------------------------------------------------------------------------------------------
# Calibration par hôpital tenu à l'écart
# ----------------------------------------------------------------------------------------------

def hospital_calibration(df):
    """df : stay_id, hospitalid, fold, lp, y. Une ligne par hôpital."""
    rows = []
    for h, g in df.groupby("hospitalid"):
        lp, y = g["lp"].to_numpy(), g["y"].to_numpy(float)
        a, v = citl(lp, y)
        b, se_b = cal_slope(lp, y)
        rows.append({"hospitalid": int(h), "fold": int(g["fold"].iloc[0]), "n": len(g), "events": int(y.sum()),
                     "prevalence": float(y.mean()), "mean_lp": float(lp.mean()), "sd_lp": float(lp.std()),
                     "citl": a, "var_citl": v, "slope": b, "se_slope": se_b})
    return pd.DataFrame(rows).set_index("hospitalid").sort_index()


# ----------------------------------------------------------------------------------------------
# Descripteurs de site, sans label
# ----------------------------------------------------------------------------------------------

BLOODGAS = ["lactate", "pH", "paO2", "paCO2", "FiO2"]
OBS_COV = {"cov_lactate": ["lactate"], "cov_bloodgas": BLOODGAS, "cov_invasive_bp": ["systemicmean"],
           "cov_gcs": ["GCS Total"], "cov_urine": ["urine_output"], "cov_temperature": ["temperature"]}
DX_KEYS = {"dx_sepsis": r"sepsis", "dx_cardiac_surgery": r"cabg|valve", "dx_arrest": r"cardiac arrest",
           "dx_overdose": r"overdose", "dx_stroke": r"cva|stroke", "dx_chf": r"chf|congestive",
           "dx_ami": r"infarction, acute myocardial", "dx_respiratory": r"pneumonia|emphysema|copd|asthma",
           "dx_gi_bleed": r"bleed", "dx_dka": r"ketoacidosis"}
SRC_GROUPS = {"Emergency Department": "src_ed", "Operating Room": "src_or", "Recovery Room": "src_or",
              "PACU": "src_or", "Floor": "src_floor", "Step-Down Unit (SDU)": "src_floor",
              "ICU to SDU": "src_floor", "Acute Care/Floor": "src_floor", "Other Hospital": "src_transfer",
              "Direct Admit": "src_direct"}
BEDS = {"<100": 0, "100 - 249": 1, "100-249": 1, "250 - 499": 2, "250-499": 2, ">= 500": 3, ">=500": 3}


def site_descriptors(data_dir, stay_labels_path, hospitals):
    """Descripteurs sans label par hôpital (split train uniquement pour tout ce qui est patient).
    Retourne (DataFrame indexé par hospitalid, dict groupe -> colonnes)."""
    data_dir = Path(data_dir)
    feats = json.loads((data_dir / "features.json").read_text(encoding="utf-8"))["features"]
    local = json.loads((data_dir / "normalizers" / "local_stats.json").read_text(encoding="utf-8"))
    manifest = pd.read_csv(data_dir / "clients" / "manifest.csv").set_index("hospitalid")
    splits = pd.read_parquet(data_dir / "splits" / "patient_splits.parquet")[["patientunitstayid", "split"]]
    cols_c = ["patientunitstayid", "hospitalid", "age_num", "gender", "apacheadmissiondx", "unittype",
              "unitadmitsource"]
    coh = pd.read_parquet(data_dir / "interim" / "cohort_final.parquet", columns=cols_c)
    coh = coh.merge(splits, on="patientunitstayid")
    coh = coh[(coh["split"] == "train") & coh["hospitalid"].isin(hospitals)]
    D = pd.DataFrame(index=pd.Index(sorted(int(h) for h in hospitals), name="hospitalid"))
    groups = {}

    # --- processus d'observation (24 h) : couvertures et disponibilité (local_stats, split train)
    idx = {f: i for i, f in enumerate(feats)}
    for name, vs in OBS_COV.items():
        ii = [idx[v] for v in vs if v in idx]
        D[name] = [float(np.mean([local[str(h)]["coverage"][i] for i in ii])) if ii else np.nan for h in D.index]
    D["n_unavailable"] = [int(np.sum(np.asarray(local[str(h)]["avail"]) == 0)) for h in D.index]
    D["mean_coverage"] = [float(np.mean(local[str(h)]["coverage"])) for h in D.index]
    obs_cols = list(OBS_COV) + ["n_unavailable", "mean_coverage"]

    # --- processus d'observation après 24 h : un examen a-t-il été refait ? (jamais son résultat)
    if stay_labels_path is not None and Path(stay_labels_path).exists():
        st = pd.read_parquet(stay_labels_path)
        st = st[(st["split"] == "train") & st["present48"].astype(bool) & st["hospitalid"].isin(hospitals)]
        g = st.groupby("hospitalid")
        D["test_rate_lactate"] = g["obs_la"].mean().reindex(D.index)
        D["test_rate_creatinine"] = st[st["cr_base"].notna()].groupby("hospitalid")["obs_cr"].mean().reindex(D.index)
        D["intensity_lactate"] = g["la_rate"].mean().reindex(D.index)
        D["intensity_creatinine"] = g["cr_rate"].mean().reindex(D.index)
        obs_cols += ["test_rate_lactate", "test_rate_creatinine", "intensity_lactate", "intensity_creatinine"]
    groups["obs"] = obs_cols

    # --- case-mix (split train)
    g = coh.groupby("hospitalid")
    D["age_mean"] = g["age_num"].mean().reindex(D.index)
    D["female_share"] = coh.assign(f=(coh["gender"] == "Female").astype(float)).groupby("hospitalid")["f"].mean().reindex(D.index)
    top_units = coh["unittype"].value_counts().index[:6]
    case_cols = ["age_mean", "female_share"]
    for u in top_units:
        c = "unit_" + re.sub(r"[^0-9a-z]+", "_", str(u).lower()).strip("_")
        D[c] = coh.assign(f=(coh["unittype"] == u).astype(float)).groupby("hospitalid")["f"].mean().reindex(D.index)
        case_cols.append(c)
    src = coh["unitadmitsource"].map(SRC_GROUPS).fillna("src_other")
    for s in ["src_ed", "src_or", "src_floor", "src_transfer", "src_direct"]:
        D[s] = coh.assign(f=(src == s).astype(float)).groupby("hospitalid")["f"].mean().reindex(D.index)
        case_cols.append(s)
    dx = coh["apacheadmissiondx"].fillna("").astype(str).str.lower()
    for c, pat in DX_KEYS.items():
        D[c] = coh.assign(f=dx.str.contains(pat, regex=True).astype(float)).groupby("hospitalid")["f"].mean().reindex(D.index)
        case_cols.append(c)
    groups["case"] = case_cols

    # --- structure de l'hôpital (table hospital d'eICU, fusionnée dans hospital_quality.csv)
    struct_cols = ["log_size"]
    D["log_size"] = np.log(manifest.loc[D.index, "n_stays"].astype(float))
    qp = data_dir / "reports" / "hospital_quality.csv"
    if qp.exists():
        q = pd.read_csv(qp).drop_duplicates("hospitalid").set_index("hospitalid").reindex(D.index)
        if "numbedscategory" in q:
            D["beds_cat"] = q["numbedscategory"].astype(str).str.strip().map(BEDS)
            struct_cols.append("beds_cat")
        if "teachingstatus" in q:
            D["teaching"] = q["teachingstatus"].astype(str).str.lower().isin(["t", "true", "1", "yes"]).astype(float)
            struct_cols.append("teaching")
        if "region" in q:
            for r in ["Midwest", "Northeast", "South", "West"]:
                D[f"region_{r.lower()}"] = (q["region"].astype(str) == r).astype(float)
                struct_cols.append(f"region_{r.lower()}")
            D["region_missing"] = q["region"].isna().astype(float)
            struct_cols.append("region_missing")
    groups["struct"] = struct_cols

    # --- score de référence APACHE IVa (moyenne du site, split train) : descripteur secondaire
    ap = {}
    for h in D.index:
        z = np.load(data_dir / "clients" / f"hospital_{h}.npz")
        a = z["apache_pred"][z["split"] == 0]
        a = a[np.isfinite(a)]
        ap[h] = (float(logit(np.clip(a.mean(), 1e-4, 1 - 1e-4))) if len(a) else np.nan,
                 float(1 - len(a) / max((z["split"] == 0).sum(), 1)))
    D["apache_logit_mean"] = [ap[h][0] for h in D.index]
    D["apache_missing_share"] = [ap[h][1] for h in D.index]
    groups["apache"] = ["apache_logit_mean", "apache_missing_share"]
    return D, groups


# ----------------------------------------------------------------------------------------------
# Méta-modèle de la calibration de site (régime 0), croisé par pli
# ----------------------------------------------------------------------------------------------

class SiteRidge:
    """Régression ridge pondérée de a_h sur des descripteurs standardisés ; intercept non pénalisé."""

    def __init__(self, lam):
        self.lam = lam

    def fit(self, Z, c, w):
        Z = np.asarray(Z, float)
        self.fill = np.nanmean(Z, axis=0) if Z.shape[1] else np.zeros(0)
        self.fill = np.where(np.isfinite(self.fill), self.fill, 0.0)
        Z = np.where(np.isfinite(Z), Z, self.fill)
        w = np.asarray(w, float) / np.sum(w)
        self.mz = (w[:, None] * Z).sum(0)
        sd = np.sqrt((w[:, None] * (Z - self.mz) ** 2).sum(0))
        self.sz = np.where(sd > 1e-9, sd, 1.0)
        Zs = (Z - self.mz) / self.sz
        cbar = float(np.sum(w * c))
        if Zs.shape[1]:
            A = (Zs * w[:, None]).T @ Zs + self.lam * np.eye(Zs.shape[1]) / len(c)
            self.beta = np.linalg.solve(A, (Zs * w[:, None]).T @ (c - cbar))
        else:
            self.beta = np.zeros(0)
        self.b0 = cbar
        return self

    def predict(self, Z):
        Z = np.asarray(Z, float)
        Z = np.where(np.isfinite(Z), Z, self.fill)
        return self.b0 + ((Z - self.mz) / self.sz) @ self.beta


LAM_GRID = [0.3, 1, 3, 10, 30, 100, 300, 1000]


class SiteEB:
    """Méta-régression bayésienne empirique de la calibration de site :
        a_h = mu + z_h' beta + u_h + e_h,  beta ~ N(0, s2b I) (descripteurs standardisés),
        u_h ~ N(0, tau2) (hétérogénéité non expliquée),  e_h ~ N(0, v_h) (bruit d'estimation de a_h).
    (tau2, s2b) par maximum de vraisemblance restreinte (REML) ; aucun réglage par validation croisée.
    predict() renvoie la moyenne et la variance prédictive d'un hôpital nouveau : c'est l'a priori
    N(â_h, V_h) utilisé ensuite avec 0, un agrégat ou k labels."""

    def fit(self, Z, c, v):
        from scipy.optimize import minimize
        Z = np.asarray(Z, float).reshape(len(c), -1)
        c, v = np.asarray(c, float), np.asarray(v, float)
        self.p = Z.shape[1]
        if self.p:
            with np.errstate(all="ignore"):
                fill = np.nanmean(Z, axis=0)
            self.fill = np.where(np.isfinite(fill), fill, 0.0)
            Z = np.where(np.isfinite(Z), Z, self.fill)
            self.mz, sd = Z.mean(0), Z.std(0)
            self.sz = np.where(sd > 1e-9, sd, np.inf)
            Zs = (Z - self.mz) / self.sz
        else:
            Zs = np.zeros((len(c), 0))
        K = Zs @ Zs.T
        one = np.ones(len(c))

        def parts(theta):
            t2 = np.exp(theta[0])
            s2 = np.exp(theta[1]) if self.p else 0.0
            V = s2 * K + np.diag(t2 + v)
            L = np.linalg.cholesky(V)
            Vi = np.linalg.solve(L.T, np.linalg.solve(L, np.eye(len(c))))
            a = one @ Vi @ one
            mu = (one @ Vi @ c) / a
            r = c - mu
            return t2, s2, Vi, a, mu, r, 2 * np.log(np.diag(L)).sum()

        def nll(theta):
            try:
                t2, s2, Vi, a, mu, r, logdet = parts(theta)
            except np.linalg.LinAlgError:
                return 1e12
            return 0.5 * (logdet + np.log(a) + r @ Vi @ r)

        g_t = np.log(np.geomspace(1e-4, 2.0, 12))
        g_s = np.log(np.geomspace(1e-5, 1.0, 12)) if self.p else [0.0]
        best = min(((nll([a_, b_]), a_, b_) for a_ in g_t for b_ in g_s))
        bounds = [(np.log(1e-6), np.log(5.0)), (np.log(1e-7), np.log(2.0))] if self.p else [(np.log(1e-6), np.log(5.0))]
        x0 = [best[1], best[2]] if self.p else [best[1]]
        res = minimize(lambda th: nll(th if self.p else [th[0], 0.0]), x0, method="L-BFGS-B", bounds=bounds)
        theta = res.x if res.fun <= best[0] else np.array(x0)
        theta = theta if self.p else np.array([theta[0], 0.0])
        self.tau2, self.s2b, self.Vi, self.a, self.mu, r, _ = parts(theta)
        self.Zs = Zs
        self.beta = self.s2b * Zs.T @ (self.Vi @ r) if self.p else np.zeros(0)
        return self

    def _std(self, Z):
        Z = np.asarray(Z, float).reshape(-1, self.p) if self.p else np.zeros((np.asarray(Z).shape[0], 0))
        if self.p:
            Z = np.where(np.isfinite(Z), Z, self.fill)
            Z = (Z - self.mz) / self.sz
        return Z

    def predict(self, Z):
        Zn = self._std(Z)
        mean = self.mu + Zn @ self.beta
        var = np.full(len(Zn), self.tau2 + 1.0 / self.a)
        if self.p:
            k = self.s2b * Zn @ self.Zs.T
            var += self.s2b * (Zn ** 2).sum(1) - np.einsum("ij,jk,ik->i", k, self.Vi, k)
        return mean, np.maximum(var, 1e-6)


def crossfit_prior(cal, D, cols, fixed_beta=None, engine="eb", lam_grid=LAM_GRID):
    """Pour chaque pli f : méta-modèle appris sur les a_h (hors fédération) des hôpitaux des AUTRES plis,
    puis prédiction pour les hôpitaux du pli f, qui n'ont servi à rien d'autre.
    engine = "eb" (méta-régression REML, principal) ou "ridge" (ridge pondéré, lambda par validation
    croisée interne, sensibilité). fixed_beta = (colonne, coefficient) : prédicteur mécanistique sans
    coefficient ajusté (seuls la moyenne et tau2 sont appris).
    Retourne : a_hat, pred_var (variance prédictive de l'a priori), tau2_raw (DL, autres plis),
    tau2_resid, hyper (s2b ou lambda), mu."""
    out = []
    for f in sorted(cal["fold"].unique()):
        tr, te = cal[cal["fold"] != f], cal[cal["fold"] == f]
        c_tr, v_tr = tr["citl"].to_numpy(), tr["var_citl"].to_numpy()
        tau2_dl = random_effects(c_tr, v_tr)["tau2"]
        if fixed_beta is not None:
            col, coef = fixed_beta
            z_tr, z_te = D.loc[tr.index, col].to_numpy(float), D.loc[te.index, col].to_numpy(float)
            zbar = float(np.nanmean(z_tr))
            off_tr = coef * (np.nan_to_num(z_tr, nan=zbar) - zbar)
            off_te = coef * (np.nan_to_num(z_te, nan=zbar) - zbar)
            m = SiteEB().fit(np.zeros((len(tr), 0)), c_tr - off_tr, v_tr)
            mean, var = m.predict(np.zeros((len(te), 0)))
            mean = mean + off_te
            res = {"tau2_resid": m.tau2, "hyper": np.nan, "mu": m.mu}
        elif engine == "eb" or not cols:
            m = SiteEB().fit(D.loc[tr.index, cols].to_numpy(float), c_tr, v_tr)
            mean, var = m.predict(D.loc[te.index, cols].to_numpy(float))
            res = {"tau2_resid": m.tau2, "hyper": m.s2b if cols else np.nan, "mu": m.mu}
        else:
            w = 1.0 / (v_tr + tau2_dl)
            Ztr = D.loc[tr.index, cols].to_numpy(float)
            inner = tr["fold"].to_numpy()
            best, lam, best_pred = np.inf, lam_grid[0], None
            for l_ in lam_grid:
                pred_in = np.zeros(len(tr))
                for g in np.unique(inner):
                    a_, b_ = inner != g, inner == g
                    pred_in[b_] = SiteRidge(l_).fit(Ztr[a_], c_tr[a_], w[a_]).predict(Ztr[b_])
                sse = float(np.sum(w * (c_tr - pred_in) ** 2))
                if sse < best:
                    best, lam, best_pred = sse, l_, pred_in.copy()
            m = SiteRidge(lam).fit(Ztr, c_tr, w)
            mean = m.predict(D.loc[te.index, cols].to_numpy(float))
            t2r = random_effects(c_tr - best_pred, v_tr)["tau2"]
            var = np.full(len(te), t2r)
            res = {"tau2_resid": t2r, "hyper": lam, "mu": m.b0}
        out.append(pd.DataFrame({"a_hat": mean, "pred_var": var, "tau2_raw": tau2_dl, **res}, index=te.index))
    return pd.concat(out).sort_index()


def evaluate_prior(cal, prior):
    """Résidus de calibration après correction a_hat, hôpitaux tenus à l'écart."""
    c, v = cal["citl"], cal["var_citl"]
    r = c - prior["a_hat"].reindex(c.index)
    raw, res = random_effects(c, v), random_effects(r, v)
    return {"mean_abs_citl": float(r.abs().mean()), "median_abs_citl": float(r.abs().median()),
            "mean_resid": float(r.mean()), "share_abs_lt_0.2": float((r.abs() < 0.2).mean()),
            "tau2_raw": raw["tau2"], "tau2_resid": res["tau2"],
            "R2_tau": float(1 - res["tau2"] / raw["tau2"]) if raw["tau2"] > 0 else np.nan}


# ----------------------------------------------------------------------------------------------
# Régimes 1 et 2 : taux agrégé ou k labels, avec ou sans a priori appris
# ----------------------------------------------------------------------------------------------

def simulate_regimes(stays, prior_desc, prior_glob, k_grid, n_rep=50, n0=10.0, seed=0):
    """stays : stay_id, hospitalid, lp, y (patients d'évaluation des hôpitaux tenus à l'écart).
    Chaque répétition coupe les patients d'un hôpital en deux : « historique » (agrégé ou k labels)
    et « déploiement » (évaluation). Retourne le |CITL| sur la moitié déploiement après correction."""
    rng = np.random.default_rng(seed)
    rows = []
    for h, g in stays.groupby("hospitalid"):
        lp_all, y_all = g["lp"].to_numpy(), g["y"].to_numpy(float)
        pd_, pg = prior_desc.loc[h], prior_glob.loc[h]
        for rep in range(n_rep):
            perm = rng.permutation(len(g))
            half = len(g) // 2
            H, Dp = perm[:half], perm[half:]
            lpD, yD = lp_all[Dp], y_all[Dp]

            def resid(a):
                return abs(offset_fit(lpD + a, yD)[0])

            base = {"hospitalid": h, "rep": rep}
            rows.append({**base, "k": 0, "method": "aucune", "abs_citl": resid(0.0)})
            rows.append({**base, "k": 0, "method": "moyenne", "abs_citl": resid(pg["a_hat"])})
            rows.append({**base, "k": 0, "method": "descripteurs", "abs_citl": resid(pd_["a_hat"])})
            tot = y_all[H].sum()
            rows.append({**base, "k": -1, "method": "agrege_local",
                         "abs_citl": resid(offset_fit(lp_all[H], total=tot)[0])})
            rows.append({**base, "k": -1, "method": "agrege_EB_descripteurs",
                         "abs_citl": resid(offset_fit(lp_all[H], total=tot, prior_mean=pd_["a_hat"],
                                                      prior_var=pd_["pred_var"])[0])})
            for k in k_grid:
                if k > len(H):
                    continue
                L = H[:k]
                lpL, yL = lp_all[L], y_all[L]
                rows += [
                    {**base, "k": k, "method": "local", "abs_citl": resid(offset_fit(lpL, yL)[0])},
                    {**base, "k": k, "method": "retrecissement_fixe",
                     "abs_citl": resid(offset_fit(lpL, yL, prior_mean=pg["a_hat"], prior_var=1.0 / n0)[0])},
                    {**base, "k": k, "method": "EB_global",
                     "abs_citl": resid(offset_fit(lpL, yL, prior_mean=pg["a_hat"], prior_var=pg["pred_var"])[0])},
                    {**base, "k": k, "method": "EB_descripteurs",
                     "abs_citl": resid(offset_fit(lpL, yL, prior_mean=pd_["a_hat"], prior_var=pd_["pred_var"])[0])},
                ]
    return pd.DataFrame(rows)


def summarize_regimes(sim):
    """|CITL| moyen par (k, méthode) : moyenne sur les répétitions par hôpital, puis sur les hôpitaux."""
    per_h = sim.groupby(["k", "method", "hospitalid"])["abs_citl"].mean().reset_index()
    tab = per_h.groupby(["k", "method"]).agg(abs_citl=("abs_citl", "mean"), hopitaux=("hospitalid", "nunique"))
    return per_h, tab.reset_index()


def paired_by_hospital(per_h, k, a, b, n_boot=2000, seed=0):
    """Moyenne sur les hôpitaux de |CITL|(a) − |CITL|(b) au même k, IC bootstrap des hôpitaux."""
    w = per_h[per_h["k"] == k].pivot(index="hospitalid", columns="method", values="abs_citl").dropna(subset=[a, b])
    return boot_mean_diff(w[a].to_numpy(), w[b].to_numpy(), n_boot, seed), len(w)


# ----------------------------------------------------------------------------------------------
# Mécanisme pour un label défini par un examen : Y* = D × Y
# ----------------------------------------------------------------------------------------------

def offset_slope_fit(lp, y, z, max_iter=50):
    """logit P(y=1) = lp + alpha + gamma * z (lp en offset). Retourne (alpha, gamma)."""
    lp, y, z = (np.asarray(v, float) for v in (lp, y, z))
    X = np.column_stack([np.ones(len(lp)), z])
    b = np.zeros(2)
    for _ in range(max_iter):
        mu = sigmoid(lp + X @ b)
        H = (X * (mu * (1 - mu))[:, None]).T @ X + 1e-9 * np.eye(2)
        step = np.linalg.solve(H, X.T @ (y - mu))
        b += np.clip(step, -5, 5)
        if np.max(np.abs(step)) < 1e-9:
            break
    return float(b[0]), float(b[1])


def pooled_gamma(stays, z_by_h, n_boot=1000, seed=0):
    """gamma (effet du log du taux de dosage du site sur le label enregistré, à score égal),
    IC par bootstrap des hôpitaux. Le mécanisme Y* = D × Y prédit gamma > 0 (≈ 1 si le score
    n'a rien capté de la politique de dosage)."""
    s = stays[stays["hospitalid"].isin(z_by_h.dropna().index)]
    z = s["hospitalid"].map(z_by_h).to_numpy(float)
    z = z - np.mean(z_by_h.dropna())
    g = s["hospitalid"].to_numpy()
    lp, y = s["lp"].to_numpy(), s["y"].to_numpy(float)
    est = offset_slope_fit(lp, y, z)[1]
    hs = np.unique(g)
    rows = {h: np.flatnonzero(g == h) for h in hs}
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n_boot):
        idx = np.concatenate([rows[h] for h in rng.choice(hs, len(hs))])
        bs.append(offset_slope_fit(lp[idx], y[idx], z[idx])[1])
    return float(est), float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))


def boot_r2tau(cal, a_hat, n_boot=2000, seed=0):
    """IC bootstrap (hôpitaux) de R2_tau = 1 − tau2(résidus) / tau2(brut), a_hat fixé (croisé)."""
    c, v = cal["citl"].to_numpy(), cal["var_citl"].to_numpy()
    r = c - a_hat.reindex(cal.index).to_numpy()
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_boot):
        i = rng.integers(0, len(c), len(c))
        t_raw = random_effects(c[i], v[i])["tau2"]
        if t_raw > 0:
            out.append(1 - random_effects(r[i], v[i])["tau2"] / t_raw)
    return float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975))


def check(label, ok, store=None):
    print(("OK     " if ok else "ÉCHEC  ") + label)
    if store is not None:
        store.append({"controle": label, "ok": bool(ok)})
    return bool(ok)