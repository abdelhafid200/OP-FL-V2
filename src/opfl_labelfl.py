"""
opfl_labelfl — apprentissage fédéré quand le label dépend de la politique de dosage de l'hôpital (OP-FL).

Généré par notebooks/05_raccourci_masquage.ipynb (étape 1) : modifier le notebook, pas ce fichier.

- build_fold / restrict : clients d'un pli limités à une population de séjours, éventuellement à certains hôpitaux.
- set_labels : label d'entraînement y et poids w (0 = label non utilisable) pour les hôpitaux d'entraînement.
- run_fl : FedAvg (réglages du notebook 02) ; meilleur round sur le val poolé des hôpitaux d'entraînement,
  avec les labels d'entraînement.
- degrade_labels : applique à un hôpital k la politique de dosage d'un hôpital j (masquage contrôlé).
- cluster_boot : IC à 95 % par bootstrap sur les hôpitaux ; auc_sub : AUROC sur un sous-ensemble.
"""
import copy
import time
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

import opfl_data as od
from opfl_fed import set_seed, fedavg_
from opfl_models import build_model, n_params, INPUT_KEYS
from opfl_metrics import auroc
from opfl_label import summarize_post, threshold_labels


def _pack(client, keep):
    return {"X": torch.from_numpy(client["X"][keep]), "M": torch.from_numpy(client["M"][keep]),
            "D": torch.from_numpy(client["Delta"][keep]), "C": torch.from_numpy(client["C"][keep]),
            "S": torch.from_numpy(client["S"][keep]), "stay_id": np.asarray(client["stay_id"])[keep]}


def build_fold(data_dir, fold, population, mode="global"):
    """Hôpitaux d'entraînement : train / val / test ; hôpitaux tenus à l'écart : valtest. Séjours limités à `population`."""
    if str(fold) == "final":
        raise ValueError("Le test verrouillé ne se charge pas ici.")
    norm = od.load_normalizer(data_dir, fold)
    tr, ho = od.fold_hospitals(data_dir, fold)
    train_h, held_h = [int(h) for h in tr], [int(h) for h in ho]
    locked = set(od.load_protocol(data_dir)["locked_test_hospitals"])
    if locked & set(train_h + held_h) or set(train_h) & set(held_h):
        raise ValueError("Hôpitaux du pli incohérents.")
    pop = np.asarray(sorted(int(s) for s in population))
    codes = od.SPLIT_CODES
    clients = {}
    for h in train_h + held_h:
        c = od.load_client(data_dir, h, norm, mode=mode)
        inpop = np.isin(c["stay_id"], pop)
        if h in train_h:
            clients[h] = {s: _pack(c, inpop & (c["split"] == codes[s])) for s in ("train", "val", "test")}
        else:
            clients[h] = {"valtest": _pack(c, inpop & np.isin(c["split"], [codes["val"], codes["test"]]))}
    ref = clients[train_h[0]]["train"]
    return {"fold": int(fold), "train_h": train_h, "held_h": held_h, "clients": clients,
            "n_feat": int(ref["X"].shape[2]), "n_static": int(ref["S"].shape[1])}


def restrict(fd, hospitals):
    hs = {int(h) for h in hospitals}
    return {**fd, "train_h": [h for h in fd["train_h"] if h in hs], "held_h": [h for h in fd["held_h"] if h in hs]}


def set_labels(fd, y, w):
    """y, w : Series indexées par stay_id. Label manquant (NaN) => poids 0."""
    y, w = pd.Series(y).astype(float), pd.Series(w).astype(float)
    for h in fd["train_h"]:
        for s in ("train", "val", "test"):
            p = fd["clients"][h][s]
            yy = y.reindex(p["stay_id"]).to_numpy(np.float32)
            ww = w.reindex(p["stay_id"]).to_numpy(np.float32)
            ww = np.where(np.isnan(yy) | np.isnan(ww), 0.0, ww).astype(np.float32)
            p["y"] = torch.from_numpy(np.nan_to_num(yy, nan=0.0).astype(np.float32))
            p["w"] = torch.from_numpy(ww)


@torch.no_grad()
def predict(model, data, batch_size=4096):
    model.eval()
    n = len(data["stay_id"])
    if n == 0:
        return np.zeros(0, np.float32)
    out = [torch.sigmoid(model(*[data[k][i:i + batch_size] for k in INPUT_KEYS])) for i in range(0, n, batch_size)]
    return torch.cat(out).numpy()


def local_train(model, data, cfg, gen):
    lab = torch.nonzero(data["w"] > 0).flatten()
    n = len(lab)
    if n == 0:
        return np.nan, 0
    model.train()
    opt = torch.optim.Adam(model.parameters(), lr=cfg["lr"])
    total = 0.0
    for _ in range(cfg["local_epochs"]):
        perm = lab[torch.randperm(n, generator=gen)]
        for i in range(0, n, cfg["batch_size"]):
            idx = perm[i:i + cfg["batch_size"]]
            logit = model(*[data[k][idx] for k in INPUT_KEYS])
            loss = F.binary_cross_entropy_with_logits(logit, data["y"][idx])
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg["grad_clip"])
            opt.step()
            total += float(loss.item()) * len(idx)
    return total / (n * cfg["local_epochs"]), n


def run_fl(fd, model_name, seed, cfg, verbose=True):
    set_seed(seed)
    model = build_model(model_name, fd["n_feat"], fd["n_static"], cfg["hidden"], cfg["head"], cfg["dropout"])
    rng = np.random.default_rng(seed)
    gen = torch.Generator().manual_seed(seed)
    C, train_h = fd["clients"], fd["train_h"]
    n_sel = max(1, int(round(cfg["client_frac"] * len(train_h))))
    vmask = [C[h]["val"]["w"].numpy() > 0 for h in train_h]
    y_val = np.concatenate([C[h]["val"]["y"].numpy()[m] for h, m in zip(train_h, vmask)])
    best_auc, best_state, best_round, hist = -np.inf, None, 0, []
    for r in range(1, cfg["rounds"] + 1):
        t0 = time.time()
        states, weights, losses = [], [], []
        for h in rng.choice(train_h, size=n_sel, replace=False):
            local = copy.deepcopy(model)
            loss, n = local_train(local, C[int(h)]["train"], cfg, gen)
            if n > 0:
                states.append(local.state_dict()); weights.append(n); losses.append(loss)
        if states:
            fedavg_(model, states, weights)
        p_val = np.concatenate([predict(model, C[h]["val"])[m] for h, m in zip(train_h, vmask)])
        va = auroc(y_val, p_val)
        hist.append({"round": r, "train_loss": float(np.average(losses, weights=weights)) if states else np.nan,
                     "val_auroc": va, "seconds": time.time() - t0})
        if np.isfinite(va) and va > best_auc:
            best_auc, best_state, best_round = va, copy.deepcopy(model.state_dict()), r
        if verbose:
            print(f"    round {r:2d}/{cfg['rounds']} | AUROC val {va:.4f} | {hist[-1]['seconds']:.1f} s   ", end="\r")
    if verbose:
        print()
    if best_state is None:                     # val sans les deux classes : dernier round
        best_round = cfg["rounds"]
    else:
        model.load_state_dict(best_state)
    rows = []
    def add(h, data, role):
        rows.append(pd.DataFrame({"stay_id": data["stay_id"], "hospitalid": h, "role": role,
                                  "p": predict(model, data).astype(np.float32)}))
    for h in train_h:
        add(h, C[h]["val"], "val")
        add(h, C[h]["test"], "intra")
    for h in fd["held_h"]:
        add(h, C[h]["valtest"], "transfer")
    info = {"best_round": best_round, "best_val_auroc": float(best_auc), "n_params": n_params(model),
            "n_train_labelled": int(sum(float(C[h]["train"]["w"].sum()) for h in train_h)),
            "seconds": float(sum(x["seconds"] for x in hist))}
    return pd.concat(rows, ignore_index=True), pd.DataFrame(hist), info


def degrade_labels(post, stays, assign, lp, offset, rate_t, thr, rng):
    """
    Applique aux hôpitaux k de `assign` la politique de dosage de l'hôpital assign[k].
    post : dosages [stay_id, offset, value] de la fenêtre du label ; stays : DataFrame indexé par stay_id (hospitalid).
    lp : score linéaire du modèle commun de redosage ; offset : décalage par hôpital ; rate_t : dosages / jour chez les redosés.
    Un patient redosé reste redosé avec la probabilité min(1, π_j / π_k) ; son premier dosage est gardé, les suivants
    avec la probabilité min(1, intensité_j / intensité_k). On ne peut que retirer des dosages, jamais en ajouter.
    """
    sig = lambda z: 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
    sub = stays[stays["hospitalid"].isin(list(assign))]
    k = sub["hospitalid"].to_numpy()
    j = np.array([assign[int(h)] for h in k])
    z = lp.reindex(sub.index).to_numpy()
    q = np.minimum(1.0, sig(z + offset.reindex(j).to_numpy()) / sig(z + offset.reindex(k).to_numpy()))
    kept = sub.index[rng.random(len(sub)) < q]
    m = post[post["stay_id"].isin(kept)].sort_values(["stay_id", "offset"], kind="stable")
    first = ~m["stay_id"].duplicated().to_numpy()
    hk = m["stay_id"].map(sub["hospitalid"])
    ratio = np.minimum(1.0, rate_t.reindex(hk.map(assign)).to_numpy() / rate_t.reindex(hk).to_numpy())
    m = m[first | (rng.random(len(m)) < ratio)]
    s = summarize_post(m, sub.index)
    obs, cc, neg = threshold_labels(s["peak"], s["n_post"], thr)
    return pd.DataFrame({"hospitalid": k, "policy_of": j, "q": q, "obs": obs, "y_cc": cc, "y_neg": neg}, index=sub.index)


def auc_sub(y, p, idx, mask=None):
    y, p = np.asarray(y, float)[idx], np.asarray(p, float)[idx]
    keep = ~np.isnan(y)
    if mask is not None:
        keep &= np.asarray(mask, bool)[idx]
    return auroc(y[keep], p[keep])


def cluster_boot(groups, stat, n_boot=1000, seed=0):
    """stat(idx) -> float. Rééchantillonne les hôpitaux (groupes) avec remise. Renvoie (estimation, IC bas, IC haut)."""
    groups = np.asarray(groups)
    uniq = np.unique(groups)
    members = [np.flatnonzero(groups == g) for g in uniq]
    est = float(stat(np.arange(len(groups))))
    rng = np.random.default_rng(seed)
    bs = np.array([stat(np.concatenate([members[i] for i in rng.integers(0, len(uniq), len(uniq))]))
                   for _ in range(n_boot)], float)
    lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    return est, float(lo), float(hi)
