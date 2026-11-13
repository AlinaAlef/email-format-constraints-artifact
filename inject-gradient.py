"""E3 of preregistration-2026-11-08.md: inject ONE Outlook-dropped feature, a CSS gradient background, into the
free-HTML email of each pair in the 52-pair safe sample. The first block in document order that carries a
non-white background colour (td, th, table, div, section, tr, header; not body/html) gets
`background-image: linear-gradient(135deg, C 0%, C2 100%)` where C is its colour and C2 is C with its HSL lightness
multiplied by 0.78 (22% darker, relative). Near-white colours (HSL lightness > 0.9) and transparent are skipped
as page backgrounds; an element that already has a background-image is skipped. Nothing else changes.

Writes <run>/<brief>/raw-html__<slug>/injected/email.injected.html and injected.json, plus injected-jobs.json for
render-degraded.mjs (which renders screenshot.png / screenshot-phone.png into the same folder). After rendering,
`--audit` re-audits original and injected emails with the Can I Email database and writes injected-audit.json.

usage: python3 -I inject-gradient.py            (inject + write jobs)
       python3 -I inject-gradient.py --audit    (after node render-degraded.mjs injected-jobs.json)
"""
import colorsys, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import judgelib as J
import audit, analyze_formats

NAMED = {"black": "#000000", "navy": "#000080", "darkblue": "#00008b", "blue": "#0000ff", "teal": "#008080", "green": "#008000", "darkgreen": "#006400",
         "maroon": "#800000", "red": "#ff0000", "purple": "#800080", "indigo": "#4b0082", "orange": "#ffa500", "gold": "#ffd700", "gray": "#808080",
         "grey": "#808080", "darkgray": "#a9a9a9", "darkgrey": "#a9a9a9", "dimgray": "#696969", "silver": "#c0c0c0", "crimson": "#dc143c",
         "tomato": "#ff6347", "coral": "#ff7f50", "salmon": "#fa8072", "olive": "#808000", "brown": "#a52a2a", "chocolate": "#d2691e",
         "firebrick": "#b22222", "forestgreen": "#228b22", "seagreen": "#2e8b57", "steelblue": "#4682b4", "royalblue": "#4169e1",
         "midnightblue": "#191970", "slategray": "#708090", "slategrey": "#708090", "darkslategray": "#2f4f4f", "white": "#ffffff"}
TAGS = ("td", "th", "table", "div", "section", "tr", "header")
TAG_RE = re.compile(r"<(" + "|".join(TAGS) + r")\b([^>]*)>", re.I)
STYLE_RE = re.compile(r'style\s*=\s*("([^"]*)"|\'([^\']*)\')', re.I)
BGCOLOR_RE = re.compile(r'bgcolor\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)


def parse_colour(s):
    s = s.strip().lower().rstrip(";").strip()
    if s in ("transparent", "none", "inherit", "initial", ""): return None
    if s in NAMED: s = NAMED[s]
    m = re.fullmatch(r"#([0-9a-f]{3})", s)
    if m: s = "#" + "".join(ch * 2 for ch in m.group(1))
    m = re.fullmatch(r"#([0-9a-f]{6})([0-9a-f]{2})?", s)
    if m:
        h = m.group(1); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)", s)
    if m:
        if m.group(4) is not None and float(m.group(4)) < 0.99: return None
        return tuple(min(255, int(m.group(i))) for i in (1, 2, 3))
    return None


def block_colour(attrs):
    """Colour of a candidate block from its style attribute or bgcolor, or None."""
    m = STYLE_RE.search(attrs)
    style = (m.group(2) or m.group(3) or "") if m else ""
    if re.search(r"background-image\s*:", style, re.I) or re.search(r"background\s*:[^;]*url\(", style, re.I) or "gradient(" in style.lower(): return "has-image"
    for prop in ("background-color", "background"):
        mm = re.search(r"(?:^|;)\s*" + prop + r"\s*:\s*([^;]+)", style, re.I)
        if mm:
            val = mm.group(1).strip()
            c = parse_colour(val.split()[0]) if prop == "background" else parse_colour(val)
            if c: return c
    mb = BGCOLOR_RE.search(attrs)
    if mb:
        c = parse_colour(mb.group(2) or mb.group(3) or mb.group(4) or "")
        if c: return c
    return None


def hexc(rgb): return "#%02x%02x%02x" % rgb


def darker(rgb, factor=0.78):
    h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
    r, g, b = colorsys.hls_to_rgb(h, max(0.0, l * factor), s)
    return tuple(int(round(v * 255)) for v in (r, g, b))


def lightness(rgb): return colorsys.rgb_to_hls(*(v / 255 for v in rgb))[1]


def inject(html):
    """Returns (new_html, info) or (None, reason)."""
    for i, m in enumerate(TAG_RE.finditer(html)):
        tag, attrs = m.group(1).lower(), m.group(2)
        c = block_colour(attrs)
        if c is None or c == "has-image": continue
        if lightness(c) > 0.9: continue
        c2 = darker(c)
        decl = f"background-image: linear-gradient(135deg, {hexc(c)} 0%, {hexc(c2)} 100%);"
        sm = STYLE_RE.search(attrs)
        if sm:
            old = sm.group(2) if sm.group(2) is not None else sm.group(3)
            q = '"' if sm.group(2) is not None else "'"
            new_style = old.rstrip().rstrip(";") + ("; " if old.strip() else "") + decl
            new_attrs = attrs[:sm.start()] + f"style={q}{new_style}{q}" + attrs[sm.end():]
        else:
            new_attrs = attrs + f' style="{decl}"'
        new_html = html[:m.start()] + f"<{m.group(1)}{new_attrs}>" + html[m.end():]
        return new_html, {"tag": tag, "tag_index": i, "colour": hexc(c), "colour2": hexc(c2), "lightness": round(lightness(c), 3), "position": m.start()}
    return None, "no block with a non-white background colour"


def main():
    pairs = J.safe_sample()
    if "--audit" in sys.argv:
        feats = audit.load_db("<data-repo>/caniemail/data.json")
        out = {}
        for p in pairs:
            d = J.pair_dirs(p)["html"]; inj = os.path.join(d, "injected", "email.injected.html")
            if not os.path.exists(inj): continue
            a0 = analyze_formats.audit_email(os.path.join(d, "email.html"), feats); a1 = analyze_formats.audit_email(inj, feats)
            key = f"{p['set']}/{p['brief']}/{p['slug']}"
            added = sorted(set(a1["features_outside"]) - set(a0["features_outside"])); removed = sorted(set(a0["features_outside"]) - set(a1["features_outside"]))
            ow0, ow1 = a0["clients"]["Outlook Windows"], a1["clients"]["Outlook Windows"]
            rj = os.path.join(d, "injected", "render.json"); scroll = json.load(open(rj))["phoneScrollWidth"] if os.path.exists(rj) else None
            out[key] = {"features_added": added, "features_removed": removed, "outlook_content_before": ow0["content"], "outlook_content_after": ow1["content"],
                        "outlook_layout_after": ow1["layout"], "words_before": a0["words"], "words_after": a1["words"], "phone_scroll_after": scroll,
                        "rendered": os.path.exists(os.path.join(d, "injected", "screenshot.png"))}
        json.dump(out, open(os.path.join(HERE, "injected-audit.json"), "w"), indent=1)
        ok = sum(1 for v in out.values() if v["features_added"] == ["css-linear-gradient"] and not v["features_removed"] and v["rendered"])
        print(f"audited {len(out)} injected emails; {ok} add exactly css-linear-gradient, remove nothing and are rendered")
        for k, v in out.items():
            if not (v["features_added"] == ["css-linear-gradient"] and not v["features_removed"] and v["rendered"]): print("  check:", k, v["features_added"], v["features_removed"], v["rendered"])
        return
    jobs, log = [], []
    for p in pairs:
        d = J.pair_dirs(p)["html"]; src = os.path.join(d, "email.html")
        html = open(src, encoding="utf-8").read()
        new, info = inject(html)
        key = f"{p['set']}/{p['brief']}/{p['slug']}"
        if new is None: log.append({"pair": key, "injected": False, "reason": info}); print("skip", key, info); continue
        od = os.path.join(d, "injected"); os.makedirs(od, exist_ok=True)
        open(os.path.join(od, "email.injected.html"), "w", encoding="utf-8").write(new)
        json.dump(info, open(os.path.join(od, "injected.json"), "w"), indent=1)
        jobs.append({"html": os.path.join(od, "email.injected.html"), "outDir": od}); log.append({"pair": key, "injected": True, **info})
        print("ok", key, info["tag"], info["colour"], "->", info["colour2"], "L=%.2f" % info["lightness"])
    json.dump(jobs, open(os.path.join(HERE, "injected-jobs.json"), "w"), indent=1)
    json.dump(log, open(os.path.join(HERE, "injected-log.json"), "w"), indent=1)
    print(f"injected {len(jobs)} of {len(pairs)}; jobs -> injected-jobs.json")


if __name__ == "__main__":
    main()
