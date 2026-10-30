#!/usr/bin/env python3
"""Client-support audit of generated email HTML against the Can I Email database.

For every email.html under the run folders, extracts the CSS and HTML features it uses, maps them to
Can I Email feature slugs, and looks up the latest support value for a fixed list of mail clients.
Output: features.json (per email: features used, per-client unsupported/partial lists) and a summary
printed to stdout. No model is involved.

usage: audit.py <caniemail data.json> <run folder> [<run folder> ...]
"""
import json, re, sys, os, glob, collections
from html.parser import HTMLParser

CLIENTS = [  # (family, platform, label)
    ("gmail", "desktop-webmail", "Gmail web"),
    ("gmail", "ios", "Gmail iOS"),
    ("gmail", "android", "Gmail Android"),
    ("outlook", "windows", "Outlook Windows"),
    ("outlook", "outlook-com", "Outlook.com"),
    ("outlook", "macos", "Outlook macOS"),
    ("outlook", "ios", "Outlook iOS"),
    ("apple-mail", "macos", "Apple Mail macOS"),
    ("apple-mail", "ios", "Apple Mail iOS"),
    ("yahoo", "desktop-webmail", "Yahoo web"),
    ("samsung-email", "android", "Samsung Email"),
]

# features whose lack of support changes the layout rather than a cosmetic detail
LAYOUT = {
    "css-display-flex", "css-display-grid", "css-position", "css-float", "css-max-width", "css-min-width",
    "css-gap", "css-aspect-ratio", "css-object-fit", "css-transform", "css-inset", "css-left-right-top-bottom",
    "css-flex-direction", "css-flex-wrap", "css-justify-content", "css-align-items", "css-grid-template",
    "css-box-sizing", "css-overflow", "css-width", "css-height", "css-margin", "css-padding", "css-at-media",
    "css-column-count", "css-display", "css-display-none", "css-visibility", "css-z-index",
}

VENDOR = re.compile(r"^-(webkit|moz|ms|o)-")


def load_db(path):
    d = json.load(open(path))
    feats = {f["slug"]: f for f in d["data"]}
    return feats


def latest(stats, family, platform):
    try:
        versions = stats[family][platform]
    except KeyError:
        return None
    if not versions:
        return None
    # caniemail lists versions chronologically; the last key is the newest
    val = list(versions.values())[-1]
    return (val or "u").strip()[:1]


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.styles = []          # <style> contents
        self.inline = []          # style attribute values
        self.tags = collections.Counter()
        self.attrs = collections.Counter()
        self.hrefs = []
        self.srcs = []
        self.inputs = collections.Counter()
        self.buttons = collections.Counter()
        self.metas = []
        self.links = []
        self._in_style = False
        self.comments = 0
        self.cond_comments = 0

    def handle_starttag(self, tag, attrs):
        self.tags[tag] += 1
        a = dict(attrs)
        for k in a:
            self.attrs[k] += 1
            if k.startswith("aria-"):
                self.attrs[k] += 0
        if "style" in a and a["style"]:
            self.inline.append(a["style"])
        if tag == "style":
            self._in_style = True
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        if tag in ("img", "source", "video", "audio") and a.get("src"):
            self.srcs.append(a["src"])
        if tag == "input":
            self.inputs[a.get("type", "text")] += 1
        if tag == "button":
            self.buttons[a.get("type", "submit")] += 1
        if tag == "meta":
            self.metas.append(a)
        if tag == "link":
            self.links.append(a)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            self.styles.append(data)

    def handle_comment(self, data):
        self.comments += 1
        if data.strip().startswith("[if"):
            self.cond_comments += 1

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype"):
            self.tags["!doctype"] += 1


DECL = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;{}]+)")


def css_features(css_text, feats, from_style_block):
    used = set()
    t = css_text
    # at-rules
    if re.search(r"@media", t):
        used.add("css-at-media")
        if "prefers-color-scheme" in t: used.add("css-at-media-prefers-color-scheme")
        if "prefers-reduced-motion" in t: used.add("css-at-media-prefers-reduced-motion")
        if "orientation" in t: used.add("css-at-media-orientation")
        if "hover" in t and "(hover" in t: used.add("css-at-media-hover")
        if "device-pixel-ratio" in t or "resolution" in t: used.add("css-at-media-device-pixel-ratio")
    if "@font-face" in t: used.add("css-at-font-face")
    if "@import" in t: used.add("css-at-import")
    if "@supports" in t: used.add("css-at-supports")
    if "@keyframes" in t: used.add("css-at-keyframes")
    # selectors (only in style blocks)
    if from_style_block:
        body = re.sub(r"@media[^{]*\{", "", t)
        for sel in re.findall(r"([^{}]+)\{", body):
            s = sel.strip()
            if not s or s.startswith("@"): continue
            if ":hover" in s: used.add("css-pseudo-class-hover")
            if ":active" in s: used.add("css-pseudo-class-active")
            if ":focus" in s: used.add("css-pseudo-class-focus")
            if ":visited" in s: used.add("css-pseudo-class-visited")
            if ":link" in s: used.add("css-pseudo-class-link")
            if ":first-child" in s: used.add("css-pseudo-class-first-child")
            if ":last-child" in s: used.add("css-pseudo-class-last-child")
            if ":nth-child" in s: used.add("css-pseudo-class-nth-child")
            if ":not(" in s: used.add("css-pseudo-class-not")
            if "::before" in s or ":before" in s: used.add("css-pseudo-element-before")
            if "::after" in s or ":after" in s: used.add("css-pseudo-element-after")
            if "." in s: used.add("css-selector-class")
            if "#" in s: used.add("css-selector-id")
            if "[" in s: used.add("css-selector-attribute")
            if "*" in s: used.add("css-selector-universal")
            if ">" in s: used.add("css-selector-child")
            if "+" in s: used.add("css-selector-adjacent-sibling")
            if "~" in s: used.add("css-selector-general-sibling")
            if "," in s: used.add("css-selector-grouping")
            if re.search(r"[a-z\]]\s+[a-z.#\[]", s): used.add("css-selector-descendant")
            if re.match(r"^[a-zA-Z][a-zA-Z0-9]*(\s|$|,|:)", s): used.add("css-selector-type")
    # declarations
    for prop, val in DECL.findall(re.sub(r"/\*.*?\*/", "", t, flags=re.S)):
        p = prop.strip().lower(); v = val.strip().lower()
        if p.startswith("mso-") or p.startswith("-ms-text-size-adjust") or p.startswith("-webkit-text-size-adjust"):
            continue
        p = VENDOR.sub("", p)
        # default values that use no feature: `float: none` (mj-social emits it), `position: static`
        if (p == "float" and val.strip().lower().replace("!important", "").strip() == "none") or (p == "position" and val.strip().lower().replace("!important", "").strip() == "static"):
            continue
        if "!important" in v: used.add("css-important")
        vclean = v.replace("!important", "").strip()
        # property-level mapping
        cand = []
        if p == "display":
            first = vclean.split()[0] if vclean else ""
            if first in ("flex", "inline-flex"): cand.append("css-display-flex")
            elif first == "grid": cand.append("css-display-grid")
            elif first == "none": cand.append("css-display-none")
            else: cand.append("css-display")
        elif p in ("left", "right", "top", "bottom"): cand.append("css-left-right-top-bottom")
        elif p.startswith("grid-template"): cand.append("css-grid-template")
        elif p.startswith("border-") and p.endswith("-radius"): cand.append("css-border-radius")
        elif p in ("border", "border-top", "border-right", "border-bottom", "border-left", "border-width",
                   "border-style", "border-color", "border-top-width", "border-bottom-width", "border-left-width",
                   "border-right-width", "border-top-color", "border-bottom-color", "border-top-style",
                   "border-bottom-style", "border-left-color", "border-right-color", "border-left-style",
                   "border-right-style"):
            cand.append("css-border")
        elif p.startswith("margin-inline") or p.startswith("margin-block"): cand.append("css-margin-inline-start-end")
        elif p.startswith("padding-inline") or p.startswith("padding-block"): cand.append("css-padding-inline-start-end")
        elif p.startswith("margin"): cand.append("css-margin")
        elif p.startswith("padding"): cand.append("css-padding")
        elif p.startswith("overflow"): cand.append("css-overflow-wrap" if p == "overflow-wrap" else "css-overflow")
        elif p.startswith("list-style"): cand.append("css-" + p if "css-" + p in feats else "css-list-style")
        elif p.startswith("background"): cand.append("css-" + p if "css-" + p in feats else "css-background")
        elif p.startswith("text-decoration"): cand.append("css-" + p if "css-" + p in feats else "css-text-decoration")
        elif p.startswith("font-") or p == "font":
            cand.append("css-" + p if "css-" + p in feats else "css-font")
        elif p in ("flex", "flex-grow", "flex-shrink", "flex-basis"): cand.append("css-display-flex")
        elif p in ("row-gap", "column-gap"): cand.append("css-gap")
        elif p == "inline-size": cand.append("css-inline-size")
        elif p == "block-size": cand.append("css-block-inline-size")
        elif p in ("word-wrap",): cand.append("css-word-wrap")
        elif p == "text-size-adjust": pass
        else:
            if "css-" + p in feats: cand.append("css-" + p)
        used.update(c for c in cand if c in feats)
        # value-level features
        if "linear-gradient(" in vclean: used.add("css-linear-gradient")
        if "radial-gradient(" in vclean: used.add("css-radial-gradient")
        if "conic-gradient(" in vclean: used.add("css-conic-gradient")
        if re.search(r"\brgba\(", vclean): used.add("css-rgba")
        elif re.search(r"\brgb\(", vclean): used.add("css-rgb")
        if re.search(r"\b(oklch|oklab|lab|lch|color)\(", vclean): used.add("css-modern-color")
        if "var(" in vclean: used.add("css-variables")
        if "calc(" in vclean: used.add("css-unit-calc")
        if "clamp(" in vclean: used.add("css-function-clamp")
        if re.search(r"\bmin\(", vclean): used.add("css-function-min")
        if re.search(r"\bmax\(", vclean): used.add("css-function-max")
        if p == "font-family" and "system-ui" in vclean: used.add("css-sytem-ui")
        for num, unit in re.findall(r"(-?\d*\.?\d+)(px|%|em|rem|pt|vw|vh|vmin|vmax|ch|ex|cm|mm|in|pc)\b", vclean):
            slug = "css-unit-" + ("percent" if unit == "%" else unit)
            if slug in feats: used.add(slug)
        if vclean in ("initial",): used.add("css-unit-initial")
    return used


def html_features(c, feats):
    used = set()
    tagmap = {"table": "html-table", "div": "html-div", "p": "html-p", "span": "html-span", "strong": "html-strong",
              "b": "html-strong", "hr": "html-hr", "small": "html-small", "img": "html-img", "picture": "html-picture",
              "svg": "html-svg", "video": "html-video", "audio": "html-audio", "form": "html-form", "select": "html-select",
              "textarea": "html-textarea", "blockquote": "html-blockquote", "code": "html-code", "pre": "html-pre",
              "address": "html-address", "abbr": "html-abbr", "del": "html-del", "strike": "html-strike", "s": "html-strike",
              "wbr": "html-wbr", "dialog": "html-dialog", "meter": "html-meter", "progress": "html-progress",
              "object": "html-object", "marquee": "html-marquee", "base": "html-base", "style": "html-style",
              "link": "html-link", "body": "html-body", "!doctype": "html-doctype"}
    for t, n in c.tags.items():
        if n and t in tagmap: used.add(tagmap[t])
        if t in ("h1", "h2", "h3", "h4", "h5", "h6"): used.add("html-h1-h6")
        if t in ("ul", "ol", "li"): used.add("html-lists")
        if t in ("header", "footer", "nav", "section", "article", "main", "aside", "figure", "figcaption", "time"):
            used.add("html-semantics")
    for it, n in c.inputs.items():
        slug = "html-input-" + it
        if slug in feats: used.add(slug)
    for bt, n in c.buttons.items():
        slug = "html-button-" + bt
        if slug in feats: used.add(slug)
    for a in c.attrs:
        if a in ("align", "valign", "cellpadding", "cellspacing", "background", "width", "height", "role", "lang",
                 "dir", "hidden", "target", "srcset", "loading"):
            used.add("html-" + a + ("-attribute" if a == "loading" else ""))
        if a.startswith("aria-") and "html-" + a in feats: used.add("html-" + a)
    for h in c.hrefs:
        if h.lower().startswith("mailto:"): used.add("html-mailto-links")
        if h.startswith("#"): used.add("html-anchor-links")
    for s in c.srcs:
        sl = s.lower().split("?")[0]
        if sl.startswith("data:"): used.add("image-base64")
        for ext, slug in (("png", "image-png"), ("jpg", "image-jpg"), ("jpeg", "image-jpg"), ("gif", "image-gif"),
                          ("svg", "image-svg"), ("webp", "image-webp"), ("avif", "image-avif")):
            if sl.endswith("." + ext): used.add(slug)
    for m in c.metas:
        if (m.get("name") or "").lower() == "color-scheme": used.add("html-meta-color-scheme")
    if c.comments: used.add("html-comments")
    return {u for u in used if u in feats}


def audit_file(path, feats):
    html = open(path, encoding="utf-8", errors="replace").read()
    c = Collector(); c.feed(html)
    used = set()
    for s in c.styles: used |= css_features(s, feats, True)
    for s in c.inline: used |= css_features(s, feats, False)
    used |= html_features(c, feats)
    per_client = {}
    for fam, plat, label in CLIENTS:
        unsupported, partial = [], []
        for slug in sorted(used):
            v = latest(feats[slug]["stats"], fam, plat)
            if v == "n": unsupported.append(slug)
            elif v == "a": partial.append(slug)
        per_client[label] = {"n": unsupported, "a": partial,
                             "n_layout": [s for s in unsupported if s in LAYOUT]}
    return {"features": sorted(used), "clients": per_client, "bytes": len(html.encode("utf-8")),
            "cond_comments": c.cond_comments, "style_blocks": len(c.styles), "inline_styles": len(c.inline)}


def main():
    db, *roots = sys.argv[1:]
    feats = load_db(db)
    out = {}
    for root in roots:
        for path in sorted(glob.glob(os.path.join(root, "*", "*", "email.html"))):
            brief = path.split(os.sep)[-3]; combo = path.split(os.sep)[-2]
            out[f"{brief}/{combo}"] = audit_file(path, feats)
    here = os.path.dirname(os.path.abspath(__file__))
    json.dump(out, open(os.path.join(here, "features.json"), "w"), indent=1)
    # summary by generator kind
    groups = collections.defaultdict(list)
    for key, r in out.items():
        combo = key.split("/")[1]
        kind = combo.split("__")[0]
        groups[kind].append(r)
    labels = [c[2] for c in CLIENTS]
    print(f"{'kind':22s} n   " + " ".join(f"{l[:12]:>12s}" for l in labels))
    for kind, rs in sorted(groups.items()):
        row = []
        for l in labels:
            mean_n = sum(len(r["clients"][l]["n"]) for r in rs) / len(rs)
            share = sum(1 for r in rs if r["clients"][l]["n_layout"]) / len(rs)
            row.append(f"{mean_n:5.1f}/{share*100:3.0f}%")
        print(f"{kind:22s} {len(rs):3d} " + " ".join(f"{x:>12s}" for x in row))
    print("\ncells: mean count of used features the client does not support / share of emails with a layout feature unsupported")
    # most common unsupported features in Outlook Windows and Gmail web by kind
    for l in ("Outlook Windows", "Gmail web", "Gmail iOS"):
        print(f"\nmost common unsupported in {l}:")
        for kind, rs in sorted(groups.items()):
            cnt = collections.Counter(s for r in rs for s in r["clients"][l]["n"])
            print(f"  {kind:22s} " + ", ".join(f"{s}:{n}" for s, n in cnt.most_common(8)))


if __name__ == "__main__":
    main()
