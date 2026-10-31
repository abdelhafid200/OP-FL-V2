"""Tests unitaires T1–T3 de la spécification OP-Cal v2 (données synthétiques uniquement)."""
import numpy as np
from opcal_gp import SiteGP, expected_rbf

rng = np.random.default_rng(0)
ok_all = True

def report(name, ok, detail):
    global ok_all
    ok_all &= ok
    print(f"{'OK   ' if ok else 'ÉCHEC'} {name} : {detail}")

# --- T1 : retour vers μ̂ hors domaine
H, p = 50, 3
Z = rng.normal(size=(H, p)); C = np.full((H, p), 0.01)
a = 0.4 * Z[:, 0] - 0.3 * Z[:, 1] ** 2 + rng.normal(0, 0.1, H)
v = np.full(H, 0.03); c = a + rng.normal(0, np.sqrt(v))
m = SiteGP().fit(Z, C, c, v)
ts = [0.0, 2.0, 5.0, 20.0, 100.0]
pred = [m.predict(t * np.ones((1, p)) / np.sqrt(p), np.full((1, p), 0.01))[0][0] for t in ts]
gap = [abs(x - m.mu) for x in pred]
report("T1 retour à la moyenne", gap[-1] < 1e-6 and gap[-2] < 1e-3,
       " ; ".join(f"t={t:g}: |ã−μ̂|={g:.2e}" for t, g in zip(ts, gap)) + f" ; convergé={m.converged}")

# --- T2 : p = 1, f linéaire : prédiction à entrée bruitée ≈ calibration de régression μ + w·λ·(ẑ − m)
H = 200
z = rng.normal(0, 1, H); Ch = rng.uniform(0.01, 0.5, H)
zhat = z + rng.normal(0, np.sqrt(Ch)); v = np.full(H, 0.01)
c = 0.5 * z + rng.normal(0, np.sqrt(v))
m = SiteGP(ell_L=50.0, local=False).fit(zhat[:, None], Ch[:, None], c, v)
d = 0.05
w_hat = (m.predict(np.array([[d * m.sz[0] + m.mz[0]]]))[0][0] - m.predict(np.array([[-d * m.sz[0] + m.mz[0]]]))[0][0]) / (2 * d * m.sz[0])
errs = []
for zs, cs in [(1.5, 0.05), (1.5, 1.0), (-1.0, 2.0), (0.8, 0.3)]:
    lam = m.s2[0] / (m.s2[0] + cs / m.sz[0] ** 2)
    rc = m.predict(np.array([[m.mz[0]]]))[0][0] + w_hat * lam * (zs - m.mz[0])
    gp = m.predict(np.array([[zs]]), np.array([[cs]]))[0][0]
    errs.append((zs, cs, lam, gp, rc))
rel = max(abs(g - r) / max(abs(r - m.predict(np.array([[m.mz[0]]]))[0][0]), 1e-3) for *_, g, r in errs)
report("T2 cas p = 1 contre calibration de régression", rel < 0.05,
       f"écart relatif max {rel:.3f} ; pente estimée {w_hat:.3f} (vraie 0,5 ; atténuée par le bruit des entrées d'entraînement) ; "
       + " ; ".join(f"ẑ={zs:g}, C={cs:g}, λ={lam:.2f}: GP {g:.3f} / RC {r:.3f}" for zs, cs, lam, g, r in errs))

# --- T2b : débruitage en dimension 10 avec la règle par défaut (ℓ_L = 2 × médiane) : la pente le long du signal
# doit être plus proche de la vérité avec débruitage que sans (dé-atténuation)
H, p, w0 = 60, 10, 0.25
z = rng.normal(size=(H, p)); Cm = rng.uniform(0.05, 0.8, (H, p)); zh = z + rng.normal(size=(H, p)) * np.sqrt(Cm)
v = np.full(H, 0.02); c = w0 * z[:, 0] + rng.normal(0, np.sqrt(v))
sl = {}
for den in (True, False):
    mm = SiteGP(local=False, denoise=den).fit(zh, Cm, c, v)
    e = np.zeros((2, p)) + mm.mz; dd = 0.05 * mm.sz[0]; e[0, 0] += dd; e[1, 0] -= dd
    pr = mm.predict(e)[0]; sl[den] = (pr[0] - pr[1]) / (2 * dd)
naive = np.linalg.lstsq(np.column_stack([np.ones(H), zh]), c, rcond=None)[0][1]
report("T2b dé-atténuation (p = 10, règle par défaut)", abs(sl[True] - w0) < abs(sl[False] - w0),
       f"pente vraie {w0} ; avec débruitage {sl[True]:.3f} ; sans {sl[False]:.3f} ; MCO naïfs {naive:.3f}")

# --- T3 : K̃ semi-définie positive avec P très inégaux, et formule exacte contre Monte Carlo
H, p = 60, 5
Zb = rng.normal(size=(H, p)); P = np.exp(rng.uniform(np.log(1e-4), np.log(10), (H, p)))
K = expected_rbf(Zb, P, Zb, P, 1.0, 1.3, same=True) + expected_rbf(Zb, P, Zb, P, 0.5, 0.4, same=True)
lmin = float(np.linalg.eigvalsh(K).min())
n = 400_000
za = Zb[0] + rng.normal(size=(n, p)) * np.sqrt(P[0]); zb = Zb[1] + rng.normal(size=(n, p)) * np.sqrt(P[1])
mc = np.exp(-((za - zb) ** 2).sum(1) / (2 * 1.3 ** 2))
exact = expected_rbf(Zb[:1], P[:1], Zb[1:2], P[1:2], 1.0, 1.3)[0, 0]
se = mc.std() / np.sqrt(n)
report("T3 positivité et forme exacte", lmin >= -1e-10 and abs(mc.mean() - exact) < 4 * se,
       f"valeur propre min {lmin:.2e} ; exacte {exact:.5f} contre Monte Carlo {mc.mean():.5f} ± {se:.5f}")
print("TOUS LES TESTS RÉUSSIS" if ok_all else "AU MOINS UN TEST ÉCHOUE")
