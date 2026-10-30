#!/usr/bin/env python3
"""Before/after comparison for the degraded-render re-judge of the 52 risky pairs.

Before = the original verdicts (<run>/judge/ for Opus 5.5, <run>/judge-gpt/ for GPT-6.1 Sol: HTML arm rendered as
written). After = <run>/judge-degraded/<judge>/ (HTML arm with the Outlook-unsupported features removed, MJML arm
unchanged). Per judge: consistent verdicts (html / mjml / split), HTML-arm and MJML-arm mean scores and their
difference on the five dimensions, exact McNemar test on "HTML wins the pair" before vs after, Wilcoxon on the
per-pair overall difference, Fisher's exact test of the after-rate against the safe-pair baseline, Wilson intervals,
the same split by whether the degradation removed a layout/content feature or only border-radius / box-shadow, and
a tally of words in the judges' reasons when the HTML arm was preferred.

usage: python3 -I analyze-degraded.py  → results-degraded.json next to this script, summary on stdout
"""
import json, os, re, sys, collections, random
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import degrade

DIMS = ("design", "readability", "briefCoverage", "phone", "overall")
JUDGES = {"opus": {"label": "Claude Opus 5.5", "before_dir": "judge", "safe": (101, 113, 44)},
          "gpt": {"label": "GPT-6.1 Sol", "before_dir": "judge-gpt", "safe": (98, 121, 39)}}
WORDS = {"polished": r"\bpolish", "card": r"\bcards?\b", "modern": r"\bmodern\b", "premium": r"\bpremium\b|\bupscale\b|\bluxur",
         "contrast": r"\bcontrast\b", "cut off": r"\bcut[- ]off\b|\bclipped\b|\bcropped\b", "overflow / sideways": r"\boverflow|\bsideways\b|\bhorizontal(ly)? scroll",
         "missing / invisible": r"\bmissing\b|\binvisible\b|\bblank\b|\bempty\b|\bdisappear", "broken": r"\bbroken\b|\bbreaks?\b",
         "cramped / stacked": r"\bcramped\b|\bstack(ed|s|ing)?\b|\bcrowded\b", "plain / basic": r"\bplain(er)?\b|\bbasic\b|\bbare\b|\bdated\b|\bgeneric\b"}


def load(path):
    if not os.path.exists(path): return None
    j = json.load(open(path))
    winners, scores, reasons = [], {"html": collections.defaultdict(list), "mjml": collections.defaultdict(list)}, []
    for o in j["orders"]:
        w = o["a"] if o["preferred"] == "A" else o["b"] if o["preferred"] == "B" else "tie"
        winners.append(w)
        for letter, fmt in (("A", o["a"]), ("B", o["b"])):
            for k in DIMS: scores[fmt][k].append(o[letter][k])
        reasons.append({"winner": w, "reason": o["reason"], "missing_html": o["A" if o["a"] == "html" else "B"]["missing"]})
    consistent = winners[0] if len(set(winners)) == 1 and winners[0] != "tie" else "split"
    return {"winners": winners, "consistent": consistent, "html_orders": winners.count("html"),
            "scores": {fmt: {k: sum(v) / len(v) for k, v in d.items()} for fmt, d in scores.items()}, "reasons": reasons, "cost": j.get("costUsd", 0)}


def wilson(k, n, z=1.96):
    if not n: return (None, None)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (c - h, c + h)


def boot(diffs, n=4000, seed=1):
    rnd = random.Random(seed); bs = sorted(sum(diffs[rnd.randrange(len(diffs))] for _ in diffs) / len(diffs) for _ in range(n))
    return {"mean": sum(diffs) / len(diffs), "lo": bs[int(0.025 * n)], "hi": bs[int(0.975 * n) - 1], "n": len(diffs)}


def counts(rows, key):
    c = collections.Counter(r[key]["consistent"] for r in rows)
    return {"html": c.get("html", 0), "mjml": c.get("mjml", 0), "split": c.get("split", 0), "n": len(rows)}


def compare(rows, judge):
    """rows: pairs with both before and after for this judge."""
    out = {"n": len(rows), "before": counts(rows, "before"), "after": counts(rows, "after")}
    for k in DIMS:
        b_h = [r["before"]["scores"]["html"][k] for r in rows]; b_m = [r["before"]["scores"]["mjml"][k] for r in rows]
        a_h = [r["after"]["scores"]["html"][k] for r in rows]; a_m = [r["after"]["scores"]["mjml"][k] for r in rows]
        out[k] = {"before_html": sum(b_h) / len(rows), "before_mjml": sum(b_m) / len(rows), "before_diff": sum(b_h) / len(rows) - sum(b_m) / len(rows),
                  "after_html": sum(a_h) / len(rows), "after_mjml": sum(a_m) / len(rows), "after_diff": sum(a_h) / len(rows) - sum(a_m) / len(rows),
                  "change_in_diff": boot([(ah - am) - (bh - bm) for ah, am, bh, bm in zip(a_h, a_m, b_h, b_m)]),
                  "change_in_html_score": boot([ah - bh for ah, bh in zip(a_h, b_h)]),
                  "change_in_mjml_score": boot([am - bm for am, bm in zip(a_m, b_m)])}
    # McNemar (exact) on "HTML wins the pair" (consistent == html), before vs after
    b = sum(1 for r in rows if r["before"]["consistent"] == "html" and r["after"]["consistent"] != "html")
    c = sum(1 for r in rows if r["before"]["consistent"] != "html" and r["after"]["consistent"] == "html")
    both = sum(1 for r in rows if r["before"]["consistent"] == "html" and r["after"]["consistent"] == "html")
    neither = len(rows) - b - c - both
    out["mcnemar_html_win"] = {"html_win_both": both, "html_win_before_only": b, "html_win_after_only": c, "html_win_neither": neither,
                               "p_exact_two_sided": stats.binomtest(min(b, c), b + c, 0.5).pvalue if b + c else 1.0}
    # same on "MJML wins the pair"
    b2 = sum(1 for r in rows if r["before"]["consistent"] == "mjml" and r["after"]["consistent"] != "mjml")
    c2 = sum(1 for r in rows if r["before"]["consistent"] != "mjml" and r["after"]["consistent"] == "mjml")
    out["mcnemar_mjml_win"] = {"mjml_win_before_only": b2, "mjml_win_after_only": c2, "p_exact_two_sided": stats.binomtest(min(b2, c2), b2 + c2, 0.5).pvalue if b2 + c2 else 1.0}
    # orders preferring HTML (0..2 per pair): sign test on the change
    d = [r["after"]["html_orders"] - r["before"]["html_orders"] for r in rows]
    pos, neg = sum(1 for x in d if x > 0), sum(1 for x in d if x < 0)
    out["sign_test_html_orders"] = {"before_orders_html": sum(r["before"]["html_orders"] for r in rows), "after_orders_html": sum(r["after"]["html_orders"] for r in rows),
                                    "of_orders": 2 * len(rows), "pairs_up": pos, "pairs_down": neg, "pairs_same": len(d) - pos - neg,
                                    "p_exact_two_sided": stats.binomtest(min(pos, neg), pos + neg, 0.5).pvalue if pos + neg else 1.0}
    # Wilcoxon on the per-pair overall difference (HTML − MJML), before vs after
    bd = [r["before"]["scores"]["html"]["overall"] - r["before"]["scores"]["mjml"]["overall"] for r in rows]
    ad = [r["after"]["scores"]["html"]["overall"] - r["after"]["scores"]["mjml"]["overall"] for r in rows]
    try:
        w = stats.wilcoxon(ad, bd, zero_method="wilcox"); out["wilcoxon_overall_diff"] = {"statistic": float(w.statistic), "p": float(w.pvalue)}
    except ValueError as e:
        out["wilcoxon_overall_diff"] = {"error": str(e)}
    # after-rate against the safe baseline
    sh, sm, ss = JUDGES[judge]["safe"]; sn = sh + sm + ss
    ah = out["after"]["html"]; bh = out["before"]["html"]; n = len(rows)
    out["vs_safe_baseline"] = {"safe": {"html": sh, "mjml": sm, "split": ss, "n": sn, "html_share": sh / sn},
                               "before_html_share": bh / n, "before_wilson": wilson(bh, n), "before_vs_safe_fisher_p": float(stats.fisher_exact([[bh, n - bh], [sh, sn - sh]])[1]),
                               "after_html_share": ah / n, "after_wilson": wilson(ah, n), "after_vs_safe_fisher_p": float(stats.fisher_exact([[ah, n - ah], [sh, sn - sh]])[1]),
                               "after_mjml_share": out["after"]["mjml"] / n, "safe_mjml_share": sm / sn}
    # reasons when the HTML arm was preferred
    for when in ("before", "after"):
        rs = [x["reason"] for r in rows for x in r[when]["reasons"] if x["winner"] == "html"]
        out[f"reasons_{when}_html_preferred"] = {"orders": len(rs), **{w: sum(1 for t in rs if re.search(p, t, re.I)) for w, p in WORDS.items()}}
        rs2 = [x["reason"] for r in rows for x in r[when]["reasons"] if x["winner"] == "mjml"]
        out[f"reasons_{when}_mjml_preferred"] = {"orders": len(rs2), **{w: sum(1 for t in rs2 if re.search(p, t, re.I)) for w, p in WORDS.items()}}
        out[f"missing_{when}_html_mean"] = sum(len(x["missing_html"]) for r in rows for x in r[when]["reasons"]) / (2 * len(rows))
    return out


def main():
    pairs = degrade.risky_pairs([os.path.join(HERE, "results-S.json"), os.path.join(HERE, "results-F.json")])
    removals = {(s["set"], s["brief"], s["slug"]): s for s in json.load(open(os.path.join(HERE, "degraded-removals.json")))}
    rows, cost = [], {"gpt": 0.0, "opus": 0.0}
    for p in pairs:
        rem = removals[(p["set"], p["brief"], p["slug"])]
        structural = any(k not in ("border-radius", "box-shadow") for k in rem["counts"])
        render = json.load(open(os.path.join(p["run"], p["brief"], f"raw-html__{p['slug']}", "degraded", "render.json")))
        row = {"set": p["set"], "brief": p["brief"], "slug": p["slug"], "risk": {"layout": p["layout"], "content": p["content"], "flags": p["flags"], "mso": p["mso"]},
               "removed": rem["counts"], "structural_removal": structural, "degraded_phone_scroll_width": render["phoneScrollWidth"]}
        for j, spec in JUDGES.items():
            before = load(os.path.join(p["run"], spec["before_dir"], p["brief"], f"{p['slug']}.json"))
            after = load(os.path.join(p["run"], "judge-degraded", j, p["brief"], f"{p['slug']}.json"))
            row[j] = {"before": before, "after": after}
            if after: cost[j] += after["cost"]
        rows.append(row)
    result = {"n_risky_pairs": len(rows), "n_structural_removal": sum(1 for r in rows if r["structural_removal"]),
              "removed_total": dict(sum((collections.Counter(r["removed"]) for r in rows), collections.Counter()).most_common()),
              "degraded_phone_overflow": [f"{r['set']} {r['brief']} {r['slug']} ({r['degraded_phone_scroll_width']} px)" for r in rows if r["degraded_phone_scroll_width"] > 375],
              "cost_usd": cost, "judges": {}}
    for j, spec in JUDGES.items():
        both = [{"before": r[j]["before"], "after": r[j]["after"], "structural": r["structural_removal"], "set": r["set"]} for r in rows if r[j]["before"] and r[j]["after"]]
        if not both: continue
        res = {"label": spec["label"], "n_judged_after": len(both), "all": compare(both, j)}
        s = [r for r in both if r["structural"]]; c = [r for r in both if not r["structural"]]
        if s: res["structural_removal_pairs"] = compare(s, j)
        if c: res["cosmetic_only_pairs"] = compare(c, j)
        for st in ("S", "F"):
            xs = [r for r in both if r["set"] == st]
            if xs: res[f"set_{st}"] = {"n": len(xs), "before": counts(xs, "before"), "after": counts(xs, "after")}
        result["judges"][j] = res
    # per-pair rows (verdicts and overall scores only)
    result["pairs"] = [{"set": r["set"], "brief": r["brief"], "slug": r["slug"], "risk": r["risk"], "removed": r["removed"], "structural_removal": r["structural_removal"],
                        "degraded_phone_scroll_width": r["degraded_phone_scroll_width"],
                        **{j: {w: ({"consistent": r[j][w]["consistent"], "winners": r[j][w]["winners"], "scores": r[j][w]["scores"], "reasons": [x["reason"] for x in r[j][w]["reasons"]]} if r[j][w] else None)
                               for w in ("before", "after")} for j in JUDGES}} for r in rows]
    json.dump(result, open(os.path.join(HERE, "results-degraded.json"), "w"), indent=1)

    print(f"{len(rows)} risky pairs; structural removal in {result['n_structural_removal']}; cost: " + ", ".join(f"{j} ${c:.2f}" for j, c in cost.items()))
    print("removed:", result["removed_total"]); print("phone overflow after degradation:", result["degraded_phone_overflow"])
    for j, res in result["judges"].items():
        a = res["all"]
        print(f"\n== {res['label']} ({res['n_judged_after']} pairs judged after) ==")
        print(f"verdicts  before HTML {a['before']['html']} : MJML {a['before']['mjml']} : split {a['before']['split']}   after HTML {a['after']['html']} : MJML {a['after']['mjml']} : split {a['after']['split']}")
        for k in DIMS:
            d = a[k]; ch = d["change_in_diff"]; hs = d["change_in_html_score"]
            print(f"  {k:14s} before HTML {d['before_html']:.2f} MJML {d['before_mjml']:.2f} diff {d['before_diff']:+.2f} | after HTML {d['after_html']:.2f} MJML {d['after_mjml']:.2f} diff {d['after_diff']:+.2f} | change in diff {ch['mean']:+.2f} [{ch['lo']:+.2f}, {ch['hi']:+.2f}]; HTML score change {hs['mean']:+.2f} [{hs['lo']:+.2f}, {hs['hi']:+.2f}]")
        m = a["mcnemar_html_win"]; print(f"  McNemar HTML-win: both {m['html_win_both']}, before only {m['html_win_before_only']}, after only {m['html_win_after_only']}, neither {m['html_win_neither']}; exact p = {m['p_exact_two_sided']:.4f}")
        m = a["mcnemar_mjml_win"]; print(f"  McNemar MJML-win: before only {m['mjml_win_before_only']}, after only {m['mjml_win_after_only']}; exact p = {m['p_exact_two_sided']:.4f}")
        s = a["sign_test_html_orders"]; print(f"  orders preferring HTML: {s['before_orders_html']} -> {s['after_orders_html']} of {s['of_orders']}; pairs up {s['pairs_up']} down {s['pairs_down']} same {s['pairs_same']}; sign p = {s['p_exact_two_sided']:.4f}")
        print(f"  Wilcoxon overall diff: {a['wilcoxon_overall_diff']}")
        v = a["vs_safe_baseline"]
        print(f"  HTML share: before {100*v['before_html_share']:.0f}% [{100*v['before_wilson'][0]:.0f}, {100*v['before_wilson'][1]:.0f}] (vs safe {100*v['safe']['html_share']:.0f}%: Fisher p = {v['before_vs_safe_fisher_p']:.4f}); after {100*v['after_html_share']:.0f}% [{100*v['after_wilson'][0]:.0f}, {100*v['after_wilson'][1]:.0f}] (Fisher p = {v['after_vs_safe_fisher_p']:.4f}); MJML share after {100*v['after_mjml_share']:.0f}% vs safe {100*v['safe_mjml_share']:.0f}%")
        for w in ("before", "after"):
            r = a[f"reasons_{w}_html_preferred"]; print(f"  reasons when HTML preferred, {w} ({r['orders']} orders): " + ", ".join(f"{k} {v}" for k, v in r.items() if k != "orders" and v))
            r = a[f"reasons_{w}_mjml_preferred"]; print(f"  reasons when MJML preferred, {w} ({r['orders']} orders): " + ", ".join(f"{k} {v}" for k, v in r.items() if k != "orders" and v))
        print(f"  missing items listed for HTML (mean per order): before {a['missing_before_html_mean']:.2f}, after {a['missing_after_html_mean']:.2f}")
        for sub in ("structural_removal_pairs", "cosmetic_only_pairs"):
            if sub in res:
                x = res[sub]; print(f"  {sub} (n={x['n']}): before {x['before']['html']}:{x['before']['mjml']}:{x['before']['split']} -> after {x['after']['html']}:{x['after']['mjml']}:{x['after']['split']}; McNemar p = {x['mcnemar_html_win']['p_exact_two_sided']:.4f}; overall diff {x['overall']['before_diff']:+.2f} -> {x['overall']['after_diff']:+.2f}")
        for st in ("S", "F"):
            if f"set_{st}" in res:
                x = res[f"set_{st}"]; print(f"  set {st} (n={x['n']}): before {x['before']['html']}:{x['before']['mjml']}:{x['before']['split']} -> after {x['after']['html']}:{x['after']['mjml']}:{x['after']['split']}")


if __name__ == "__main__":
    main()
