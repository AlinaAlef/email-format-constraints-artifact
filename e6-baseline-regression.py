"""E6 of preregistration-2026-11-08.md: does compatibility risk still predict the judges' preference once size and
complexity are controlled? Logistic regression per judge on data/pairs.csv + data/emails.csv of the public repo.
usage: venv/bin/python e6-baseline-regression.py > e6-baseline-regression.txt"""
import csv, numpy as np, statsmodels.api as sm
from scipy.stats import spearmanr
from scipy.optimize import brentq
from pathlib import Path
D = str(Path(__file__).resolve().parent / "data") + "/"
pairs = list(csv.DictReader(open(D + "pairs.csv")))
emails = {(e["set"], e["brief"], e["model"], e["format"]): e for e in csv.DictReader(open(D + "emails.csv"))}
cnt = lambda s: 0 if not s else len([x for x in s.split(";") if x])
def profile_ci(y, Xd, k, res):
    """95% profile-likelihood interval for coefficient k (the interval the pre-registration names)."""
    b, se, rest = res.params[k], res.bse[k], np.delete(Xd, k, axis=1)
    def f(v): return 2 * (res.llf - sm.GLM(y, rest, family=sm.families.Binomial(), offset=v * Xd[:, k]).fit().llf) - 3.841458820694124
    return brentq(f, b - 6 * se, b), brentq(f, b, b + 6 * se)


rows = []
for p in pairs:
    h = emails[(p["set"], p["brief"], p["model"], "html")]; m = emails[(p["set"], p["brief"], p["model"], "mjml")]
    rows.append({"risky": p["risky"] in ("True", "true", "1"), "set_F": p["set"] == "F",
                 "d_bytes": int(h["bytes"]) - int(m["bytes"]), "d_words": int(h["words"]) - int(m["words"]),
                 "html_cosmetic": cnt(h["outlook_windows_cosmetic"]), "html_features": cnt(h["features_outside_media_queries"]),
                 "opus": p["opus_verdict"] == "html", "gpt": p["gpt_verdict"] == "html", "family": p["family"]})
print(f"pairs {len(rows)}; risky {sum(r['risky'] for r in rows)}; HTML wins Opus {sum(r['opus'] for r in rows)}, GPT {sum(r['gpt'] for r in rows)}")
X = np.array([[r["risky"], r["d_bytes"], r["d_words"], r["html_cosmetic"], r["html_features"], r["set_F"]] for r in rows], float)
names = ["risky", "d_bytes", "d_words", "html_cosmetic", "html_features", "set_F"]
Xs = X.copy()
for j in (1, 2, 3, 4): Xs[:, j] = (X[:, j] - X[:, j].mean()) / X[:, j].std()
print("continuous predictors standardised (odds ratio per 1 SD): SDs bytes %.0f, words %.1f, cosmetic %.2f, features %.1f" % tuple(X[:, j].std() for j in (1, 2, 3, 4)))
for judge in ("opus", "gpt"):
    y = np.array([r[judge] for r in rows], float)
    for label, cols in (("risky only", [0]), ("risky + controls", [0, 1, 2, 3, 4, 5])):
        Xd = sm.add_constant(Xs[:, cols])
        res = sm.Logit(y, Xd).fit(disp=0, maxiter=200)
        ci = res.conf_int()
        print(f"\n[{judge}] {label}: n={len(y)}, pseudo-R2={res.prsquared:.3f}")
        for i, c in enumerate(cols):
            lo, hi = profile_ci(y, Xd, i + 1, res)
            print(f"  {names[c]:14s} OR {np.exp(res.params[i+1]):6.2f}  95% profile CI [{np.exp(lo):.2f}, {np.exp(hi):.2f}]  (Wald [{np.exp(ci[i+1][0]):.2f}, {np.exp(ci[i+1][1]):.2f}])  p={res.pvalues[i+1]:.4f}")
safe = [r for r in rows if not r["risky"]]
for judge in ("opus", "gpt"):
    for k in ("html_cosmetic", "html_features", "d_bytes"):
        rho, pv = spearmanr([r[k] for r in safe], [r[judge] for r in safe])
        print(f"safe pairs (n={len(safe)}), Spearman {k} vs HTML win [{judge}]: rho={rho:+.3f} p={pv:.3f}")
# the same regression with generator family instead of risky, to show the collinearity reviewers will ask about
fam = sorted(set(r["family"] for r in rows)); print("\nfamilies:", fam)
for judge in ("opus", "gpt"):
    y = np.array([r[judge] for r in rows], float)
    F = np.array([[r["family"] == f for f in fam[1:]] for r in rows], float)
    Xd = sm.add_constant(np.column_stack([Xs[:, [0]], F]))
    try:
        res = sm.Logit(y, Xd).fit(disp=0, maxiter=200); ci = res.conf_int()
        print(f"[{judge}] risky + family: risky OR {np.exp(res.params[1]):.2f} Wald [{np.exp(ci[1][0]):.2f}, {np.exp(ci[1][1]):.2f}] p={res.pvalues[1]:.4f}; " +
              "; ".join(f"{fam[i+1]} OR {np.exp(res.params[i+2]):.2f}" for i in range(len(fam)-1)))
    except Exception as e: print(f"[{judge}] risky + family: {type(e).__name__}: {e}")
