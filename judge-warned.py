"""E1 of preregistration-2026-11-08.md: re-judge the 52 risky pairs from the ORIGINAL browser screenshots with an
instruction that tells the judge about the target client. Two variants:
  generic  - the recipients read mail in classic Outlook for Windows; a fixed list of what it does not render.
  specific - the generic text plus, per email, the Outlook-dropped features the audit found in it (or "none found").
Writes <run>/judge-warned-<variant>/<judge>/<brief>/<slug>.json.

usage: python3 -I judge-warned.py <gpt|opus> <generic|specific> [concurrency=4] [budget usd=6]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judgelib as J

GENERIC = """Important context: the recipients of this email read their mail in classic Outlook for Windows, which renders HTML with the engine of Microsoft Word. That client does not render flexbox or grid layout, CSS positioning, transforms, floats, gradient backgrounds, ::before and ::after content, inline SVG, forms, rounded corners or box shadows, and it ignores max-width on most elements; anything built with those features is dropped or breaks there. The screenshots below were taken in a browser, which renders all of them. Score each email for how it will look to those recipients in Outlook, not for how the browser screenshot looks."""

NAMES = {"css-display-flex": "display: flex", "css-display-grid": "display: grid", "css-position": "CSS positioning", "css-left-right-top-bottom": "top/left offsets",
         "css-z-index": "z-index", "css-transform": "CSS transforms", "css-float": "floats", "css-gap": "flex/grid gap", "css-align-items": "align-items",
         "css-justify-content": "justify-content", "css-flex-wrap": "flex-wrap", "css-flex-direction": "flex-direction", "css-linear-gradient": "CSS gradient backgrounds",
         "css-radial-gradient": "radial gradient backgrounds", "css-conic-gradient": "conic gradient backgrounds", "css-pseudo-element-before": "::before generated content",
         "css-pseudo-element-after": "::after generated content", "html-svg": "inline SVG", "html-form": "a form", "css-column-count": "CSS columns",
         "css-aspect-ratio": "aspect-ratio", "css-object-fit": "object-fit", "css-background-image-gradient": "CSS gradient backgrounds"}
FLAGS = {"no table layout": "no table-based layout (the layout depends on div/CSS positioning)"}


def readable(x):
    return NAMES.get(x) or FLAGS.get(x) or x.replace("css-", "").replace("html-", "").replace("-", " ")


def make_extra(variant):
    feats = J.email_features()

    def extra(p, a, b):
        if variant == "generic": return GENERIC
        lines = []
        for label, fmt in (("A", a), ("B", b)):
            combo = ("raw-html__" if fmt == "html" else "raw__") + p["slug"]
            f = feats[(p["set"], p["brief"], combo)]
            items = sorted({readable(x) for x in f["layout"] + f["content"] + list(f["flags"])})
            lines.append(f"- Email {label}: " + (", ".join(items) if items else "none found") + ".")
        return GENERIC + "\n\nAn automated audit of each email's HTML against the Can I Email support database found these Outlook-dropped features:\n" + "\n".join(lines)
    return extra


def main():
    judge, variant = sys.argv[1], sys.argv[2]
    conc = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    budget = float(sys.argv[4]) if len(sys.argv) > 4 else 6.0
    assert variant in ("generic", "specific")
    J.run(judge, J.risky_pairs(), f"judge-warned-{variant}", conc, budget, extra_fn=make_extra(variant))


if __name__ == "__main__":
    main()
