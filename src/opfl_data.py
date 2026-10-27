"""
opfl_data — chargement des données OP-FL V1 (version 1.1).

Généré par notebooks/01_donnees_v1.ipynb (étape 11) : modifier le notebook, pas ce fichier.

Transformation au chargement :
- X : log1p (variables asymétriques) -> z-score (stats du pli, ou stats locales sans label)
      -> forward-fill -> valeurs jamais observées = 0 (moyenne).
- M ∈ {0,1} ; C -> log1p(C) ; Delta -> Delta / T. Aucune statistique nécessaire.
- S : imputation par la moyenne du pli, z-score de l'âge, de la taille et du poids,
      sexe en 0/1, diagnostic d'admission en one-hot (top-15 du pli + autre + manquant).
- avail : (F,) disponibilité de chaque variable dans l'hôpital (1 = module utilisé),
      calculée sans label sur le split train de l'hôpital.
"""
import json
from functools import lru_cache
from pathlib import Path
import numpy as np

SPLIT_CODES = {"train": 0, "val": 1, "test": 2}
MIN_LOCAL_COUNT = 20          # en dessous, le mode local retombe sur la stat du pli


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_features(data_dir):
    return _json(Path(data_dir) / "features.json")


def load_protocol(data_dir):
    return _json(Path(data_dir) / "splits" / "protocol.json")


def load_normalizer(data_dir, fold):
    """fold : 0..n_folds-1 (développement) ou 'final' (test verrouillé)."""
    name = "fold_final.json" if str(fold) == "final" else f"fold_{int(fold)}.json"
    return _json(Path(data_dir) / "normalizers" / name)


def fold_hospitals(data_dir, fold):
    """Retourne (hôpitaux d'entraînement, hôpitaux tenus à l'écart) pour un pli."""
    norm = load_normalizer(data_dir, fold)
    return norm["train_hospitals"], norm["heldout_hospitals"]


@lru_cache(maxsize=None)
def _local_stats(data_dir):
    return _json(Path(data_dir) / "normalizers" / "local_stats.json")


def availability(data_dir, hospital_id):
    return np.asarray(_local_stats(str(data_dir))[str(int(hospital_id))]["avail"], np.float32)


def forward_fill(x):
    x = x.copy()
    for t in range(1, x.shape[1]):
        cur = x[:, t, :]
        x[:, t, :] = np.where(np.isnan(cur), x[:, t - 1, :], cur)
    return x


def build_static(S_num, dx_code, norm):
    s = S_num.astype(np.float32).copy()
    mean = np.asarray(norm["s_mean"], np.float32)
    std = np.asarray(norm["s_std"], np.float32)
    s = np.where(np.isnan(s), mean, s)
    s[:, :3] = (s[:, :3] - mean[:3]) / std[:3]
    top = list(norm["dx_top_codes"])
    pos = {c: i for i, c in enumerate(top)}
    col = np.array([pos.get(int(c), len(top)) for c in dx_code], dtype=np.int64)
    col[dx_code == norm["dx_missing_code"]] = len(top) + 1
    oh = np.zeros((len(dx_code), len(top) + 2), np.float32)
    oh[np.arange(len(dx_code)), col] = 1.0
    return np.concatenate([s, oh], axis=1)


def static_names(data_dir, norm):
    feats = load_features(str(data_dir))
    return feats["static_num"] + [f"dx_{n}" for n in norm["dx_top_names"]] + ["dx_other", "dx_missing"]


def load_client(data_dir, hospital_id, norm, mode="global"):
    """Charge un hôpital prêt pour un modèle. norm = load_normalizer(data_dir, fold)."""
    data_dir = Path(data_dir)
    feats = load_features(str(data_dir))
    d = np.load(data_dir / "clients" / f"hospital_{int(hospital_id)}.npz")
    log_mask = np.asarray(feats["log"], bool)

    x = d["X_raw"].astype(np.float32)
    x[..., log_mask] = np.log1p(np.clip(x[..., log_mask], 0, None))
    mean = np.asarray(norm["x_mean"], np.float32)
    std = np.asarray(norm["x_std"], np.float32)
    if mode == "local":
        loc = _local_stats(str(data_dir))[str(int(hospital_id))]
        ok = np.asarray(loc["n"]) >= MIN_LOCAL_COUNT
        mean = np.where(ok, np.asarray(loc["mean"], np.float32), mean)
        std = np.where(ok, np.asarray(loc["std"], np.float32), std)
    elif mode != "global":
        raise ValueError("mode doit valoir 'global' ou 'local'")
    x = (x - mean) / std
    x = np.nan_to_num(forward_fill(x), nan=0.0).astype(np.float32)

    T = feats["T"]
    return {
        "hospital_id": int(hospital_id),
        "stay_id": d["stay_id"], "split": d["split"],
        "X": x,
        "M": d["M"].astype(np.float32),
        "C": np.log1p(d["C"].astype(np.float32)),
        "Delta": d["Delta"].astype(np.float32) / T,
        "S": build_static(d["S_num"], d["dx_code"], norm),
        "avail": availability(data_dir, hospital_id),
        "y_mortality": d["y_mortality"].astype(np.float32),
        "y_aki": d["y_aki"], "aki_ascertained": d["aki_ascertained"],
        "y_los_gt7": d["y_los_gt7"].astype(np.float32),
        "apache_pred": d["apache_pred"],
    }


def select(client, split):
    """Sous-ensemble d'un client : split = 'train', 'val', 'test' ou une liste."""
    codes = [SPLIT_CODES[s] for s in ([split] if isinstance(split, str) else split)]
    keep = np.isin(client["split"], codes)
    return {k: (v[keep] if isinstance(v, np.ndarray) and v.ndim > 0 and len(v) == len(keep) else v)
            for k, v in client.items()}
