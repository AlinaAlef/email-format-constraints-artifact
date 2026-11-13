#!/usr/bin/env python3
"""Per-email measures and paired format contrasts for one run folder (set S or set F).

For every raw__<model> / raw-html__<model> email: client-support audit against Can I Email (features used
outside @media blocks only; a feature used only inside @media is progressive enhancement), classed as
layout / content / fonts / cosmetic; MSO fallback, media queries, table layout, bytes, Gmail clip; words,
placeholders; cost, tokens, seconds; phone scroll width; the blind pairwise judge's verdicts and scores;
the two claims judges' counts. Then paired contrasts (HTML minus MJML, paired by brief x model) with
bootstrap 95% intervals.

usage: python3 -I analyze-formats.py <set> <run folder> <caniemail data.json> <prompts json> [claims dir]
writes results-<set>.json next to this script and prints the summary.
"""
import json, os, re, sys, glob, random, collections, html as htmlmod
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit  # noqa: E402  (our own module next to this script)

CLIENTS = audit.CLIENTS
# features whose lack of support changes the layout of the email
LAYOUT = {
    "css-display-flex", "css-display-grid", "css-position", "css-float", "css-transform", "css-gap",
    "css-inset", "css-left-right-top-bottom", "css-flex-direction", "css-flex-wrap", "css-justify-content",
    "css-align-items", "css-grid-template", "css-aspect-ratio", "css-object-fit", "css-column-count", "css-z-index",
}
# features whose lack of support drops or hides content (text drawn by CSS, backgrounds that carry text,
# interactive elements, vector graphics)
CONTENT = {
    "css-pseudo-element-before", "css-pseudo-element-after", "css-linear-gradient", "css-radial-gradient",
    "css-conic-gradient", "html-svg", "image-svg", "html-form", "html-video", "html-audio", "html-picture",
    "html-input-text", "html-input-checkbox", "html-input-radio", "html-input-submit", "html-input-hidden",
    "html-button-submit", "html-button-reset", "html-button-button", "html-select", "html-textarea",
    "html-dialog", "html-meter", "html-progress", "html-object", "image-base64", "image-webp", "image-avif",
}
# web fonts: fall back to the declared system font
FONTS = {"css-at-import", "css-at-font-face", "html-link"}
NOT_RISK = {"css-at-media", "html-style", "html-body", "html-doctype", "html-comments"}
KEY_CLIENTS = ["Gmail web", "Gmail iOS", "Gmail Android", "Outlook Windows", "Outlook.com", "Apple Mail iOS", "Yahoo web"]


def split_media(css):
    """Return (css outside @media blocks, css inside them)."""
    out, inside = [], []
    i = 0
    while True:
        j = css.find("@media", i)
        if j < 0:
            out.append(css[i:]); break
        out.append(css[i:j])
        k = css.find("{", j)
        if k < 0:
            out.append(css[j:]); break
        depth, p = 1, k + 1
        while p < len(css) and depth:
            if css[p] == "{": depth += 1
            elif css[p] == "}": depth -= 1
            p += 1
        inside.append(css[k + 1:p - 1])
        i = p
    return "".join(out), "\n".join(inside)


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "title", "head"): self.skip += 1
        if tag in ("p", "div", "td", "tr", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table"): self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "title", "head") and self.skip: self.skip -= 1

    def handle_data(self, data):
        if not self.skip: self.out.append(data)


def visible_text(raw):
    raw = re.sub(r"<!--\[if[\s\S]*?<!\[endif\]-->", " ", raw, flags=re.I)
    raw = re.sub(r"<!--[\s\S]*?-->", " ", raw)
    p = Text(); p.feed(raw)
    return re.sub(r"\s+", " ", htmlmod.unescape("".join(p.out))).strip()


def audit_email(path, feats):
    raw = open(path, encoding="utf-8", errors="replace").read()
    c = audit.Collector(); c.feed(raw)
    outside, inside = set(), set()
    has_media = False
    for s in c.styles:
        o, m = split_media(s)
        if m.strip(): has_media = True
        outside |= audit.css_features(o, feats, True)
        inside |= audit.css_features(m, feats, True)
    for s in c.inline:
        outside |= audit.css_features(s, feats, False)
    outside |= audit.html_features(c, feats)
    outside.discard("css-at-media")
    inside_only = inside - outside
    per_client = {}
    for fam, plat, label in CLIENTS:
        unsupported = [s for s in sorted(outside) if audit.latest(feats[s]["stats"], fam, plat) == "n" and s not in NOT_RISK]
        per_client[label] = {
            "n": unsupported,
            "layout": [s for s in unsupported if s in LAYOUT],
            "content": [s for s in unsupported if s in CONTENT],
            "fonts": [s for s in unsupported if s in FONTS],
            "cosmetic": [s for s in unsupported if s not in LAYOUT and s not in CONTENT and s not in FONTS],
        }
    text = visible_text(raw)
    return {
        "features_outside": sorted(outside), "features_media_only": sorted(inside_only), "clients": per_client,
        "bytes": len(raw.encode("utf-8")), "gmail_clip": len(raw.encode("utf-8")) > 102 * 1024,
        "mso": bool(re.search(r"<!--\[if\s+(mso|gte mso|\(gte mso)", raw, re.I)),
        "media_query": has_media or bool(re.search(r"@media[^{]*(max|min)-width", raw, re.I)),
        "table_layout": bool(re.search(r"<table[\s>]", raw, re.I)),
        "google_fonts": bool(re.search(r"fonts\.googleapis\.com", raw, re.I)),
        "words": len(text.split()),
        "bracket_placeholders": len(re.findall(r"\[[^\]\n]{2,60}\]", text)),
        "merge_tags": len(re.findall(r"\{\{[^}]{1,40}\}\}", text)),
        "unsubscribe": bool(re.search(r"unsubscribe|opt[- ]?out|manage (your )?preferences", text, re.I)),
    }


def load_judge(run, brief, slug, dirname="judge"):
    f = os.path.join(run, dirname, brief, f"{slug}.json")
    if not os.path.exists(f): return None
    j = json.load(open(f))
    winners, scores = [], {"mjml": collections.defaultdict(list), "html": collections.defaultdict(list)}
    for o in j["orders"]:
        w = o["a"] if o["preferred"] == "A" else o["b"] if o["preferred"] == "B" else "tie"
        winners.append(w)
        for letter, fmt in (("A", o["a"]), ("B", o["b"])):
            for k in ("design", "readability", "briefCoverage", "phone", "overall"):
                scores[fmt][k].append(o[letter][k])
    consistent = winners[0] if len(set(winners)) == 1 and winners[0] != "tie" else "split" if "tie" not in winners and len(set(winners)) > 1 else winners[0] if len(set(winners)) == 1 else "split"
    first_slot_wins = sum(1 for o in j["orders"] if o["preferred"] == "A")
    return {"winners": winners, "consistent": consistent, "first_slot_wins": first_slot_wins,
            "scores": {fmt: {k: sum(v) / len(v) for k, v in d.items()} for fmt, d in scores.items()}}


def load_claims(claims_dir, set_name, brief, combo):
    out = {}
    if not claims_dir: return out
    for judge in ("opus-5.5", "gpt-6.1-sol"):
        f = os.path.join(claims_dir, set_name, judge, f"{brief}__{combo}.json")
        if not os.path.exists(f): continue
        j = json.load(open(f))
        inv = j["invented"]; req = j["required"]
        out[judge] = {"invented": len(inv), "invented_real": sum(1 for x in inv if not x.get("placeholder")),
                      "placeholders": sum(1 for x in inv if x.get("placeholder")),
                      "required": len(req), "covered": sum(1 for x in req if x.get("covered")),
                      "coverage": (sum(1 for x in req if x.get("covered")) / len(req)) if req else None}
    return out


def bootstrap_mean_diff(pairs, n=4000, seed=1):
    """pairs: list of (html_value, mjml_value). Returns (mean diff, lo, hi)."""
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    if not pairs: return None
    rnd = random.Random(seed)
    d = [a - b for a, b in pairs]
    mean = sum(d) / len(d)
    boots = []
    for _ in range(n):
        s = [d[rnd.randrange(len(d))] for _ in d]
        boots.append(sum(s) / len(s))
    boots.sort()
    return {"n": len(d), "diff": mean, "lo": boots[int(0.025 * n)], "hi": boots[int(0.975 * n) - 1],
            "html": sum(a for a, _ in pairs) / len(pairs), "mjml": sum(b for _, b in pairs) / len(pairs)}


def main():
    set_name, run, db, prompts_path = sys.argv[1:5]
    claims_dir = sys.argv[5] if len(sys.argv) > 5 else None
    feats = audit.load_db(db)
    prompts = {p["id"]: p for p in json.load(open(prompts_path))}
    emails = {}
    for rfile in sorted(glob.glob(os.path.join(run, "*", "raw*__*", "result.json"))):
        brief, combo = rfile.split(os.sep)[-3], rfile.split(os.sep)[-2]
        if brief not in prompts or not (combo.startswith("raw__") or combo.startswith("raw-html__")): continue
        r = json.load(open(rfile))
        html_path = os.path.join(os.path.dirname(rfile), "email.html")
        if not r.get("ok") or not os.path.exists(html_path):
            emails[(brief, combo)] = {"brief": brief, "combo": combo, "ok": False, "error": r.get("error") or r.get("htmlError")}
            continue
        fmt = "html" if combo.startswith("raw-html__") else "mjml"
        slug = combo.split("__", 1)[1]
        render = os.path.join(os.path.dirname(rfile), "render.json")
        e = {"brief": brief, "combo": combo, "format": fmt, "slug": slug, "model": r["model"], "ok": True,
             "cost": r["costUsd"], "out_tokens": r["outputTokens"], "in_tokens": r["inputTokens"], "sec": r["durationMs"] / 1000,
             "pipeline_flags": sorted((r.get("compat") or {}).get("layoutBreaking", {}).keys()),
             "phone_scroll": json.load(open(render)).get("phoneScrollWidth") if os.path.exists(render) else None}
        e.update(audit_email(html_path, feats))
        e["claims"] = load_claims(claims_dir, set_name, brief, combo)
        emails[(brief, combo)] = e
    ok = [e for e in emails.values() if e["ok"]]
    briefs = sorted({e["brief"] for e in ok}); slugs = sorted({e["slug"] for e in ok})
    pairs = []
    for b in briefs:
        for s in slugs:
            h = emails.get((b, f"raw-html__{s}")); m = emails.get((b, f"raw__{s}"))
            if h and m and h["ok"] and m["ok"]:
                pairs.append({"brief": b, "slug": s, "html": h, "mjml": m, "judge": load_judge(run, b, s), "judge_gpt": load_judge(run, b, s, "judge-gpt")})

    def share(fmt, pred):
        xs = [e for e in ok if e["format"] == fmt]
        return sum(1 for e in xs if pred(e)) / len(xs) if xs else None

    def mean(fmt, key):
        xs = [e[key] for e in ok if e["format"] == fmt and e.get(key) is not None]
        return sum(xs) / len(xs) if xs else None

    summary = {"set": set_name, "n_html": sum(1 for e in ok if e["format"] == "html"), "n_mjml": sum(1 for e in ok if e["format"] == "mjml"),
               "n_pairs": len(pairs), "failed": [(e["brief"], e["combo"], e.get("error")) for e in emails.values() if not e["ok"]]}
    for fmt in ("html", "mjml"):
        s = {k: mean(fmt, k) for k in ("cost", "out_tokens", "sec", "bytes", "words", "bracket_placeholders", "merge_tags")}
        s.update({"mso": share(fmt, lambda e: e["mso"]), "media_query": share(fmt, lambda e: e["media_query"]),
                  "table_layout": share(fmt, lambda e: e["table_layout"]), "google_fonts": share(fmt, lambda e: e["google_fonts"]),
                  "gmail_clip": share(fmt, lambda e: e["gmail_clip"]), "unsubscribe": share(fmt, lambda e: e["unsubscribe"]),
                  "phone_scroll": share(fmt, lambda e: (e["phone_scroll"] or 0) > 375),
                  "pipeline_flag_any": share(fmt, lambda e: bool(e["pipeline_flags"]))})
        for cl in KEY_CLIENTS:
            for cls in ("layout", "content", "fonts", "cosmetic"):
                s[f"{cl}|{cls}"] = share(fmt, lambda e, cl=cl, cls=cls: bool(e["clients"][cl][cls]))
            s[f"{cl}|any"] = share(fmt, lambda e, cl=cl: bool(e["clients"][cl]["n"]))
            s[f"{cl}|mean_n"] = mean_n = sum(len(e["clients"][cl]["n"]) for e in ok if e["format"] == fmt) / max(1, sum(1 for e in ok if e["format"] == fmt))
        for judge in ("opus-5.5", "gpt-6.1-sol"):
            xs = [e["claims"][judge] for e in ok if e["format"] == fmt and judge in e["claims"]]
            if xs:
                s[f"claims|{judge}|invented_real"] = sum(x["invented_real"] for x in xs) / len(xs)
                s[f"claims|{judge}|placeholders"] = sum(x["placeholders"] for x in xs) / len(xs)
                cov = [x["coverage"] for x in xs if x["coverage"] is not None]
                s[f"claims|{judge}|coverage"] = sum(cov) / len(cov) if cov else None
                s[f"claims|{judge}|n"] = len(xs)
        summary[fmt] = s
    # judge verdicts
    judged = [p for p in pairs if p["judge"]]
    cons = collections.Counter(p["judge"]["consistent"] for p in judged)
    summary["judge"] = {"n_pairs": len(judged), "html": cons.get("html", 0), "mjml": cons.get("mjml", 0), "split": cons.get("split", 0), "tie": cons.get("tie", 0),
                        "first_slot_share": sum(p["judge"]["first_slot_wins"] for p in judged) / max(1, 2 * len(judged))}
    for k in ("design", "readability", "briefCoverage", "phone", "overall"):
        summary["judge"][k] = bootstrap_mean_diff([(p["judge"]["scores"]["html"][k], p["judge"]["scores"]["mjml"][k]) for p in judged])
    judged2 = [p for p in pairs if p["judge_gpt"]]
    cons2 = collections.Counter(p["judge_gpt"]["consistent"] for p in judged2)
    summary["judge_gpt"] = {"n_pairs": len(judged2), "html": cons2.get("html", 0), "mjml": cons2.get("mjml", 0), "split": cons2.get("split", 0), "tie": cons2.get("tie", 0),
                            "first_slot_share": sum(p["judge_gpt"]["first_slot_wins"] for p in judged2) / max(1, 2 * len(judged2))}
    for k in ("design", "readability", "briefCoverage", "phone", "overall"):
        summary["judge_gpt"][k] = bootstrap_mean_diff([(p["judge_gpt"]["scores"]["html"][k], p["judge_gpt"]["scores"]["mjml"][k]) for p in judged2])
    both = [p for p in pairs if p["judge"] and p["judge_gpt"]]
    decided = [p for p in both if p["judge"]["consistent"] in ("html", "mjml") and p["judge_gpt"]["consistent"] in ("html", "mjml")]
    summary["judge_agreement"] = {"n_both": len(both), "n_both_decided": len(decided),
                                  "agree": sum(1 for p in decided if p["judge"]["consistent"] == p["judge_gpt"]["consistent"]),
                                  "overall_score_corr": None}
    if both:
        xs = [p["judge"]["scores"]["html"]["overall"] - p["judge"]["scores"]["mjml"]["overall"] for p in both]
        ys = [p["judge_gpt"]["scores"]["html"]["overall"] - p["judge_gpt"]["scores"]["mjml"]["overall"] for p in both]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)); sxx = sum((x - mx) ** 2 for x in xs); syy = sum((y - my) ** 2 for y in ys)
        summary["judge_agreement"]["overall_score_corr"] = sxy / ((sxx * syy) ** 0.5) if sxx and syy else None
    risky2 = [p for p in judged2 if p["html"]["clients"]["Outlook Windows"]["layout"] or p["html"]["pipeline_flags"]]
    summary["judge_gpt_when_html_risky"] = {"n": len(risky2), **dict(collections.Counter(p["judge_gpt"]["consistent"] for p in risky2))}
    # verdict by model family and by layout risk
    fam = lambda s: "claude-5" if re.match(r"claude-(opus|sonnet|haiku|fable)-5", s) else "claude-4" if s.startswith("claude") else "gpt"
    summary["judge_by_family"] = {}
    for f in ("claude-5", "claude-4", "gpt"):
        c = collections.Counter(p["judge"]["consistent"] for p in judged if fam(p["slug"]) == f)
        summary["judge_by_family"][f] = dict(c)
    risky = [p for p in judged if p["html"]["clients"]["Outlook Windows"]["layout"] or p["html"]["pipeline_flags"]]
    summary["judge_when_html_risky"] = {"n": len(risky), **dict(collections.Counter(p["judge"]["consistent"] for p in risky))}
    # paired contrasts
    summary["paired"] = {k: bootstrap_mean_diff([(p["html"][k], p["mjml"][k]) for p in pairs]) for k in ("cost", "out_tokens", "sec", "bytes", "words")}
    for cl in ("Gmail web", "Outlook Windows", "Gmail iOS"):
        for cls in ("layout", "content"):
            summary["paired"][f"{cl}|{cls}"] = bootstrap_mean_diff([(float(bool(p["html"]["clients"][cl][cls])), float(bool(p["mjml"]["clients"][cl][cls]))) for p in pairs])
    for judge in ("opus-5.5", "gpt-6.1-sol"):
        pp = [(p["html"]["claims"][judge]["invented_real"], p["mjml"]["claims"][judge]["invented_real"]) for p in pairs if judge in p["html"]["claims"] and judge in p["mjml"]["claims"]]
        summary["paired"][f"claims|{judge}|invented_real"] = bootstrap_mean_diff(pp)
        pp = [(p["html"]["claims"][judge]["coverage"], p["mjml"]["claims"][judge]["coverage"]) for p in pairs if judge in p["html"]["claims"] and judge in p["mjml"]["claims"]]
        summary["paired"][f"claims|{judge}|coverage"] = bootstrap_mean_diff(pp)
    # per model
    summary["by_model"] = {}
    for s in slugs:
        row = {}
        for fmt, prefix in (("html", "raw-html__"), ("mjml", "raw__")):
            xs = [e for e in ok if e["combo"] == f"{prefix}{s}"]
            if not xs: continue
            row[fmt] = {"n": len(xs), "cost": sum(e["cost"] for e in xs) / len(xs), "out_tokens": sum(e["out_tokens"] for e in xs) / len(xs),
                        "words": sum(e["words"] for e in xs) / len(xs), "mso": sum(e["mso"] for e in xs), "media_query": sum(e["media_query"] for e in xs),
                        "table_layout": sum(e["table_layout"] for e in xs),
                        "outlook_layout": sum(bool(e["clients"]["Outlook Windows"]["layout"]) for e in xs),
                        "gmail_layout": sum(bool(e["clients"]["Gmail web"]["layout"]) for e in xs),
                        "outlook_content": sum(bool(e["clients"]["Outlook Windows"]["content"]) for e in xs),
                        "pipeline_flags": sum(bool(e["pipeline_flags"]) for e in xs)}
        c = collections.Counter(p["judge"]["consistent"] for p in judged if p["slug"] == s)
        row["judge"] = dict(c)
        summary["by_model"][s] = row
    # most common unsupported features
    summary["top_unsupported"] = {}
    for cl in ("Outlook Windows", "Gmail web", "Gmail iOS"):
        summary["top_unsupported"][cl] = {fmt: collections.Counter(x for e in ok if e["format"] == fmt for x in e["clients"][cl]["n"]).most_common(12) for fmt in ("html", "mjml")}
    summary["pipeline_flags"] = {fmt: dict(collections.Counter(x for e in ok if e["format"] == fmt for x in e["pipeline_flags"])) for fmt in ("html", "mjml")}
    summary["run"] = os.path.abspath(run)
    pair_rows = [{"brief": p["brief"], "slug": p["slug"], "judge_consistent": p["judge"]["consistent"] if p["judge"] else None,
                  "judge_gpt_consistent": p["judge_gpt"]["consistent"] if p["judge_gpt"] else None, "judge_gpt_scores": p["judge_gpt"]["scores"] if p["judge_gpt"] else None,
                  "judge_winners": p["judge"]["winners"] if p["judge"] else None, "judge_scores": p["judge"]["scores"] if p["judge"] else None} for p in pairs]
    json.dump({"summary": summary, "emails": [e for e in emails.values()], "pairs": pair_rows}, open(os.path.join(HERE, f"results-{set_name}.json"), "w"), indent=1)

    # print
    print(f"set {set_name}: {summary['n_html']} HTML, {summary['n_mjml']} MJML, {summary['n_pairs']} pairs, failed {len(summary['failed'])}")
    keys = ["cost", "out_tokens", "sec", "bytes", "words", "bracket_placeholders", "mso", "media_query", "table_layout", "google_fonts", "gmail_clip", "unsubscribe", "phone_scroll", "pipeline_flag_any"] + \
           [f"{cl}|{cls}" for cl in KEY_CLIENTS for cls in ("layout", "content", "fonts", "cosmetic", "any", "mean_n")] + \
           [k for k in summary["html"] if k.startswith("claims|")]
    print(f"{'measure':40s} {'HTML':>10s} {'MJML':>10s}")
    for k in keys:
        a, b = summary["html"].get(k), summary["mjml"].get(k)
        f = lambda x: "-" if x is None else f"{x:.3f}" if isinstance(x, float) and abs(x) < 10 else f"{x:,.0f}" if isinstance(x, (int, float)) else str(x)
        print(f"{k:40s} {f(a):>10s} {f(b):>10s}")
    j = summary["judge"]
    print(f"\njudge: {j['n_pairs']} pairs — HTML {j['html']}, MJML {j['mjml']}, split {j['split']}, tie {j['tie']}; first-slot share {j['first_slot_share']:.2f}")
    for k in ("design", "readability", "briefCoverage", "phone", "overall"):
        d = j[k]; print(f"  {k:14s} HTML {d['html']:.2f} MJML {d['mjml']:.2f} diff {d['diff']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}]")
    print("judge by family:", summary["judge_by_family"]); print("judge when HTML risky:", summary["judge_when_html_risky"])
    g = summary["judge_gpt"]
    print(f"judge GPT: {g['n_pairs']} pairs — HTML {g['html']}, MJML {g['mjml']}, split {g['split']}, tie {g['tie']}; first-slot share {g['first_slot_share']:.2f}")
    for k in ("design", "readability", "briefCoverage", "phone", "overall"):
        d = g[k]
        if d: print(f"  {k:14s} HTML {d['html']:.2f} MJML {d['mjml']:.2f} diff {d['diff']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}]")
    print("agreement:", summary["judge_agreement"], "GPT when HTML risky:", summary["judge_gpt_when_html_risky"])
    print("\npaired contrasts (HTML − MJML):")
    for k, d in summary["paired"].items():
        if d: print(f"  {k:34s} n={d['n']:3d} HTML {d['html']:9.3f} MJML {d['mjml']:9.3f} diff {d['diff']:+9.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}]")
    print("\npipeline flags:", summary["pipeline_flags"])
    for cl, d in summary["top_unsupported"].items():
        print(f"\ntop unsupported in {cl}: HTML {d['html'][:8]}\n   MJML {d['mjml'][:8]}")
    print("\nby model:")
    for s, row in summary["by_model"].items():
        h, m = row.get("html", {}), row.get("mjml", {})
        print(f"  {s:26s} HTML n={h.get('n',0)} $%.3f tok %5.0f mso %d mq %d table %d outl-lay %d gmail-lay %d flags %d | MJML n=%d $%.3f tok %5.0f | judge %s" % (
            h.get("cost", 0), h.get("out_tokens", 0), h.get("mso", 0), h.get("media_query", 0), h.get("table_layout", 0), h.get("outlook_layout", 0), h.get("gmail_layout", 0), h.get("pipeline_flags", 0),
            m.get("n", 0), m.get("cost", 0), m.get("out_tokens", 0), row["judge"]))


if __name__ == "__main__":
    main()
