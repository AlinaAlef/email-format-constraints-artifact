#!/usr/bin/env python3
"""The third arm on set S: MJML with a styling-vocabulary reference (v1, v2) vs the same HTML emails.
Judge verdicts (both orders), mean scores, and the audit of the styled emails (fallbacks, media queries,
layout/content risks in Outlook Windows and Gmail web), for the four Claude 5.x models that ran it.

usage: python3 -I styled-arm.py <run folder> <caniemail data.json>
"""
import json, os, sys, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import audit, analyze_formats as af  # noqa: E402


def judge_dir(run, d):
    rows = []
    for f in sorted(glob.glob(os.path.join(run, d, "*", "*.json"))):
        j = json.load(open(f))
        winners, scores = [], {"mjml": collections.defaultdict(list), "html": collections.defaultdict(list)}
        for o in j["orders"]:
            winners.append(o["a"] if o["preferred"] == "A" else o["b"] if o["preferred"] == "B" else "tie")
            for letter, fmt in (("A", o["a"]), ("B", o["b"])):
                for k in ("design", "readability", "briefCoverage", "phone", "overall"):
                    scores[fmt][k].append(o[letter][k])
        cons = winners[0] if len(set(winners)) == 1 else "split"
        rows.append({"brief": j["promptId"], "slug": j["slug"], "consistent": cons,
                     "scores": {fmt: {k: sum(v) / len(v) for k, v in dd.items()} for fmt, dd in scores.items()}})
    return rows


def main():
    run, db = sys.argv[1:3]
    feats = audit.load_db(db)
    out = {}
    for arm, jd in (("raw", "judge"), ("raw-mjml-styled", "judge-styled"), ("raw-mjml-styled-v2", "judge-styled-v2")):
        rows = judge_dir(run, jd)
        slugs = {r["slug"] for r in judge_dir(run, "judge-styled")}  # the four Claude 5.x models
        rows = [r for r in rows if r["slug"] in slugs]
        c = collections.Counter(r["consistent"] for r in rows)
        means = {fmt: {k: sum(r["scores"][fmt][k] for r in rows) / len(rows) for k in ("design", "readability", "briefCoverage", "phone", "overall")} for fmt in ("mjml", "html")}
        emails = [af.audit_email(p, feats) | {"cost": json.load(open(os.path.join(os.path.dirname(p), "result.json")))["costUsd"],
                                              "tokens": json.load(open(os.path.join(os.path.dirname(p), "result.json")))["outputTokens"]}
                  for p in sorted(glob.glob(os.path.join(run, "*", f"{arm}__*", "email.html")))
                  if os.path.basename(os.path.dirname(p)).split("__", 1)[1] in slugs and os.path.basename(os.path.dirname(os.path.dirname(p))) in {r["brief"] for r in rows}]
        n = len(emails)
        out[arm] = {"pairs": len(rows), "verdicts": dict(c), "mean_scores": means, "emails": n,
                    "mso": sum(e["mso"] for e in emails) / n, "media_query": sum(e["media_query"] for e in emails) / n,
                    "outlook_layout": sum(bool(e["clients"]["Outlook Windows"]["layout"]) for e in emails) / n,
                    "outlook_content": sum(bool(e["clients"]["Outlook Windows"]["content"]) for e in emails) / n,
                    "gmail_layout": sum(bool(e["clients"]["Gmail web"]["layout"]) for e in emails) / n,
                    "cost": sum(e["cost"] for e in emails) / n, "tokens": sum(e["tokens"] for e in emails) / n,
                    "words": sum(e["words"] for e in emails) / n, "phone_scroll": sum((e["phone_scroll"] if "phone_scroll" in e else 0) or 0 for e in emails)}
        print(f"{arm:22s} pairs {len(rows)} verdicts {dict(c)}  MJML-side overall {means['mjml']['overall']:.2f} design {means['mjml']['design']:.2f} readability {means['mjml']['readability']:.2f} phone {means['mjml']['phone']:.2f} | HTML-side overall {means['html']['overall']:.2f} design {means['html']['design']:.2f}")
        print(f"{'':22s} emails {n}: mso {out[arm]['mso']:.2f} mq {out[arm]['media_query']:.2f} outlook layout {out[arm]['outlook_layout']:.2f} content {out[arm]['outlook_content']:.2f} gmail layout {out[arm]['gmail_layout']:.2f} cost ${out[arm]['cost']:.3f} tokens {out[arm]['tokens']:.0f} words {out[arm]['words']:.0f}")
    json.dump(out, open(os.path.join(HERE, "results-styled.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
