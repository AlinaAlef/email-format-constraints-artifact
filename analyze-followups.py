"""Results of the pre-registered follow-ups E1 (warned judge), E3 (gradient injection) and E4 (third judge):
shares with Wilson 95% intervals, McNemar exact tests against the original browser verdicts on the same pairs,
Fisher's exact test risky vs safe. Reads the verdict files under the two runs.
usage: venv/bin/python -I analyze-followups.py > followups.txt"""
import csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import judgelib as J
from scipy.stats import binomtest, fisher_exact
from statsmodels.stats.proportion import proportion_confint

rows = list(csv.DictReader(open(J.PAIRS_CSV)))
orig = {(r["set"], r["brief"], r["model"]): r for r in rows}
risky = [(p["set"], p["brief"], p["slug"]) for p in J.risky_pairs()]
safe = [(p["set"], p["brief"], p["slug"]) for p in J.safe_sample()]


def wilson(k, n):
    lo, hi = proportion_confint(k, n, method="wilson"); return f"{k}/{n} = {100*k/n:.0f}% [{100*lo:.0f}, {100*hi:.0f}]"


def mcnemar(before, after):
    """Exact McNemar on 'html win' vs not: discordant pairs b (html->not) and c (not->html)."""
    b = sum(1 for x, y in zip(before, after) if x == "html" and y != "html")
    c = sum(1 for x, y in zip(before, after) if x != "html" and y == "html")
    p = binomtest(min(b, c), b + c, 0.5).pvalue if b + c else 1.0
    return b, c, p


def load(subdir, judge, keys):
    out = {}
    for s, run in J.RUNS.items():
        out.update({(s, b, m): v for (b, m), v in J.load_verdicts(run, subdir, judge).items()})
    return [out.get(k, "missing") for k in keys]


def counts(vs): return {k: vs.count(k) for k in ("html", "mjml", "split", "missing")}


print("=== E1: judge told about the target client (52 risky pairs, browser screenshots) ===")
for judge in ("opus", "gpt"):
    before = [orig[k][f"{judge}_verdict"] for k in risky]
    print(f"[{judge}] browser (original): HTML {wilson(before.count('html'), 52)}; counts {counts(before)}")
    for variant in ("generic", "specific"):
        after = load(f"judge-warned-{variant}", judge, risky); n = sum(1 for v in after if v != "missing")
        if not n: print(f"[{judge}] {variant}: no verdicts yet"); continue
        b, c, p = mcnemar(before, after)
        print(f"[{judge}] warned {variant}: HTML {wilson(after.count('html'), n)}; counts {counts(after)}; McNemar html->not {b}, not->html {c}, p={p:.4f}")
    safe_share = sum(1 for k in (kk for kk in orig if kk not in set(risky)) if orig[k][f"{judge}_verdict"] == "html"); print(f"[{judge}] safe stratum (258): HTML {wilson(safe_share, 258)}")

print("\n=== E3: gradient injected into safe free-HTML emails (judged against the unchanged MJML) ===")
log = json.load(open(os.path.join(HERE, "injected-log.json"))); inj = [tuple(x["pair"].split("/")) for x in log if x["injected"]]
for judge in ("opus", "gpt"):
    before = [orig[k][f"{judge}_verdict"] for k in inj]; after = load("judge-injected", judge, inj); n = sum(1 for v in after if v != "missing")
    if not n: print(f"[{judge}] no verdicts yet"); continue
    b, c, p = mcnemar(before, after)
    print(f"[{judge}] before: HTML {wilson(before.count('html'), len(inj))} {counts(before)}; after: HTML {wilson(after.count('html'), n)} {counts(after)}; McNemar html->not {b}, not->html {c}, p={p:.4f}")

print("\n=== E4: third judge (Gemini 3.1 Pro preview), risky vs safe sample ===")
r = load("judge-gemini", "gemini", risky); s = load("judge-gemini", "gemini", safe)
nr, ns = sum(1 for v in r if v != "missing"), sum(1 for v in s if v != "missing")
if nr and ns:
    a, b_ = r.count("html"), nr - r.count("html"); c_, d = s.count("html"), ns - s.count("html")
    print(f"gemini risky: HTML {wilson(a, nr)} {counts(r)}; safe sample: HTML {wilson(c_, ns)} {counts(s)}; Fisher OR {((a*d)/(b_*c_)) if b_*c_ else float('inf'):.2f} p={fisher_exact([[a, b_], [c_, d]])[1]:.4f}")
    rd, sd = [v for v in r if v in ("html", "mjml")], [v for v in s if v in ("html", "mjml")]
    a2, b2, c2, d2 = rd.count("html"), rd.count("mjml"), sd.count("html"), sd.count("mjml")
    print(f"gemini, decided pairs only (secondary): risky {a2}:{b2}, safe {c2}:{d2}; OR {((a2*d2)/(b2*c2)) if b2*c2 else float('inf'):.2f} p={fisher_exact([[a2, b2], [c2, d2]])[1]:.4f}; splits risky {r.count('split')}, safe {s.count('split')}")
    for judge in ("opus", "gpt"):
        o = [orig[k][f"{judge}_verdict"] for k in risky + safe]; g = r + s
        both = [(x, y) for x, y in zip(o, g) if x in ("html", "mjml") and y in ("html", "mjml")]
        agree = sum(1 for x, y in both if x == y)
        # Cohen's kappa on stable verdicts
        n = len(both); ph = sum(1 for x, _ in both if x == "html") / n if n else 0; qh = sum(1 for _, y in both if y == "html") / n if n else 0
        pe = ph * qh + (1 - ph) * (1 - qh); po = agree / n if n else 0; kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
        print(f"agreement gemini vs {judge} on stable verdicts: {agree}/{n} = {100*po:.0f}%, kappa {kappa:.2f}")
    print(f"gemini original-judge comparison on the same safe sample: opus HTML {wilson(sum(1 for k in safe if orig[k]['opus_verdict']=='html'), 52)}, gpt HTML {wilson(sum(1 for k in safe if orig[k]['gpt_verdict']=='html'), 52)}")
else:
    print("no gemini verdicts yet")
