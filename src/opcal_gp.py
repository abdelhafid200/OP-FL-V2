"""
opcal_gp — OP-Cal v2 : méta-régression à processus gaussien avec entrées incertaines (spécification 0.2).

  c_h = a_h + ε_h,  ε_h ~ N(0, v_h)          (CITL estimé, sites d'entraînement)
  a_h = μ + f(z_h) + u_h,  u_h ~ N(0, τ²),  f ~ GP(0, k)
  ẑ_h = z_h + δ_h,  δ_h ~ N(0, C_h)          (C_h diagonal : variances d'échantillonnage, sans label)
  k(z, z') = σ²_L exp(−‖z − z'‖²/2ℓ²_L) + σ²_R exp(−‖z − z'‖²/2ℓ²_R)

Étape A : débruitage empirique bayésien des entrées (z̄_h, P_h). Étape B : noyau espéré exact sous entrées
gaussiennes (Girard et al. 2003). Estimation : vraisemblance restreinte pénalisée par des a priori log-normaux,
μ par moindres carrés généralisés. Le terme mécanistique γ·g_h est ajouté hors de cette classe.
"""
import numpy as np
from scipy.optimize import minimize


def expected_rbf(Za, Pa, Zb, Pb, s2, ell, same=False):
    """E[σ² exp(−‖z_a − z_b‖²/2ℓ²)] pour z_a ~ N(Za, diag Pa), z_b ~ N(Zb, diag Pb) indépendants.
    same=True : matrice d'entraînement, la diagonale vaut σ² (même tirage)."""
    S = ell ** 2 + Pa[:, None, :] + Pb[None, :, :]                       # (na, nb, p)
    d2 = (Za[:, None, :] - Zb[None, :, :]) ** 2
    logk = -0.5 * np.sum(np.log(S / ell ** 2), axis=2) - 0.5 * np.sum(d2 / S, axis=2)
    K = s2 * np.exp(logk)
    if same:
        np.fill_diagonal(K, s2)
    return K


def _lognorm_logpdf(x, mu_log, sd_log):
    return -0.5 * ((np.log(x) - mu_log) / sd_log) ** 2


class SiteGP:
    """Ajuster sur les sites d'entraînement (ẑ, C diagonal, c, v), prédire pour des sites nouveaux (ẑ*, C*)."""

    def __init__(self, ell_L=None, prior_scale=0.03, starts=5, denoise=True, local=True):
        """local=False : composante RBF courte désactivée (σ²_R fixé à ~0) — ablation et test T2."""
        self.ell_L_fixed, self.prior_scale, self.starts, self.denoise, self.local = ell_L, prior_scale, starts, denoise, local

    # --- standardisation et débruitage (paramètres appris sur l'entraînement)
    def _prep(self, Zhat, C):
        Z = (np.where(np.isfinite(Zhat), Zhat, self.fill) - self.mz) / self.sz
        Cs = np.nan_to_num(C, nan=0.0) / self.sz ** 2
        if not self.denoise:
            return Z, np.zeros_like(Z)
        lam = self.s2 / (self.s2 + Cs)
        return lam * Z, self.s2 * (1 - lam)                                   # m = 0 après standardisation

    def _K(self, theta, Za, Pa, Zb=None, Pb=None):
        _, s2L, s2R, ellR = np.exp(theta)
        same = Zb is None
        Zb, Pb = (Za, Pa) if same else (Zb, Pb)
        return expected_rbf(Za, Pa, Zb, Pb, s2L, self.ell_L, same) + expected_rbf(Za, Pa, Zb, Pb, s2R, ellR, same)

    def _parts(self, theta):
        t2 = np.exp(theta[0])
        S = self._K(theta, self.Z, self.P) + np.diag(self.v + t2)
        L = np.linalg.cholesky(S)
        Si = np.linalg.solve(L.T, np.linalg.solve(L, np.eye(len(self.c))))
        one = np.ones(len(self.c))
        a = one @ Si @ one
        mu = float(one @ Si @ self.c / a)
        r = self.c - mu
        return Si, a, mu, r, 2 * np.log(np.diag(L)).sum()

    def _obj(self, theta):
        try:
            Si, a, mu, r, logdet = self._parts(theta)
        except np.linalg.LinAlgError:
            return 1e12
        reml = -0.5 * (logdet + np.log(a) + r @ Si @ r)
        t2, s2L, s2R, ellR = np.exp(theta)
        # a priori sur la variance ENTRE SITES apportée par chaque composante : σ²_s (1 − k̄_s), avec k̄_s la
        # corrélation moyenne entre sites d'entraînement ; un RBF long a k̄ proche de 1, donc σ²_L doit être grand.
        kR = 1 - np.mean(np.exp(-self.D2 / (2 * ellR ** 2)))
        lp = (_lognorm_logpdf(t2, np.log(self.prior_scale), 1.5)
              + _lognorm_logpdf(s2L * self.kL, np.log(self.prior_scale), 1.5)
              + _lognorm_logpdf(max(s2R * kR, 1e-300), np.log(self.prior_scale), 1.5)
              + _lognorm_logpdf(ellR, np.log(0.5 * self.med), 0.5))
        return -(reml + lp)

    def fit(self, Zhat, C, c, v):
        Zhat, C = np.asarray(Zhat, float), np.asarray(C, float)
        self.c, self.v = np.asarray(c, float), np.asarray(v, float)
        with np.errstate(all="ignore"):
            fill = np.nanmean(Zhat, 0)
        self.fill = np.where(np.isfinite(fill), fill, 0.0)
        Zf = np.where(np.isfinite(Zhat), Zhat, self.fill)
        self.mz, sd = Zf.mean(0), Zf.std(0)
        self.sz = np.where(sd > 1e-9, sd, 1.0)
        Zs, Cs = (Zf - self.mz) / self.sz, np.nan_to_num(C, nan=0.0) / self.sz ** 2
        vz = Zs.var(0)
        self.s2 = np.maximum(vz - Cs.mean(0), 0.05 * np.maximum(vz, 1e-12))
        self.Z, self.P = self._prep(Zhat, C)
        dist = np.sqrt(((self.Z[:, None] - self.Z[None]) ** 2).sum(2))[np.triu_indices(len(self.c), 1)]
        self.med = float(np.median(dist)) if len(dist) else 1.0
        self.ell_L = self.ell_L_fixed if self.ell_L_fixed is not None else 2 * self.med
        self.D2 = dist ** 2
        self.kL = max(1 - float(np.mean(np.exp(-self.D2 / (2 * self.ell_L ** 2)))), 1e-6)
        lo = np.log([1e-6, 1e-6, 1e-6, 0.05 * self.med])
        hi = np.log([5.0, 5.0 / self.kL, 5.0 if self.local else 1e-6, 10 * self.med])
        g = 1 / self.kL                                                      # σ²_L de départ à l'échelle du signal entre sites
        grid = [(0.03, 0.03 * g, 0.01, 0.5), (0.01, 0.06 * g, 0.005, 0.5), (0.06, 0.01 * g, 0.01, 1.0),
                (0.02, 0.02 * g, 0.03, 0.25), (0.04, 0.04 * g, 0.001, 2.0)][: self.starts]
        best = None
        for t2, sL, sR, fr in grid:
            x0 = np.minimum(np.log([t2, sL, sR, fr * self.med]), hi)
            res = minimize(self._obj, x0, method="L-BFGS-B", bounds=list(zip(lo, hi)))
            if best is None or res.fun < best.fun:
                best = res
        self.converged = bool(best.success and best.fun < 1e11)
        self.theta = best.x
        self.at_bound = bool(np.any(np.isclose(best.x, lo, atol=1e-3) | np.isclose(best.x, hi, atol=1e-3)))
        self.Si, self.a, self.mu, r, _ = self._parts(self.theta)
        self.alpha = self.Si @ r
        self.tau2, self.s2L, self.s2R, self.ellR = np.exp(self.theta)
        return self

    def predict(self, Zhat, C=None):
        Zhat = np.atleast_2d(np.asarray(Zhat, float))
        C = np.zeros_like(Zhat) if C is None else np.atleast_2d(np.asarray(C, float))
        Zs, Ps = self._prep(Zhat, C)
        Ks = self._K(self.theta, Zs, Ps, self.Z, self.P)
        mean = self.mu + Ks @ self.alpha
        one = np.ones(len(self.c))
        q = Ks @ self.Si
        var = (self.s2L + self.s2R) - np.einsum("ij,ij->i", q, Ks) + self.tau2 + (1 - q @ one) ** 2 / self.a
        return mean, np.maximum(var, 1e-9)