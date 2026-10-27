# %%writefile ../src/opfl_models.py
"""
opfl_models — encodeurs et classifieurs (OP-FL).

Généré par notebooks/02_baselines_h1.ipynb (étape 2) : modifier le notebook, pas ce fichier.

Variantes d'entrée (échelle d'ablation) :
- x_only   : X seul (niveau 0)
- obs_only : [M, Δ, C] seuls (signal du processus d'observation)
- x_obs    : [X, M, Δ, C] concaténés (niveau 1)
- grud     : GRU-D (Che et al., 2018), niveau 1, référence de la littérature
Toutes : dernier état caché ‖ S -> MLP -> logit.
"""
import torch
import torch.nn as nn

INPUT_KEYS = ("X", "M", "D", "C", "S")
MODEL_NAMES = ("x_only", "obs_only", "x_obs", "grud")


class Head(nn.Module):
    def __init__(self, hidden, n_static, head=32, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(hidden + n_static, head), nn.ReLU(),
                                 nn.Dropout(dropout), nn.Linear(head, 1))

    def forward(self, h, S):
        return self.net(torch.cat([h, S], dim=1)).squeeze(1)


class GRUClassifier(nn.Module):
    def __init__(self, variant, n_feat, n_static, hidden=64, head=32, dropout=0.1):
        super().__init__()
        mult = {"x_only": 1, "obs_only": 3, "x_obs": 4}[variant]
        self.variant = variant
        self.gru = nn.GRU(mult * n_feat, hidden, batch_first=True)
        self.head = Head(hidden, n_static, head, dropout)

    def encode_input(self, X, M, D, C):
        if self.variant == "x_only":
            return X
        if self.variant == "obs_only":
            return torch.cat([M, D, C], dim=-1)
        return torch.cat([X, M, D, C], dim=-1)

    def forward(self, X, M, D, C, S):
        _, h = self.gru(self.encode_input(X, M, D, C))
        return self.head(h[-1], S)


class GRUD(nn.Module):
    def __init__(self, n_feat, n_static, hidden=64, head=32, dropout=0.1):
        super().__init__()
        self.hidden = hidden
        self.w_gx = nn.Parameter(torch.empty(n_feat).uniform_(0.05, 0.5))   # décroissance des entrées (diagonale)
        self.b_gx = nn.Parameter(torch.zeros(n_feat))
        self.gamma_h = nn.Linear(n_feat, hidden)                            # décroissance de l'état caché
        self.cell = nn.GRUCell(2 * n_feat, hidden)
        self.head = Head(hidden, n_static, head, dropout)

    def forward(self, X, M, D, C, S):
        h = X.new_zeros(X.shape[0], self.hidden)
        for t in range(X.shape[1]):
            x, m, d = X[:, t], M[:, t], D[:, t]
            gx = torch.exp(-torch.relu(self.w_gx * d + self.b_gx))
            x_hat = m * x + (1 - m) * gx * x      # x = dernière valeur observée (forward-fill) ; moyenne = 0
            h = torch.exp(-torch.relu(self.gamma_h(d))) * h
            h = self.cell(torch.cat([x_hat, m], dim=1), h)
        return self.head(h, S)


def build_model(name, n_feat, n_static, hidden=64, head=32, dropout=0.1):
    if name == "grud":
        return GRUD(n_feat, n_static, hidden, head, dropout)
    return GRUClassifier(name, n_feat, n_static, hidden, head, dropout)


def n_params(model):
    return int(sum(p.numel() for p in model.parameters()))