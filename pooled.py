#!/usr/bin/env python3
"""Pooled numbers over results-S.json and results-F.json for the article: paired contrasts with bootstrap
intervals, risk shares by client and class, judge verdicts (both judges) overall, by model family and by
whether the HTML email carries a risk, claims and coverage, per-model rows.

usage: python3 -I pooled.py results-S.json results-F.json
"""
import json, sys, re, random, collections

FAM = lambda s: "Claude 5.x" if re.match(r"claude-(opus|sonnet|haiku|fable)-5", s) else "Claude 4.x" if s.startswith("claude") else "GPT-6"


def boot(pairs, n=4000, seed=1):
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    if not pairs: return None
    rnd = random.Random(seed); d = [a - b for a, b in pairs]
    boots = sorted(sum(d[rnd.randrange(len(d))] for _ in d) / len(d) for _ in range(n))
    return {"n": len(d), "html": sum(a for a, _ in pairs) / len(pairs), "mjml": sum(b for _, b in pairs) / len(pairs),
            "diff": sum(d) / len(d), "lo": boots[int(0.025 * n)], "hi": boots[int(0.975 * n) - 1]}


def fmt(v, pct=False, dec=3):
    if v is None: return "-"
    if pct: return f"{100*v['html']:.1f}% vs {100*v['mjml']:.1f}%  diff {100*v['diff']:+.1f} [{100*v['lo']:+.1f}, {100*v['hi']:+.1f}] n={v['n']}"
    return f"{v['html']:.{dec}f} vs {v['mjml']:.{dec}f}  diff {v['diff']:+.{dec}f} [{v['lo']:+.{dec}f}, {v['hi']:+.{dec}f}] n={v['n']}"


def main():
    emails, pairs = [], []
    for f in sys.argv[1:]:
        d = json.load(open(f)); s = d["summary"]["set"]
        ok = {(e["brief"], e["combo"]): e | {"set": s} for e in d["emails"] if e["ok"]}
        emails += ok.values()
        jmap = {(p["brief"], p["slug"]): p for p in d.get("pairs", [])}
        for (b, c), e in ok.items():
            if c.startswith("raw-html__"):
                m = ok.get((b, "raw__" + e["slug"]))
                if m: pairs.append({"set": s, "brief": b, "slug": e["slug"], "html": e, "mjml": m, **{k: v for k, v in jmap.get((b, e["slug"]), {}).items() if k.startswith("judge")}})
    H = [e for e in emails if e["format"] == "html"]; M = [e for e in emails if e["format"] == "mjml"]
    print(f"pooled: {len(H)} HTML, {len(M)} MJML, {len(pairs)} pairs")
    print("\n== paired contrasts (HTML − MJML) ==")
    for k in ("cost", "out_tokens", "sec", "bytes", "words", "bracket_placeholders"):
        print(f"{k:22s} {fmt(boot([(p['html'][k], p['mjml'][k]) for p in pairs]), dec=3 if k in ('cost','bracket_placeholders') else 0)}")
    rel = boot([(p["html"]["cost"] / p["mjml"]["cost"] if p["mjml"]["cost"] else None, 1.0) for p in pairs if p["mjml"]["cost"]])
    print(f"{'cost ratio HTML/MJML':22s} mean ratio {rel['html']:.2f} [{1+rel['lo']:.2f}, {1+rel['hi']:.2f}]")
    rel = boot([(p["html"]["out_tokens"] / p["mjml"]["out_tokens"], 1.0) for p in pairs])
    print(f"{'token ratio HTML/MJML':22s} mean ratio {rel['html']:.2f} [{1+rel['lo']:.2f}, {1+rel['hi']:.2f}]")
    print("\n== shares (emails) ==")
    for k in ("mso", "media_query", "table_layout", "google_fonts", "unsubscribe"):
        print(f"{k:22s} HTML {sum(e[k] for e in H)}/{len(H)} = {100*sum(e[k] for e in H)/len(H):.1f}%   MJML {sum(e[k] for e in M)}/{len(M)} = {100*sum(e[k] for e in M)/len(M):.1f}%")
    ph = [e for e in H if e["phone_scroll"] is not None]; pm = [e for e in M if e["phone_scroll"] is not None]
    print(f"{'phone overflow':22s} HTML {sum(1 for e in ph if e['phone_scroll']>375)}/{len(ph)}   MJML {sum(1 for e in pm if e['phone_scroll']>375)}/{len(pm)}")
    print(f"{'pipeline flag any':22s} HTML {sum(1 for e in H if e['pipeline_flags'])}/{len(H)}   MJML {sum(1 for e in M if e['pipeline_flags'])}/{len(M)}")
    print("pipeline flags HTML:", dict(collections.Counter(x for e in H for x in e["pipeline_flags"])))
    print("\n== risk shares by client (emails with ≥1 unsupported feature of the class, outside @media) ==")
    for cl in ("Outlook Windows", "Gmail web", "Gmail iOS", "Gmail Android", "Outlook.com", "Yahoo web", "Apple Mail iOS", "Apple Mail macOS", "Outlook macOS", "Outlook iOS", "Samsung Email"):
        row = []
        for cls in ("layout", "content", "fonts", "cosmetic"):
            h = sum(1 for e in H if e["clients"][cl][cls]); m = sum(1 for e in M if e["clients"][cl][cls])
            row.append(f"{cls} {h}/{len(H)} ({100*h/len(H):.1f}%) vs {m}/{len(M)} ({100*m/len(M):.1f}%)")
        print(f"{cl:18s} " + " | ".join(row))
    for cl in ("Outlook Windows", "Gmail web"):
        for cls in ("layout", "content"):
            print(f"paired {cl} {cls}: {fmt(boot([(float(bool(p['html']['clients'][cl][cls])), float(bool(p['mjml']['clients'][cl][cls]))) for p in pairs]), pct=True)}")
    print("\n== features behind the risks (HTML emails) ==")
    for cl in ("Outlook Windows", "Gmail web"):
        for cls in ("layout", "content"):
            print(f"{cl} {cls}: HTML {dict(collections.Counter(x for e in H for x in e['clients'][cl][cls]))}  MJML {dict(collections.Counter(x for e in M for x in e['clients'][cl][cls]))}")
    print("\n== by model family (HTML emails): risk and fallbacks ==")
    for fam in ("Claude 5.x", "Claude 4.x", "GPT-6"):
        xs = [e for e in H if FAM(e["slug"]) == fam]; ms = [e for e in M if FAM(e["slug"]) == fam]
        print(f"{fam:11s} n={len(xs):3d} outlook layout {sum(1 for e in xs if e['clients']['Outlook Windows']['layout'])}, content {sum(1 for e in xs if e['clients']['Outlook Windows']['content'])}, gmail layout {sum(1 for e in xs if e['clients']['Gmail web']['layout'])}, no-table {sum(1 for e in xs if not e['table_layout'])}, mso {sum(1 for e in xs if e['mso'])}, mq {sum(1 for e in xs if e['media_query'])} | MJML outlook layout {sum(1 for e in ms if e['clients']['Outlook Windows']['layout'])} content {sum(1 for e in ms if e['clients']['Outlook Windows']['content'])}")
    print("\n== claims and coverage (paired) ==")
    for judge in ("opus-5.5", "gpt-6.1-sol"):
        for k in ("invented_real", "placeholders", "coverage"):
            pp = [(p["html"]["claims"][judge][k], p["mjml"]["claims"][judge][k]) for p in pairs if judge in p["html"]["claims"] and judge in p["mjml"]["claims"]]
            print(f"{judge:12s} {k:14s} {fmt(boot(pp), dec=3)}")
        for s in ("S", "F"):
            pp = [(p["html"]["claims"][judge]["invented_real"], p["mjml"]["claims"][judge]["invented_real"]) for p in pairs if p["set"] == s and judge in p["html"]["claims"] and judge in p["mjml"]["claims"]]
            v = boot(pp)
            if v: print(f"{judge:12s} invented set {s}: {fmt(v, dec=2)}")
    print("\n== judges ==")
    for jk, label in (("judge_consistent", "Opus 5.5"), ("judge_gpt_consistent", "GPT-6.1 Sol")):
        jp = [p for p in pairs if p.get(jk)]
        c = collections.Counter(p[jk] for p in jp)
        print(f"{label}: {len(jp)} pairs — HTML {c.get('html',0)}, MJML {c.get('mjml',0)}, split {c.get('split',0)}, tie {c.get('tie',0)}")
        for s in ("S", "F"):
            c = collections.Counter(p[jk] for p in jp if p["set"] == s); print(f"   set {s}: {dict(c)}")
        for fam in ("Claude 5.x", "Claude 4.x", "GPT-6"):
            c = collections.Counter(p[jk] for p in jp if FAM(p["slug"]) == fam); print(f"   {fam}: {dict(c)}")
        risky = lambda p: bool(p["html"]["clients"]["Outlook Windows"]["layout"] or p["html"]["clients"]["Outlook Windows"]["content"] or p["html"]["pipeline_flags"])
        c1 = collections.Counter(p[jk] for p in jp if risky(p)); c0 = collections.Counter(p[jk] for p in jp if not risky(p))
        print(f"   HTML risky (Outlook layout/content or flag): {dict(c1)}  n={sum(c1.values())}   HTML safe: {dict(c0)} n={sum(c0.values())}")
        c1 = collections.Counter(p[jk] for p in jp if not p["html"]["table_layout"]); print(f"   HTML with no table layout: {dict(c1)}")
        sk = "judge_scores" if jk == "judge_consistent" else "judge_gpt_scores"
        for k in ("design", "readability", "briefCoverage", "phone", "overall"):
            v = boot([(p[sk]["html"][k], p[sk]["mjml"][k]) for p in jp if p.get(sk)])
            print(f"   {k:14s} {fmt(v, dec=2)}")
    both = [p for p in pairs if p.get("judge_consistent") and p.get("judge_gpt_consistent")]
    dec = [p for p in both if p["judge_consistent"] in ("html", "mjml") and p["judge_gpt_consistent"] in ("html", "mjml")]
    print(f"agreement: both judged {len(both)}; both decided {len(dec)}; agree {sum(1 for p in dec if p['judge_consistent']==p['judge_gpt_consistent'])}")
    print("\n== per model (pooled) ==")
    for slug in sorted({p["slug"] for p in pairs}, key=lambda s: (FAM(s), s)):
        xs = [p for p in pairs if p["slug"] == slug]
        h = [p["html"] for p in xs]; m = [p["mjml"] for p in xs]
        co = collections.Counter(p.get("judge_consistent") for p in xs); cg = collections.Counter(p.get("judge_gpt_consistent") for p in xs)
        print(f"{slug:22s} n={len(xs):2d} tok {sum(e['out_tokens'] for e in h)/len(h):5.0f}/{sum(e['out_tokens'] for e in m)/len(m):5.0f} $ {sum(e['cost'] for e in h)/len(h):.3f}/{sum(e['cost'] for e in m)/len(m):.3f} "
              f"HTML: table {sum(e['table_layout'] for e in h)} mso {sum(e['mso'] for e in h)} mq {sum(e['media_query'] for e in h)} outl-lay {sum(bool(e['clients']['Outlook Windows']['layout']) for e in h)} outl-cont {sum(bool(e['clients']['Outlook Windows']['content']) for e in h)} | opus {dict(co)} gpt {dict(cg)}")


if __name__ == "__main__":
    main()
