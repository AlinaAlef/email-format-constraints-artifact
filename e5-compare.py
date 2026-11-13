"""E5 of preregistration-2026-11-08.md: run-to-run variation for two configurations (Claude Sonnet 4.6, GPT-6 Astra high)
on the 20 set-F briefs. Compares the original results-F.json with results-R.json (the re-run, produced by
analyze-formats.py on generation-approaches/2026-11-08-raw-formats-rerun). Descriptive.
usage: venv/bin/python -I e5-compare.py"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
orig = json.load(open(os.path.join(HERE, "results-F.json")))["emails"]
rerun = json.load(open(os.path.join(HERE, "results-R.json")))["emails"]
SLUGS = ("claude-sonnet-4-6", "gpt-6-astra__high")


def table(emails, slug, fmt):
    xs = [e for e in emails if e["ok"] and e["slug"] == slug and e["format"] == fmt]
    ow = lambda e: e["clients"]["Outlook Windows"]
    risk = sum(1 for e in xs if ow(e)["layout"] or ow(e)["content"])
    flags = sum(1 for e in xs if e["pipeline_flags"])
    mso = sum(1 for e in xs if e["mso"]); mq = sum(1 for e in xs if e["media_query"]); tbl = sum(1 for e in xs if e["table_layout"])
    toks = sum(e["out_tokens"] for e in xs) / len(xs) if xs else float("nan")
    words = sum(e["words"] for e in xs) / len(xs) if xs else float("nan")
    return {"n": len(xs), "outlook_layout_or_content": risk, "linter_flags": flags, "mso": mso, "media_query": mq, "table_layout": tbl,
            "mean_out_tokens": round(toks), "mean_words": round(words, 1)}


for slug in SLUGS:
    print(f"\n=== {slug} ===")
    for label, emails in (("original (29 Oct)", orig), ("re-run (8 Nov)", rerun)):
        h, m = table(emails, slug, "html"), table(emails, slug, "mjml")
        ratio = h["mean_out_tokens"] / m["mean_out_tokens"] if m["mean_out_tokens"] else float("nan")
        print(f"{label:18s} HTML n={h['n']}: Outlook layout/content risk {h['outlook_layout_or_content']}, flags {h['linter_flags']}, MSO {h['mso']}, media query {h['media_query']}, table {h['table_layout']}, tokens {h['mean_out_tokens']}, words {h['mean_words']}")
        print(f"{'':18s} MJML n={m['n']}: Outlook risk {m['outlook_layout_or_content']}, tokens {m['mean_out_tokens']}, words {m['mean_words']}; HTML/MJML token ratio {ratio:.2f}")
    # per-brief agreement of the risk class between runs (HTML arm)
    o = {e["brief"]: bool(e["clients"]["Outlook Windows"]["layout"] or e["clients"]["Outlook Windows"]["content"] or e["pipeline_flags"]) for e in orig if e["ok"] and e["slug"] == slug and e["format"] == "html"}
    r = {e["brief"]: bool(e["clients"]["Outlook Windows"]["layout"] or e["clients"]["Outlook Windows"]["content"] or e["pipeline_flags"]) for e in rerun if e["ok"] and e["slug"] == slug and e["format"] == "html"}
    common = sorted(set(o) & set(r)); same = sum(1 for b in common if o[b] == r[b])
    print(f"risky class (HTML arm) agrees between runs on {same} of {len(common)} briefs; original risky {sum(o[b] for b in common)}, re-run risky {sum(r[b] for b in common)}")
