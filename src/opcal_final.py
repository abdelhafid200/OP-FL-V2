"""
opcal_final — modèles finaux, labels et observation des hôpitaux verrouillés (notebook 07, OP-Cal).

Généré par notebooks/07_confirmation.ipynb (étape 1) : modifier le notebook, pas ce fichier.

- observation_table : variables d'observation par séjour, SANS résultat d'examen (présence à 48 h, créatinine
  de base sur [0, 24 h[, nombre de dosages après 24 h, intensité) ; c'est tout ce qu'utilisent les descripteurs.
- label_table : ajoute les pics après 24 h et les labels (AKI, hyperlactatémie) ; code identique au notebook 04.
- unit_shares : parts des types d'unité gelés (les 6 colonnes unit_* de la spécification) pour n'importe quels hôpitaux.
- load_final_mortality / build_final_population : pli « final » (60 hôpitaux de développement, 96 verrouillés),
  comme opfl_fed.load_fold et opfl_labelfl.build_fold, mais sans aucun label pour les hôpitaux verrouillés.
"""
import numpy as np
import pandas as pd
import torch

import opfl_data as od
from opfl_fed import _pack as _pack_mort
from opfl_labelfl import _pack as _pack_pop
from opfl_label import summarize_post, aki_labels, threshold_labels

WIN = 1440                      # fin de la fenêtre des données d'entrée (24 h), comme le notebook 04


def _post(labs, var, disc, end):
    x = labs[labs["var"] == var]
    stop = np.minimum(x["stay_id"].map(disc), end)
    return x[(x["offset"] >= WIN) & (x["offset"] <= stop)]


def observation_table(cohort, splits, labs_counts, cr_base_labs, hospitals, cfg04):
    """cohort : patientunitstayid, hospitalid, unitdischargeoffset ; splits : patientunitstayid, split ;
    labs_counts : stay_id, var, offset (SANS valeur) ; cr_base_labs : créatinine sur [0, 24 h[ (stay_id, value)."""
    c = cohort.merge(splits, on="patientunitstayid").rename(columns={"patientunitstayid": "stay_id"})
    c = c[c["hospitalid"].isin(hospitals)].sort_values("stay_id").reset_index(drop=True)
    c["present48"] = c["unitdischargeoffset"] >= cfg04["present_min"]
    disc = c.set_index("stay_id")["unitdischargeoffset"]
    lab = labs_counts[labs_counts["stay_id"].isin(c["stay_id"])]
    n_cr = _post(lab, "creatinine", disc, cfg04["aki_end"]).groupby("stay_id").size().reindex(c["stay_id"]).fillna(0).astype(int)
    n_la = _post(lab, "lactate", disc, cfg04["lac_end"]).groupby("stay_id").size().reindex(c["stay_id"]).fillna(0).astype(int)
    base = cr_base_labs[cr_base_labs["stay_id"].isin(c["stay_id"])].groupby("stay_id")["value"].min().reindex(c["stay_id"])
    c["cr_base"] = base.to_numpy()
    c["cr_n_post"] = n_cr.to_numpy()
    c["obs_cr"] = (c["cr_n_post"] > 0) & c["cr_base"].notna()
    c["cr_days"] = (np.minimum(c["unitdischargeoffset"], cfg04["aki_end"]) - WIN).clip(lower=1) / 1440
    c["cr_rate"] = c["cr_n_post"] / c["cr_days"]
    c["la_n_post"] = n_la.to_numpy()
    c["obs_la"] = c["la_n_post"] > 0
    c["la_days"] = (np.minimum(c["unitdischargeoffset"], cfg04["lac_end"]) - WIN).clip(lower=1) / 1440
    c["la_rate"] = c["la_n_post"] / c["la_days"]
    return c


def label_table(obs, labs, cfg04):
    """Ajoute pics et labels à observation_table (labs : stay_id, var, offset, value)."""
    c = obs.copy()
    disc = c.set_index("stay_id")["unitdischargeoffset"]
    lab = labs[labs["stay_id"].isin(c["stay_id"])]
    s_cr = summarize_post(_post(lab, "creatinine", disc, cfg04["aki_end"])[["stay_id", "offset", "value"]], c["stay_id"])
    s_la = summarize_post(_post(lab, "lactate", disc, cfg04["lac_end"])[["stay_id", "offset", "value"]], c["stay_id"])
    assert np.array_equal(s_cr["n_post"].to_numpy(), c["cr_n_post"].to_numpy()) and \
        np.array_equal(s_la["n_post"].to_numpy(), c["la_n_post"].to_numpy()), "Comptes de dosages incohérents."
    c["cr_peak"] = s_cr["peak"].to_numpy()
    _, c["aki_cc"], c["aki_neg"] = aki_labels(c["cr_base"], c["cr_peak"], c["cr_n_post"], cfg04["aki_ratio"])
    c["la_peak"] = s_la["peak"].to_numpy()
    _, c["hyper_cc"], c["hyper_neg"] = threshold_labels(c["la_peak"], c["la_n_post"], cfg04["lac_thr"])
    return c


def unit_shares(cohort_units, splits, hospitals, cols):
    """Part des séjours (split train) de chaque type d'unité nommé dans `cols` (« unit_<type> »), avec la même règle
    de nom et le même dénominateur que opcal_feas.site_descriptors. Nécessaire parce que site_descriptors ne crée que
    les colonnes des 6 types les plus fréquents parmi les hôpitaux qu'on lui passe : les 44 descripteurs gelés sont
    définis par leur nom, pas par ce classement."""
    c = cohort_units.merge(splits, on="patientunitstayid")
    c = c[(c["split"] == "train") & c["hospitalid"].isin(hospitals)]
    name = "unit_" + c["unittype"].astype(str).str.lower().str.replace(r"[^0-9a-z]+", "_", regex=True).str.strip("_")
    out = pd.DataFrame(index=pd.Index(sorted(int(h) for h in hospitals), name="hospitalid"))
    for col in cols:
        out[col] = c.assign(f=(name == col).astype(float)).groupby("hospitalid")["f"].mean().reindex(out.index)
    return out


def _final_hospitals(data_dir, dev, locked):
    norm = od.load_normalizer(data_dir, "final")
    train_h = [int(h) for h in norm["train_hospitals"]]
    held_h = [int(h) for h in norm["heldout_hospitals"]]
    assert set(train_h) == set(dev) and set(held_h) == set(locked) and not set(train_h) & set(held_h), \
        "fold_final.json ne correspond pas au protocole."
    return norm, train_h, held_h


def _strip_labels(c):
    for k in ("y_mortality", "y_aki", "aki_ascertained", "y_los_gt7", "apache_pred"):
        c.pop(k, None)
    return c


def load_final_mortality(data_dir, dev, locked, mode="global"):
    """Comme opfl_fed.load_fold, pour le pli final ; les hôpitaux verrouillés n'ont pas de label (y = 0, jamais utilisé)."""
    norm, train_h, held_h = _final_hospitals(data_dir, dev, locked)
    clients = {}
    for h in train_h:
        c = od.load_client(data_dir, h, norm, mode=mode)
        clients[h] = {s: _pack_mort(c, s, "y_mortality") for s in ("train", "val", "test")}
    for h in held_h:
        c = _strip_labels(od.load_client(data_dir, h, norm, mode=mode))
        sub = od.select(c, ["val", "test"])
        clients[h] = {"valtest": {"X": torch.from_numpy(sub["X"]), "M": torch.from_numpy(sub["M"]),
                                  "D": torch.from_numpy(sub["Delta"]), "C": torch.from_numpy(sub["C"]),
                                  "S": torch.from_numpy(sub["S"]), "y": torch.zeros(len(sub["stay_id"])),
                                  "stay_id": np.asarray(sub["stay_id"])}}
    first = clients[train_h[0]]["train"]
    return {"fold": -1, "train_h": train_h, "held_h": held_h, "clients": clients,
            "n_feat": int(first["X"].shape[2]), "n_static": int(first["S"].shape[1])}


def build_final_population(data_dir, population, dev, locked, mode="global"):
    """Comme opfl_labelfl.build_fold, pour le pli final ; séjours limités à `population`."""
    norm, train_h, held_h = _final_hospitals(data_dir, dev, locked)
    pop = np.asarray(sorted(int(s) for s in population))
    codes = od.SPLIT_CODES
    clients = {}
    for h in train_h + held_h:
        c = od.load_client(data_dir, h, norm, mode=mode)
        if h in held_h:
            c = _strip_labels(c)
        inpop = np.isin(c["stay_id"], pop)
        if h in train_h:
            clients[h] = {s: _pack_pop(c, inpop & (c["split"] == codes[s])) for s in ("train", "val", "test")}
        else:
            clients[h] = {"valtest": _pack_pop(c, inpop & np.isin(c["split"], [codes["val"], codes["test"]]))}
    ref = clients[train_h[0]]["train"]
    return {"fold": -1, "train_h": train_h, "held_h": held_h, "clients": clients,
            "n_feat": int(ref["X"].shape[2]), "n_static": int(ref["S"].shape[1])}


def average_seeds(frames, role):
    """Moyenne des prédictions d'un rôle sur les seeds, une ligne par séjour ; lp = logit de la moyenne."""
    d = pd.concat([f[f["role"] == role].assign(seed=i) for i, f in enumerate(frames)], ignore_index=True)
    agg = {"hospitalid": ("hospitalid", "first"), "p": ("p", "mean"), "n_seeds": ("seed", "nunique")}
    if "y" in d.columns and role != "transfer":
        agg["y"] = ("y", "first")
    out = d.groupby("stay_id").agg(**agg).reset_index()
    p = np.clip(out["p"].to_numpy(float), 1e-6, 1 - 1e-6)
    out["lp"] = np.log(p / (1 - p))
    return out


def conclusions(rej):
    """Formulation des conclusions fixée par l'amendement 1."""
    out = []
    if rej["C1a"]:
        out.append("Le signal de calibration des sites se transporte (C1a).")
        out.append("Amélioration de la calibration confirmée par rapport à la meilleure constante, sous le modèle (C1b)."
                   if rej["C1b"] else "L'ampleur du gain reste incertaine sur ce jeu (C1b non rejeté).")
        if rej["C2"]:
            out.append("Gain de vraisemblance confirmé contre l'absence de correction (C2).")
    else:
        out.append("Le transport du signal de calibration des sites n'est pas confirmé sur le test verrouillé (C1a non rejeté).")
    out.append("Mécanisme du dosage confirmé (C4)." if rej["C4"] else "Mécanisme du dosage non confirmé sur le test verrouillé (C4 non rejeté).")
    return out
