# %%writefile ../src/opfl_fed.py
"""
opfl_fed — apprentissage fédéré (FedAvg) pour OP-FL.

Généré par notebooks/02_baselines_h1.ipynb (étape 3) : modifier le notebook, pas ce fichier.

Règles : meilleur round choisi sur le split val POOLÉ des hôpitaux d'entraînement uniquement ;
hôpitaux tenus à l'écart jamais vus à l'entraînement, évalués sur val + test ;
le test verrouillé (fold="final") n'est pas chargé par ce module.
"""
import copy
import random
import time
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

import opfl_data as od
from opfl_metrics import auroc
from opfl_models import build_model, n_params, INPUT_KEYS

LABEL_KEYS = {"mortality": "y_mortality"}


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _pack(client, split, label_key):
    sub = od.select(client, split)
    return {"X": torch.from_numpy(sub["X"]), "M": torch.from_numpy(sub["M"]),
            "D": torch.from_numpy(sub["Delta"]), "C": torch.from_numpy(sub["C"]),
            "S": torch.from_numpy(sub["S"]),
            "y": torch.from_numpy(np.asarray(sub[label_key], np.float32)),
            "stay_id": np.asarray(sub["stay_id"])}


def load_fold(data_dir, fold, task="mortality", mode="global"):
    if str(fold) == "final":
        raise ValueError("Le test verrouillé ne se charge pas avec load_fold.")
    label_key = LABEL_KEYS[task]
    norm = od.load_normalizer(data_dir, fold)
    train_h, held_h = od.fold_hospitals(data_dir, fold)
    clients = {}
    for h in train_h:
        c = od.load_client(data_dir, h, norm, mode=mode)
        clients[int(h)] = {s: _pack(c, s, label_key) for s in ("train", "val", "test")}
    for h in held_h:
        c = od.load_client(data_dir, h, norm, mode=mode)
        clients[int(h)] = {"valtest": _pack(c, ["val", "test"], label_key)}
    first = clients[int(train_h[0])]["train"]
    return {"fold": int(fold), "train_h": [int(h) for h in train_h], "held_h": [int(h) for h in held_h],
            "clients": clients, "n_feat": int(first["X"].shape[2]), "n_static": int(first["S"].shape[1])}


@torch.no_grad()
def predict(model, data, batch_size=2048):
    model.eval()
    n = len(data["y"])
    out = [torch.sigmoid(model(*[data[k][i:i + batch_size] for k in INPUT_KEYS]))
           for i in range(0, n, batch_size)]
    return torch.cat(out).numpy() if out else np.zeros(0, np.float32)


def local_train(model, data, cfg, gen):
    model.train()
    opt = torch.optim.Adam(model.parameters(), lr=cfg["lr"])
    n, total = len(data["y"]), 0.0
    for _ in range(cfg["local_epochs"]):
        perm = torch.randperm(n, generator=gen)
        for i in range(0, n, cfg["batch_size"]):
            idx = perm[i:i + cfg["batch_size"]]
            logit = model(*[data[k][idx] for k in INPUT_KEYS])
            loss = F.binary_cross_entropy_with_logits(logit, data["y"][idx])
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg["grad_clip"])
            opt.step()
            total += float(loss.item()) * len(idx)
    return total / max(n * cfg["local_epochs"], 1)


def fedavg_(global_model, states, weights):
    w = np.asarray(weights, float)
    w = w / w.sum()
    avg = {k: sum(float(wi) * s[k].float() for wi, s in zip(w, states)) for k in states[0]}
    global_model.load_state_dict(avg)


def run_federated(fd, model_name, seed, cfg, rounds=None, verbose=True):
    set_seed(seed)
    model = build_model(model_name, fd["n_feat"], fd["n_static"], cfg["hidden"], cfg["head"], cfg["dropout"])
    rng = np.random.default_rng(seed)
    gen = torch.Generator().manual_seed(seed)
    C, train_h = fd["clients"], fd["train_h"]
    n_sel = max(1, int(round(cfg["client_frac"] * len(train_h))))
    y_val = np.concatenate([C[h]["val"]["y"].numpy() for h in train_h])
    R = rounds or cfg["rounds"]
    best_auc, best_state, best_round, hist = -np.inf, None, 0, []
    for r in range(1, R + 1):
        t0 = time.time()
        sel = [int(h) for h in rng.choice(train_h, size=n_sel, replace=False)]
        states, weights, losses = [], [], []
        for h in sel:
            local = copy.deepcopy(model)
            losses.append(local_train(local, C[h]["train"], cfg, gen))
            states.append(local.state_dict())
            weights.append(len(C[h]["train"]["y"]))
        fedavg_(model, states, weights)
        p_val = np.concatenate([predict(model, C[h]["val"]) for h in train_h])
        va = auroc(y_val, p_val)
        hist.append({"round": r, "train_loss": float(np.average(losses, weights=weights)),
                     "val_auroc": va, "seconds": time.time() - t0})
        if va > best_auc:
            best_auc, best_state, best_round = va, copy.deepcopy(model.state_dict()), r
        if verbose:
            print(f"    round {r:2d}/{R} | perte {hist[-1]['train_loss']:.4f} | "
                  f"AUROC val {va:.4f} | {hist[-1]['seconds']:.1f} s   ", end="\r")
    if verbose:
        print()
    model.load_state_dict(best_state)

    rows = []
    def add(h, data, role):
        rows.append(pd.DataFrame({"stay_id": data["stay_id"], "hospitalid": h, "role": role,
                                  "y": data["y"].numpy().astype(np.int8), "p": predict(model, data)}))
    for h in train_h:
        add(h, C[h]["val"], "val")
        add(h, C[h]["test"], "intra")
    for h in fd["held_h"]:
        add(h, C[h]["valtest"], "transfer")
    info = {"best_round": best_round, "best_val_auroc": float(best_auc), "n_params": n_params(model),
            "seconds": float(sum(x["seconds"] for x in hist))}
    return pd.concat(rows, ignore_index=True), pd.DataFrame(hist), info