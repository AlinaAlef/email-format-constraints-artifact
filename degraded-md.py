#!/usr/bin/env python3
"""Render degraded.md (method, removal counts, before/after tables, tests, cost) from results-degraded.json and
degraded-removals.json. usage: python3 -I degraded-md.py"""
import json, os, sys, collections
  # numpy, Pillow
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results-degraded.json")))
REM = json.load(open(os.path.join(HERE, "degraded-removals.json")))
DIMS = ("design", "readability", "briefCoverage", "phone", "overall")
CATS = ["display:flex", "flex/grid property", "position", "offset/z-index", "transform", "float", "gradient", "pseudo-element rule", "<svg> element", "<form> element", "border-radius", "box-shadow"]


def pct(x): return f"{100 * x:.0f} %"
def ci(d): return f"{d['mean']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}]"
def p(x): return "< 0.0001" if x < 0.0001 else f"= {x:.4f}" if x < 0.01 else f"= {x:.3f}"


def verdict_row(label, c): return f"| {label} | {c['html']} | {c['mjml']} | {c['split']} | {pct(c['html'] / c['n'])} | {pct(c['mjml'] / c['n'])} |"


L = []
L.append("# Degraded-render re-judge of the 52 risky pairs\n")
L.append("Question: the two screenshot judges preferred the free-HTML email in 73 % (Opus 5.5) / 67 % (GPT-6.1 Sol) of the 52 "
         "\"risky\" pairs (HTML uses something Outlook for Windows drops) but only 39 % / 38 % of the 258 safe pairs. Almost all "
         "risky HTML emails come from Claude Haiku 4.5 and Sonnet 4.6, so the preference could be for that family's emails rather "
         "than for the features Outlook drops. If the features are what the judges like, removing them should pull the "
         "preference back towards the safe baseline; if the family is what they like, it should not move.\n")
L.append("## Method\n")
L.append(f"- Pairs: the {R['n_risky_pairs']} pairs whose HTML email has an Outlook Windows layout or content feature unsupported per Can I Email "
         "(`clients['Outlook Windows'].layout` or `.content` non-empty in `results-S.json` / `results-F.json`) or a pipeline flag "
         "(`pipeline_flags` non-empty) — the definition in `pooled.py`. Sets: 12 from S, 40 from F. Models: Haiku 4.5 26, Sonnet 4.6 24, "
         "Sonnet 5.5 1 (float), GPT-6 Luna low 1 (float).")
L.append("- Degradation (`degrade.py`): in `<style>` blocks (including inside `@media`) and `style` attributes, remove every declaration "
         "whose Can I Email feature Outlook for Windows does not support in the layout / content classes of `analyze-formats.py`: "
         "`display: flex | grid` and all flex / grid properties (gap, align-*, justify-*, order, grid-*); `position` other than static "
         "with top / right / bottom / left / inset and z-index; `transform`; `float` other than none; column-count, aspect-ratio, object-fit; "
         "any `background*` whose value holds a gradient; plus `border-radius` and `box-shadow`, which Outlook also drops. Selectors with "
         "`::before` / `::after` are removed whole. Inline `<svg>` and `<form>` elements are removed with their contents. Everything else "
         "is kept, in particular `max-width`, `margin`, `padding` (partial support in Outlook), `@media` blocks, web fonts and images. "
         "MSO conditional comments stay as the browser sees them (inactive), so an email with an MSO fallback is shown without it "
         f"({sum(1 for r in REM if r['risk']['mso'])} of the 52 has one). The MJML arm is untouched.")
L.append("- Render (`render-degraded.mjs`): the runner's screenshot procedure reproduced with the same Playwright 1.56.1 / chromium-1194 "
         "(desktop 700 × 900 viewport, phone 375 × 800, `networkidle` + 500 ms, full page, device scale 1). Re-rendering an original "
         "email this way reproduces its stored screenshot pixel for pixel, so the only difference between before and after is the degradation. "
         "Output: `<run>/<brief>/raw-html__<slug>/degraded/{email.degraded.html, screenshot.png, screenshot-phone.png, render.json, removed.json}`.")
L.append("- Judges (`judge-degraded.py`): same instruction, JSON schema, tiling (1,500 px tiles, at most 6 per screenshot) and both orders as "
         "the runner's Opus judge and `judge-gpt.py`; the degraded HTML render against the MJML arm's original render. GPT-6.1 Sol via "
         "OpenRouter (`openai/gpt-6.1-sol`, reasoning effort medium) exactly as before. Opus 5.5 via OpenRouter (`anthropic/claude-opus-5.5`, "
         "reasoning effort medium, strict JSON schema) where the original verdicts came from the Anthropic API directly with `effort: medium` — "
         "same model, different route; the GPT route is unchanged. Written to `<run>/judge-degraded/<judge>/<brief>/<slug>.json`.")
L.append("- \"Before\" is the original verdict on the same pair from `results-S.json` / `results-F.json` (`judge/`, `judge-gpt/`). A pair's "
         "verdict is *html* or *mjml* when both orders agree, *split* otherwise. Tests: exact McNemar (binomial on the discordant pairs) on "
         "\"HTML wins the pair\" before vs after; sign test on the number of orders (0–2) preferring HTML; Wilcoxon signed-rank on the per-pair "
         "overall-score difference; Fisher's exact test of the HTML-win share against the safe-pair baseline; paired bootstrap (4,000 resamples) "
         "for score changes. `analyze-degraded.py` → `results-degraded.json`.\n")

L.append("## What was removed\n")
tot = collections.Counter()
for r in REM: tot.update(r["counts"])
L.append("Declarations / rules / elements removed over the 52 HTML emails (an email with only border-radius / box-shadow removed is "
         f"\"cosmetic only\"; {R['n_structural_removal']} of 52 lost at least one layout or content feature):\n")
L.append("| what | removed |\n|---|---|")
for c in CATS:
    if tot.get(c): L.append(f"| {c} | {tot[c]} |")
L.append(f"| **total** | **{sum(tot.values())}** |\n")
L.append("Per email (set, brief, model: removals; risk features from the audit):\n")
L.append("| set | brief | model | " + " | ".join(CATS) + " | audit risk |\n|" + "---|" * (3 + len(CATS) + 1))
for r in REM:
    risk = ", ".join(r["risk"]["layout"] + r["risk"]["content"] + [f"flag: {f}" for f in r["risk"]["flags"]]).replace("css-", "")
    L.append(f"| {r['set']} | {r['brief']} | {r['slug']} | " + " | ".join(str(r["counts"].get(c, "")) for c in CATS) + f" | {risk} |")
L.append("")
import numpy as np
from PIL import Image
JOBS = json.load(open(os.path.join(HERE, "degraded-jobs.json")))
stds, hchanged, near_identical, hb, ha = [], 0, 0, [], []
for jb in JOBS:
    o = os.path.dirname(jb["outDir"]); d = jb["outDir"]
    a_im = Image.open(os.path.join(o, "screenshot.png")).convert("RGB"); b_im = Image.open(os.path.join(d, "screenshot.png")).convert("RGB")
    p_im = Image.open(os.path.join(d, "screenshot-phone.png")).convert("RGB")
    stds += [float(np.asarray(b_im).std()), float(np.asarray(p_im).std())]
    hb.append(a_im.height); ha.append(b_im.height); hchanged += a_im.height != b_im.height
    h = min(a_im.height, b_im.height)
    diff = (np.abs(np.asarray(a_im.crop((0, 0, 700, h)), dtype=int) - np.asarray(b_im.crop((0, 0, 700, h)), dtype=int)).max(axis=2) > 8).mean()
    near_identical += diff < 0.005 and a_im.height == b_im.height
L.append(f"Render checks: no degraded email rendered blank (pixel standard deviation of every render ≥ {min(stds):.0f}); desktop page height changed "
         f"on {hchanged} of 52 (mean {np.mean(hb):,.0f} → {np.mean(ha):,.0f} px); {near_identical} desktop renders differ from the original on fewer than 0.5 % of pixels (border-radius-only emails). "
         + ("Two phone renders scroll sideways after degradation where the originals did not: " + "; ".join(R["degraded_phone_overflow"]) + "."
            if R["degraded_phone_overflow"] else "No phone render scrolls sideways.")
         + " Expected side effects seen in the renders: gradient cards lose their background so white text on them disappears "
         "(e.g. F s09 Sonnet 4.6), flex rows stack, SVG logos and the one `<form>`-wrapped button vanish.\n")

L.append("## Results\n")
for j, res in R["judges"].items():
    a = res["all"]
    L.append(f"### {res['label']} ({res['n_judged_after']} of 52 pairs re-judged)\n")
    L.append("| render of the HTML arm | HTML | MJML | split | HTML share | MJML share |\n|---|---|---|---|---|---|")
    L.append(verdict_row("original (before)", a["before"]))
    L.append(verdict_row("degraded (after)", a["after"]))
    s = a["vs_safe_baseline"]["safe"]
    L.append(f"| safe pairs, original render (baseline) | {s['html']} | {s['mjml']} | {s['split']} | {pct(s['html'] / s['n'])} | {pct(s['mjml'] / s['n'])} |\n")
    L.append("Mean scores (1–10, averaged over the two orders), HTML arm and MJML arm, and the HTML − MJML difference:\n")
    L.append("| dimension | before HTML | before MJML | before diff | after HTML | after MJML | after diff | change in diff [95 % CI] | change in HTML score [95 % CI] | change in MJML score [95 % CI] |\n|---|---|---|---|---|---|---|---|---|---|")
    for k in DIMS:
        d = a[k]
        L.append(f"| {k} | {d['before_html']:.2f} | {d['before_mjml']:.2f} | {d['before_diff']:+.2f} | {d['after_html']:.2f} | {d['after_mjml']:.2f} | {d['after_diff']:+.2f} | {ci(d['change_in_diff'])} | {ci(d['change_in_html_score'])} | {ci(d['change_in_mjml_score'])} |")
    L.append("")
    m = a["mcnemar_html_win"]; m2 = a["mcnemar_mjml_win"]; sg = a["sign_test_html_orders"]; v = a["vs_safe_baseline"]; w = a["wilcoxon_overall_diff"]
    L.append("Tests:\n")
    L.append(f"- HTML wins the pair, before vs after (McNemar, exact): HTML won both times in {m['html_win_both']} pairs, before only in "
             f"{m['html_win_before_only']}, after only in {m['html_win_after_only']}, neither in {m['html_win_neither']}; p {p(m['p_exact_two_sided'])}.")
    L.append(f"- MJML wins the pair: before only {m2['mjml_win_before_only']}, after only {m2['mjml_win_after_only']}; p {p(m2['p_exact_two_sided'])}.")
    L.append(f"- Orders preferring HTML: {sg['before_orders_html']} → {sg['after_orders_html']} of {sg['of_orders']}; pairs where the count went up {sg['pairs_up']}, "
             f"down {sg['pairs_down']}, unchanged {sg['pairs_same']}; sign test p {p(sg['p_exact_two_sided'])}.")
    if "p" in w: L.append(f"- Per-pair overall difference (HTML − MJML), Wilcoxon signed-rank before vs after: W = {w['statistic']:.0f}, p {p(w['p'])}.")
    L.append(f"- HTML-win share against the safe baseline ({pct(v['safe']['html_share'])}): before {pct(v['before_html_share'])} "
             f"(Wilson 95 % [{pct(v['before_wilson'][0])}, {pct(v['before_wilson'][1])}], Fisher p {p(v['before_vs_safe_fisher_p'])}); after "
             f"{pct(v['after_html_share'])} (Wilson [{pct(v['after_wilson'][0])}, {pct(v['after_wilson'][1])}], Fisher p {p(v['after_vs_safe_fisher_p'])}). "
             f"MJML-win share after: {pct(v['after_mjml_share'])} vs {pct(v['safe_mjml_share'])} on safe pairs.")
    L.append(f"- Items the judge listed as missing from the HTML email, mean per order: {a['missing_before_html_mean']:.2f} before, {a['missing_after_html_mean']:.2f} after.")
    for sub, lab in (("structural_removal_pairs", "pairs that lost a layout / content feature"), ("cosmetic_only_pairs", "pairs that lost only border-radius / box-shadow")):
        if sub in res:
            x = res[sub]
            L.append(f"- {lab} (n = {x['n']}): {x['before']['html']}:{x['before']['mjml']}:{x['before']['split']} → {x['after']['html']}:{x['after']['mjml']}:{x['after']['split']} "
                     f"(HTML share {pct(x['before']['html'] / x['n'])} → {pct(x['after']['html'] / x['n'])}); overall diff {x['overall']['before_diff']:+.2f} → {x['overall']['after_diff']:+.2f}; "
                     f"McNemar p {p(x['mcnemar_html_win']['p_exact_two_sided'])}.")
    for st in ("S", "F"):
        if f"set_{st}" in res:
            x = res[f"set_{st}"]; L.append(f"- set {st} (n = {x['n']}): {x['before']['html']}:{x['before']['mjml']}:{x['before']['split']} → {x['after']['html']}:{x['after']['mjml']}:{x['after']['split']}.")
    L.append("")
    L.append("Words in the stated reasons (share of orders mentioning the word, by which email that order preferred):\n")
    words = [k for k in a["reasons_before_html_preferred"] if k != "orders"]
    L.append("| word | HTML preferred, before | HTML preferred, after | MJML preferred, before | MJML preferred, after |\n|---|---|---|---|---|")
    for wd in words:
        cells = []
        for key in ("reasons_before_html_preferred", "reasons_after_html_preferred", "reasons_before_mjml_preferred", "reasons_after_mjml_preferred"):
            r = a[key]; cells.append(f"{r[wd]} / {r['orders']}" if r["orders"] else "–")
        L.append(f"| {wd} | " + " | ".join(cells) + " |")
    L.append("")

L.append("## Cost\n")
L.append(f"OpenRouter spend as reported in the responses: GPT-6.1 Sol ${R['cost_usd']['gpt']:.2f}, Opus 5.5 ${R['cost_usd']['opus']:.2f}, total "
         f"${R['cost_usd']['gpt'] + R['cost_usd']['opus']:.2f} (budget about $5, stop at $6). Rendering cost nothing.\n")
L.append("## Limits\n")
L.append("- The degradation is a proxy: Outlook for Windows (Word engine) also mishandles `max-width` on divs, `margin` on some elements, "
         "`padding` on `<div>` / `<p>`, and ignores `@media`; none of that is simulated, so a div-built email is shown kinder than Outlook would. "
         "The 8 \"no table layout\"-only emails lost nothing but corners and shadows for the same reason.")
L.append("- MSO conditional fallbacks are not activated, and Chromium still applies Outlook-unsupported cosmetics that are not in the removal list "
         "(letter-spacing, opacity, rgba, web fonts). A real Outlook render would differ further in both directions.")
L.append("- The Opus before-verdicts were obtained through the Anthropic API and the after-verdicts through OpenRouter (same model id, same effort "
         "setting); the GPT judge took the same route both times and shows the same movement, which argues against the route being the cause.")
L.append("- Re-judging the same screenshots twice already moves some verdicts (judge noise); the McNemar counts give the asymmetry of the movement, "
         "not its total, and a noise-only control (re-judging the *original* renders) was not run within the budget.")
open(os.path.join(HERE, "degraded.md"), "w").write("\n".join(L) + "\n")
print("wrote degraded.md", len(L), "lines")
