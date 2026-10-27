"""
tdtfl.models — modèles de TDT-FL (protocole 1.1).

Généré par notebooks/03_modeles_E0.ipynb (étape 1) : modifier le notebook, pas ce fichier.

- Régression logistique L2 locale : force de régularisation C choisie par les plis internes du train
  (log-loss hors plis) ; les prédictions hors plis au C retenu sont conservées (estimation croisée de E2).
- FedAvg, FedProx et SCAFFOLD pour la même régression logistique : participation complète, K pas de
  descente de gradient locale par round, pas local c / L_k (L_k : constante de Lipschitz du client).
  Objectif commun : log-loss moyenne pondérée par les effectifs + (λ/2)·||w||², avec λ = 1 / (C·N) ;
  c'est exactement l'objectif de scikit-learn pour le modèle centralisé au même C.
"""
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

C_GRID = (0.0001, 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0)
MIN_CLASS = 2          # moins de 2 événements (ou non-événements) : modèle constant
MAX_ITER = 2000
EPS = 1e-6


def sigmoid(z):
    return 0.5 * (1.0 + np.tanh(0.5 * np.asarray(z, dtype=np.float64)))


def logit(p):
    p = np.clip(np.asarray(p, dtype=np.float64), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def logloss(y, p):
    p = np.clip(np.asarray(p, dtype=np.float64), EPS, 1 - EPS)
    y = np.asarray(y, dtype=np.float64)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


class Linear:
    """Modèle logistique : p = sigmoid(X w + b)."""

    def __init__(self, w, b, **meta):
        self.w = np.asarray(w, dtype=np.float64)
        self.b = float(b)
        self.meta = meta

    def predict(self, X):
        return sigmoid(np.asarray(X, dtype=np.float64) @ self.w + self.b)

    @property
    def theta(self):
        return np.r_[self.w, self.b]


def constant_model(y, n_features):
    prev = (float(np.sum(y)) + 0.5) / (len(y) + 1.0)          # prévalence lissée
    return Linear(np.zeros(n_features), logit(prev), kind="constant")


def _too_few(y):
    s = float(np.sum(y))
    return min(s, len(y) - s) < MIN_CLASS


def refit(X, y, C):
    """Régression logistique L2 à C fixé (modèle constant si une classe est trop rare)."""
    if _too_few(y):
        return constant_model(y, X.shape[1])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        est = LogisticRegression(C=C, max_iter=MAX_ITER).fit(X, y.astype(int))
    n_warn = sum(issubclass(w.category, ConvergenceWarning) for w in caught)
    return Linear(est.coef_[0].copy(), est.intercept_[0], kind="logistic", C=float(C), convergence_warnings=n_warn)


def fit_local(X, y, folds, c_grid=C_GRID):
    """Choisit C par les plis internes, puis réentraîne sur tout le train.
    Renvoie (modèle, prédictions hors plis au C retenu, log-loss hors plis par C)."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    folds = np.asarray(folds)
    n = len(y)
    if _too_few(y):
        m = constant_model(y, X.shape[1])
        return m, np.full(n, sigmoid(m.b)), [np.nan] * len(c_grid)
    oof = np.full((len(c_grid), n), np.nan)
    n_warn = 0
    for k in np.unique(folds[folds >= 0]):
        va = folds == k
        tr = ~va
        if _too_few(y[tr]):
            oof[:, va] = (y[tr].sum() + 0.5) / (tr.sum() + 1.0)
            continue
        est = LogisticRegression(C=c_grid[0], max_iter=MAX_ITER, warm_start=True)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            for ci, c in enumerate(c_grid):
                est.set_params(C=c)
                est.fit(X[tr], y[tr].astype(int))
                oof[ci, va] = est.predict_proba(X[va])[:, 1]
        n_warn += sum(issubclass(w.category, ConvergenceWarning) for w in caught)
    losses = [logloss(y, o) for o in oof]
    best = int(np.nanargmin(losses))
    model = refit(X, y, c_grid[best])
    model.meta["cv_convergence_warnings"] = n_warn
    return model, oof[best], losses


# ----------------------------------------------------------------------------- fédéré
class Client:
    """Données d'entraînement d'un hôpital pour l'apprentissage fédéré."""

    def __init__(self, X, y, seed=0):
        self.X = np.asarray(X, dtype=np.float64)
        self.y = np.asarray(y, dtype=np.float64)
        self.n = len(self.y)
        self.L = lipschitz(self.X, seed=seed)


def lipschitz(X, n_iter=30, seed=0):
    """0,25 × plus grande valeur propre de [X 1]ᵀ[X 1] / n (puissance itérée)."""
    rng = np.random.default_rng(seed)
    n, p = X.shape
    v = rng.standard_normal(p + 1)
    v /= np.linalg.norm(v)
    lam = 1.0
    for _ in range(n_iter):
        u = X @ v[:-1] + v[-1]
        w = np.r_[X.T @ u, u.sum()] / n
        lam = float(np.linalg.norm(w))
        if lam == 0:
            return 0.25
        v = w / lam
    return 0.25 * lam


def _grad(theta, X, y, lam):
    r = sigmoid(X @ theta[:-1] + theta[-1]) - y
    g = np.empty_like(theta)
    g[:-1] = X.T @ r / len(y) + lam * theta[:-1]
    g[-1] = r.mean()
    return g


def objective(theta, clients, lam):
    """Log-loss moyenne pondérée par les effectifs + (λ/2)||w||² (objectif centralisé)."""
    N = sum(c.n for c in clients)
    loss = sum(c.n * logloss(c.y, sigmoid(c.X @ theta[:-1] + theta[-1])) for c in clients) / N
    return loss + 0.5 * lam * float(theta[:-1] @ theta[:-1])


def federated(clients, method="fedavg", rounds=100, local_steps=5, step_scale=1.0, lam=1e-4, mu=0.0,
              eval_fn=None, eval_every=10, theta0=None):
    """FedAvg, FedProx ou SCAFFOLD (option II) avec participation complète.
    Renvoie (modèle, historique [(round, eval_fn(theta))])."""
    if method not in ("fedavg", "fedprox", "scaffold"):
        raise ValueError(method)
    p = clients[0].X.shape[1]
    N = float(sum(c.n for c in clients))
    wts = [c.n / N for c in clients]
    theta = np.zeros(p + 1) if theta0 is None else np.array(theta0, dtype=np.float64)
    if method == "scaffold":
        c_glob = np.zeros(p + 1)
        c_loc = [np.zeros(p + 1) for _ in clients]
    history = []
    for r in range(1, rounds + 1):
        new = np.zeros_like(theta)
        dc = np.zeros_like(theta)
        for k, cl in enumerate(clients):
            eta = step_scale / (cl.L + lam + (mu if method == "fedprox" else 0.0))
            th = theta.copy()
            for _ in range(local_steps):
                g = _grad(th, cl.X, cl.y, lam)
                if method == "fedprox":
                    g += mu * (th - theta)
                elif method == "scaffold":
                    g += c_glob - c_loc[k]
                th -= eta * g
            if method == "scaffold":
                c_new = c_loc[k] - c_glob + (theta - th) / (local_steps * eta)
                dc += wts[k] * (c_new - c_loc[k])
                c_loc[k] = c_new
            new += wts[k] * th
        theta = new
        if method == "scaffold":
            c_glob = c_glob + dc
        if not np.all(np.isfinite(theta)):
            return None, history + [(r, np.inf)]
        if eval_fn is not None and (r % eval_every == 0 or r == rounds):
            history.append((r, float(eval_fn(theta))))
    model = Linear(theta[:-1], theta[-1], kind=method, rounds=rounds, local_steps=local_steps,
                   step_scale=step_scale, lam=lam, mu=mu)
    return model, history
