"""
tdtfl_data — chargement des données TDT-FL (protocole 1.0).

Généré par notebooks/02_protocole_tdtfl.ipynb (étape 8) : modifier le notebook, pas ce fichier.

Régimes et codes des découpages (graine s) :
- "r1" statique   : 0 train, 1 D, 2 test ; plis internes du train dans inner_folds(s) (0..4, -1 hors train).
- "r2" temporel   : hôpitaux `temporal` seulement ; 0 train14, 1 D14, 2 test14, 3 D15, 4 test15 (-1 sinon).
- "r3" non vu     : test = test r1 ; étiquettes de la cible = budget b pris dans deux réservoirs
                    (calibration, D) dans l'ordre d'acquisition (r3_labeled) ; fédération = hôpitaux hors
                    du pli r3 de la cible.

Encodage au chargement (rien n'est stocké normalisé) :
- continues : z-score avec la moyenne et l'écart-type du split train de la fédération
  (normalisation globale) ; valeur manquante -> 0, c'est-à-dire la moyenne ;
- binaires (indicateurs d'observation, one-hot, manquants) : 0/1 ;
- harmonisation : une variable indisponible dans un hôpital (avail = 0) est remise à « manquant » dans
  ses propres données ; matrix(j, ..., also_mask=i) la remet aussi à manquant chez j avant d'appliquer
  le modèle de i.
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

R1 = {"train": 0, "D": 1, "test": 2}
R2 = {"train14": 0, "D14": 1, "test14": 2, "D15": 3, "test15": 4}
R3_POOLS = {"cal": 0, "D": 1}
MISSING_STATS = ("mean", "min", "max", "last", "total")   # -> NaN quand la variable est masquée
ZERO_STATS = ("n_obs", "observed")                        # -> 0 quand la variable est masquée


class TDTData:
    """Accès unique aux données TDT-FL. data = TDTData("../data_tdtfl")."""

    def __init__(self, tdt_dir):
        self.dir = Path(tdt_dir)
        self.protocol = json.loads((self.dir / "protocol_tdtfl.json").read_text(encoding="utf-8"))
        self.seeds = list(range(self.protocol["seeds"]["n_seeds"]))
        self.stays = pd.read_parquet(self.dir / "stays.parquet").set_index("patientunitstayid")
        self.hospitals = pd.read_csv(self.dir / "hospitals.csv", index_col="hospitalid")
        self.hospitals["temporal"] = self.hospitals["temporal"].astype(bool)
        self.meta = pd.read_csv(self.dir / "feature_meta.csv")
        self.columns = self.meta["name"].tolist()
        self.cont = (self.meta["kind"] == "cont").to_numpy()
        self.splits = pd.read_parquet(self.dir / "splits.parquet").set_index("patientunitstayid").loc[self.stays.index]
        raw = pd.read_parquet(self.dir / "features_raw.parquet").set_index("patientunitstayid")
        self.avail = pd.read_csv(self.dir / "availability.csv", index_col="hospitalid").astype(bool)
        hosp = self.stays["hospitalid"].to_numpy()
        self._rows = {int(h): np.flatnonzero(hosp == h) for h in np.unique(hosp)}
        x = raw.loc[self.stays.index, self.columns].to_numpy(dtype=np.float32, copy=True)
        for h, rows in self._rows.items():          # chaque hôpital : ses variables indisponibles -> manquant
            x[rows] = self._mask(x[rows], self.unavailable(h))
        self.raw = x

    # ------------------------------------------------------------------ hôpitaux
    def targets(self, regime="r1", role="eval", stratum=None):
        """Cibles d'un régime. role : 'eval' (résultats rapportés), 'tune' (réglage) ou None (toutes)."""
        h = self.hospitals
        keep = np.ones(len(h), dtype=bool)
        if regime == "r2":
            keep &= h["temporal"].to_numpy()
        if role is not None:
            keep &= (h["role"] == role).to_numpy()
        if stratum is not None:
            keep &= (h["stratum"] == stratum).to_numpy()
        return [int(i) for i in h.index[keep]]

    def federation(self, regime="r1", fold=None):
        """Hôpitaux qui entraînent un modèle (sources, modèle global) dans un régime."""
        h = self.hospitals
        if regime == "r1":
            return [int(i) for i in h.index]
        if regime == "r2":
            return [int(i) for i in h.index[h["temporal"].to_numpy()]]
        if regime == "r3":
            if fold is None:
                raise ValueError("régime r3 : préciser le pli de la cible (r3_fold(hôpital))")
            return [int(i) for i in h.index[h["r3_fold"].to_numpy() != int(fold)]]
        raise ValueError(f"régime inconnu : {regime}")

    def r3_fold(self, hospital_id):
        return int(self.hospitals.loc[int(hospital_id), "r3_fold"])

    def unavailable(self, hospital_id):
        a = self.avail.loc[int(hospital_id)]
        return a.index[~a.to_numpy()].tolist()

    def masked_variables(self, source, target):
        """Variables disponibles chez la cible mais pas chez la source (remises à manquant chez la cible)."""
        a_s, a_t = self.avail.loc[int(source)].to_numpy(), self.avail.loc[int(target)].to_numpy()
        return self.avail.columns[(~a_s) & a_t].tolist()

    # ---------------------------------------------------------------- découpages
    def codes(self, regime, seed):
        """Codes de partie de tous les séjours (ordre de self.stays)."""
        col = {"r1": f"r1_s{seed}", "r3": f"r1_s{seed}", "r2": f"r2_s{seed}"}[regime]
        return self.splits[col].to_numpy()

    def inner_folds(self, seed):
        return self.splits[f"r1_inner_s{seed}"].to_numpy()

    def r3_labeled(self, hospital_id, seed, budget):
        """Masques (calibration, D) sur les séjours de l'hôpital, pour un budget de `budget` patients étiquetés."""
        rows = self._rows[int(hospital_id)]
        pool = self.splits[f"r3_pool_s{seed}"].to_numpy()[rows]
        rank = self.splits[f"r3_rank_s{seed}"].to_numpy()[rows]
        n_cal = budget // 2
        n_d = budget - n_cal
        return (pool == R3_POOLS["cal"]) & (rank < n_cal), (pool == R3_POOLS["D"]) & (rank < n_d)

    def train_rows(self, regime, seed, fold=None):
        """Lignes du split d'entraînement de la fédération (les seules qui servent à la normalisation)."""
        rows = np.concatenate([self._rows[h] for h in self.federation(regime, fold)])
        return np.sort(rows[self.codes(regime, seed)[rows] == 0])

    # ------------------------------------------------------------------ encodage
    def normalizer(self, regime, seed, fold=None):
        """Normalisation globale : moyenne et écart-type des variables continues sur train_rows."""
        rows = self.train_rows(regime, seed, fold)
        x = self.raw[rows][:, self.cont].astype(np.float64)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            mean, std = np.nanmean(x, axis=0), np.nanstd(x, axis=0)
        mean = np.where(np.isfinite(mean), mean, 0.0)
        std = np.where(np.isfinite(std) & (std > 1e-6), std, 1.0)
        return {"regime": regime, "seed": int(seed), "fold": fold, "n_rows": int(len(rows)),
                "mean": mean.astype(np.float32), "std": std.astype(np.float32)}

    def _mask(self, x, variables):
        if not variables:
            return x
        m = self.meta["var"].isin(variables)
        x = x.copy()
        x[:, np.flatnonzero(m & self.meta["stat"].isin(MISSING_STATS))] = np.nan
        x[:, np.flatnonzero(m & self.meta["stat"].isin(ZERO_STATS))] = 0.0
        return x

    def encode(self, x, norm):
        x = x.copy()
        x[:, self.cont] = (x[:, self.cont] - norm["mean"]) / norm["std"]
        return np.nan_to_num(x, nan=0.0).astype(np.float32)

    def matrix(self, hospital_id, regime, seed, norm, also_mask=None):
        """Tous les séjours d'un hôpital, encodés. also_mask = hôpital source dont le modèle sera appliqué."""
        rows = self._rows[int(hospital_id)]
        x = self.raw[rows]
        if also_mask is not None:
            x = self._mask(x, self.unavailable(also_mask))
        st = self.stays.iloc[rows]
        out = {"hospital_id": int(hospital_id), "stay_id": st.index.to_numpy(),
               "split": self.codes(regime, seed)[rows], "X": self.encode(x, norm),
               "y_mortality": st["y_mortality"].to_numpy(dtype=np.float32),
               "phenotype": st["phenotype"].to_numpy(), "operative": st["operative"].to_numpy(),
               "year": st["year"].to_numpy()}
        for c in ("y_aki", "aki_ascertained", "apache_pred_mortality"):
            if c in st.columns:
                out[c] = st[c].to_numpy()
        if regime in ("r1", "r3"):
            out["inner_fold"] = self.inner_folds(seed)[rows]
        return out


def select(d, mask):
    """Sous-ensemble d'un dictionnaire renvoyé par matrix (masque booléen ou liste de codes de partie)."""
    if not (isinstance(mask, np.ndarray) and mask.dtype == bool):
        mask = np.isin(d["split"], np.atleast_1d(mask))
    n = len(d["stay_id"])
    return {k: (v[mask] if isinstance(v, np.ndarray) and v.ndim >= 1 and len(v) == n else v)
            for k, v in d.items()}
