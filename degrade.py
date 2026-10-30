#!/usr/bin/env python3
"""Degraded-render proxy for Outlook for Windows: strip, from each risky HTML email, what Outlook drops.

For the 52 "risky" pairs (HTML email with an Outlook Windows layout or content feature unsupported per
Can I Email, or a pipeline flag — the definition in pooled.py), writes
<run>/<brief>/raw-html__<slug>/degraded/email.degraded.html plus removed.json (every removed declaration,
selector and element), and a jobs file for render-degraded.mjs. The MJML arm is not touched.

Removed, in <style> blocks (also inside @media) and in style attributes, when the property is not a
vendor-prefixed duplicate of nothing (vendor prefixes are stripped before matching):
  display: flex | inline-flex | grid | inline-grid; flex, flex-*, align-*, justify-*, order, gap, row-gap,
  column-gap, grid, grid-*, place-*  (css-display-flex / css-display-grid / css-gap / css-align-items / ...);
  position (except static) with top / right / bottom / left / inset* and z-index  (css-position, css-left-right-top-bottom, css-z-index);
  transform, transform-origin, transform-style  (css-transform);
  float (except none), column-count / columns, aspect-ratio, object-fit  (css-float, css-column-count, ...);
  any background* declaration whose value holds a gradient()  (css-linear-gradient / css-radial-gradient / css-conic-gradient);
  border-radius and border-*-radius, box-shadow  (css-border-radius, css-box-shadow: cosmetic, but Outlook drops them).
Removed as whole selectors: anything with ::before / ::after (:before / :after); a rule left with no selector goes.
Removed as elements: inline <svg>…</svg>, <form>…</form> with its contents (Outlook renders neither).
Everything else, including max-width / margin / padding (partial support in Outlook), @media blocks, MSO
conditional comments (left as the browser sees them: inactive), web fonts and images, is kept.

usage: python3 -I degrade.py results-S.json results-F.json  → prints the per-email log, writes degraded-jobs.json
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = re.compile(r"^-(webkit|moz|ms|o)-")
PSEUDO_EL = re.compile(r"::?(before|after)\b", re.I)

FLEX_GRID_PROPS = {"flex", "flex-grow", "flex-shrink", "flex-basis", "flex-direction", "flex-wrap", "flex-flow",
                   "align-items", "align-self", "align-content", "justify-content", "justify-items", "justify-self",
                   "order", "gap", "row-gap", "column-gap", "grid", "place-items", "place-content", "place-self"}
POSITION_PROPS = {"top", "right", "bottom", "left", "inset", "inset-inline", "inset-block", "inset-inline-start",
                  "inset-inline-end", "inset-block-start", "inset-block-end", "z-index"}
OTHER_LAYOUT = {"transform", "transform-origin", "transform-style", "column-count", "columns", "aspect-ratio", "object-fit"}
COSMETIC = {"box-shadow"}


def classify(prop, value):
    """Return the reason a declaration is removed, or None to keep it."""
    p = VENDOR.sub("", prop.strip().lower())
    v = value.strip().lower().replace("!important", "").strip()
    if p == "display":
        first = v.split()[0] if v else ""
        if first in ("flex", "inline-flex", "grid", "inline-grid"): return "display:" + first
        return None
    if p in FLEX_GRID_PROPS or p.startswith("grid-"): return "flex/grid property"
    if p == "position":
        return None if v == "static" else "position"
    if p in POSITION_PROPS: return "offset/z-index"
    if p in OTHER_LAYOUT: return p.split("-")[0] if p.startswith("transform") else p
    if p == "float":
        return None if v == "none" else "float"
    if p.startswith("background") and "gradient(" in v: return "gradient"
    if p == "border-radius" or (p.startswith("border-") and p.endswith("-radius")): return "border-radius"
    if p in COSMETIC: return p
    return None


def split_decls(text):
    """Split a declaration list on ';' outside parentheses and quotes."""
    out, depth, quote, cur = [], 0, None, []
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote: quote = None
            continue
        if ch in "\"'": quote = ch; cur.append(ch); continue
        if ch == "(": depth += 1
        elif ch == ")": depth = max(0, depth - 1)
        if ch == ";" and depth == 0:
            out.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip(): out.append("".join(cur))
    return out


def filter_decls(text, where, log):
    kept = []
    for d in split_decls(text):
        if ":" not in d or not d.strip():
            if d.strip(): kept.append(d)
            continue
        prop, value = d.split(":", 1)
        why = classify(prop, value)
        if why:
            log.append({"where": where, "prop": prop.strip(), "value": value.strip()[:120], "why": why})
        else:
            kept.append(d)
    return ";".join(k.strip() for k in kept if k.strip())


def rewrite_css(css, log, ctx="style"):
    """Walk rule blocks; recurse into nested at-rules; filter declarations; drop ::before/::after selectors."""
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            out.append(css[i:]); break
        head = css[i:j]
        # match the closing brace of this block
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{": depth += 1
            elif css[k] == "}": depth -= 1
            k += 1
        body = css[j + 1:k - 1]
        comments = "".join(re.findall(r"/\*.*?\*/", head, flags=re.S))   # comments before the selector are kept, not matched
        sel = re.sub(r"/\*.*?\*/", "", head, flags=re.S).strip()
        if sel.startswith("@") and "{" in body:          # @media, @supports, @keyframes: recurse
            out.append(head + "{" + rewrite_css(body, log, ctx) + "}")
        elif sel.startswith("@"):                          # @font-face, @page: keep as is
            out.append(head + "{" + body + "}")
        else:
            parts = [s.strip() for s in sel.split(",")]
            keep = [s for s in parts if not PSEUDO_EL.search(s)]
            dropped = [s for s in parts if PSEUDO_EL.search(s)]
            for s in dropped:
                log.append({"where": ctx, "selector": s, "why": "pseudo-element rule", "decls": body.strip()[:160]})
            lead = head[:len(head) - len(head.lstrip())]
            if keep:
                out.append(lead + comments + ", ".join(keep) + " {" + filter_decls(body, f"{ctx} {', '.join(keep)}", log) + "}")
            elif comments:
                out.append(lead + comments)
        i = k
    return "".join(out)


def degrade(html):
    log, removed_elements = [], []
    # elements Outlook does not render
    for tag in ("svg", "form"):
        pat = re.compile(rf"<{tag}\b[^>]*>.*?</{tag}\s*>", re.S | re.I)
        for m in pat.finditer(html):
            removed_elements.append({"tag": tag, "html": m.group(0)[:200]})
        html = pat.sub("", html)
    # <style> blocks
    def style_block(m):
        return m.group(1) + rewrite_css(m.group(2), log, "style") + m.group(3)
    html = re.sub(r"(<style\b[^>]*>)(.*?)(</style\s*>)", style_block, html, flags=re.S | re.I)
    # style attributes
    def style_attr(m):
        q = m.group(2)
        new = filter_decls(m.group(3), "inline", log)
        return (m.group(1) + q + new + q) if new else ""
    html = re.sub(r"(\sstyle\s*=\s*)([\"'])(.*?)\2", style_attr, html, flags=re.S | re.I)
    return html, log, removed_elements


def risky_pairs(result_files):
    pairs = []
    for f in result_files:
        d = json.load(open(f)); s = d["summary"]["set"]; run = d["summary"]["run"]
        ok = {(e["brief"], e["combo"]): e for e in d["emails"] if e["ok"]}
        jmap = {(p["brief"], p["slug"]): p for p in d["pairs"]}
        for (b, c), e in sorted(ok.items()):
            if not c.startswith("raw-html__") or (b, "raw__" + e["slug"]) not in ok: continue
            ow = e["clients"]["Outlook Windows"]
            if ow["layout"] or ow["content"] or e["pipeline_flags"]:
                pairs.append({"set": s, "run": run, "brief": b, "slug": e["slug"], "layout": ow["layout"], "content": ow["content"],
                              "flags": e["pipeline_flags"], "mso": e["mso"], "judge": jmap[(b, e["slug"])]})
    return pairs


def main():
    pairs = risky_pairs(sys.argv[1:])
    print(f"{len(pairs)} risky pairs")
    jobs, summary = [], []
    for p in pairs:
        src = os.path.join(p["run"], p["brief"], f"raw-html__{p['slug']}", "email.html")
        out_dir = os.path.join(os.path.dirname(src), "degraded")
        os.makedirs(out_dir, exist_ok=True)
        html = open(src, encoding="utf-8").read()
        new, log, elements = degrade(html)
        open(os.path.join(out_dir, "email.degraded.html"), "w", encoding="utf-8").write(new)
        counts = collections.Counter(x["why"] for x in log)
        for e in elements: counts[f"<{e['tag']}> element"] += 1
        json.dump({"set": p["set"], "brief": p["brief"], "slug": p["slug"], "source": src, "bytes_before": len(html.encode()), "bytes_after": len(new.encode()),
                   "risk": {"layout": p["layout"], "content": p["content"], "flags": p["flags"], "mso": p["mso"]},
                   "counts": dict(counts), "removed": log, "removed_elements": elements}, open(os.path.join(out_dir, "removed.json"), "w"), indent=1)
        jobs.append({"html": os.path.join(out_dir, "email.degraded.html"), "outDir": out_dir})
        summary.append({"set": p["set"], "brief": p["brief"], "slug": p["slug"], "counts": dict(counts), "risk": {"layout": p["layout"], "content": p["content"], "flags": p["flags"], "mso": p["mso"]}})
        print(f"{p['set']} {p['brief']:18s} {p['slug']:22s} removed {sum(counts.values()):3d}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    json.dump(jobs, open(os.path.join(HERE, "degraded-jobs.json"), "w"), indent=1)
    json.dump(summary, open(os.path.join(HERE, "degraded-removals.json"), "w"), indent=1)
    total = collections.Counter()
    for s in summary: total.update(s["counts"])
    print("\ntotal removed:", dict(total.most_common()))
    print("emails with no layout/content removal (only border-radius/box-shadow or nothing):",
          sum(1 for s in summary if not any(k not in ("border-radius", "box-shadow") for k in s["counts"])))


if __name__ == "__main__":
    main()
