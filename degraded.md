# Degraded-render re-judge of the 52 risky pairs

Question: the two screenshot judges preferred the free-HTML email in 73 % (Opus 5.5) / 67 % (GPT-6.1 Sol) of the 52 "risky" pairs (HTML uses something Outlook for Windows drops) but only 39 % / 38 % of the 258 safe pairs. Almost all risky HTML emails come from Claude Haiku 4.5 and Sonnet 4.6, so the preference could be for that family's emails rather than for the features Outlook drops. If the features are what the judges like, removing them should pull the preference back towards the safe baseline; if the family is what they like, it should not move.

## Method

- Pairs: the 52 pairs whose HTML email has an Outlook Windows layout or content feature unsupported per Can I Email (`clients['Outlook Windows'].layout` or `.content` non-empty in `results-S.json` / `results-F.json`) or a pipeline flag (`pipeline_flags` non-empty) — the definition in `pooled.py`. Sets: 12 from S, 40 from F. Models: Haiku 4.5 26, Sonnet 4.6 24, Sonnet 5.5 1 (float), GPT-6 Luna low 1 (float).
- Degradation (`degrade.py`): in `<style>` blocks (including inside `@media`) and `style` attributes, remove every declaration whose Can I Email feature Outlook for Windows does not support in the layout / content classes of `analyze-formats.py`: `display: flex | grid` and all flex / grid properties (gap, align-*, justify-*, order, grid-*); `position` other than static with top / right / bottom / left / inset and z-index; `transform`; `float` other than none; column-count, aspect-ratio, object-fit; any `background*` whose value holds a gradient; plus `border-radius` and `box-shadow`, which Outlook also drops. Selectors with `::before` / `::after` are removed whole. Inline `<svg>` and `<form>` elements are removed with their contents. Everything else is kept, in particular `max-width`, `margin`, `padding` (partial support in Outlook), `@media` blocks, web fonts and images. MSO conditional comments stay as the browser sees them (inactive), so an email with an MSO fallback is shown without it (2 of the 52 has one). The MJML arm is untouched.
- Render (`render-degraded.mjs`): the runner's screenshot procedure reproduced with the same Playwright 1.56.1 / chromium-1194 (desktop 700 × 900 viewport, phone 375 × 800, `networkidle` + 500 ms, full page, device scale 1). Re-rendering an original email this way reproduces its stored screenshot pixel for pixel, so the only difference between before and after is the degradation. Output: `<run>/<brief>/raw-html__<slug>/degraded/{email.degraded.html, screenshot.png, screenshot-phone.png, render.json, removed.json}`.
- Judges (`judge-degraded.py`): same instruction, JSON schema, tiling (1,500 px tiles, at most 6 per screenshot) and both orders as the runner's Opus judge and `judge-gpt.py`; the degraded HTML render against the MJML arm's original render. GPT-6.1 Sol via OpenRouter (`openai/gpt-6.1-sol`, reasoning effort medium) exactly as before. Opus 5.5 via OpenRouter (`anthropic/claude-opus-5.5`, reasoning effort medium, strict JSON schema) where the original verdicts came from the Anthropic API directly with `effort: medium` — same model, different route; the GPT route is unchanged. Written to `<run>/judge-degraded/<judge>/<brief>/<slug>.json`.
- "Before" is the original verdict on the same pair from `results-S.json` / `results-F.json` (`judge/`, `judge-gpt/`). A pair's verdict is *html* or *mjml* when both orders agree, *split* otherwise. Tests: exact McNemar (binomial on the discordant pairs) on "HTML wins the pair" before vs after; sign test on the number of orders (0–2) preferring HTML; Wilcoxon signed-rank on the per-pair overall-score difference; Fisher's exact test of the HTML-win share against the safe-pair baseline; paired bootstrap (4,000 resamples) for score changes. `analyze-degraded.py` → `results-degraded.json`.

## What was removed

Declarations / rules / elements removed over the 52 HTML emails (an email with only border-radius / box-shadow removed is "cosmetic only"; 44 of 52 lost at least one layout or content feature):

| what | removed |
|---|---|
| display:flex | 28 |
| flex/grid property | 61 |
| position | 9 |
| offset/z-index | 1 |
| transform | 3 |
| float | 4 |
| gradient | 42 |
| pseudo-element rule | 11 |
| <svg> element | 1 |
| <form> element | 1 |
| border-radius | 266 |
| box-shadow | 43 |
| **total** | **470** |

Per email (set, brief, model: removals; risk features from the audit):

| set | brief | model | display:flex | flex/grid property | position | offset/z-index | transform | float | gradient | pseudo-element rule | <svg> element | <form> element | border-radius | box-shadow | audit risk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S | medspa-aftercare | claude-haiku-4-5 |  |  |  |  | 1 |  | 2 |  |  |  | 5 | 2 | transform, linear-gradient, flag: no table layout |
| S | medspa-aftercare | claude-sonnet-4-6 |  |  | 2 |  |  |  | 2 | 4 |  |  | 8 | 2 | left-right-top-bottom, position, linear-gradient, pseudo-element-before, flag: position |
| S | salon-welcome | claude-haiku-4-5 |  |  |  |  | 1 |  | 2 |  |  |  | 5 | 1 | transform, linear-gradient, flag: no table layout |
| S | salon-welcome | claude-sonnet-4-6 | 4 | 11 |  |  |  |  | 3 |  |  |  | 7 |  | align-items, display-flex, gap, justify-content, linear-gradient, flag: display:flex, flag: no table layout |
| S | skin-winback | claude-haiku-4-5 |  |  | 1 |  |  |  | 1 | 1 |  |  | 5 | 1 | left-right-top-bottom, position, linear-gradient, pseudo-element-before, flag: no table layout, flag: position |
| S | skin-winback | claude-sonnet-4-6 |  |  |  |  |  |  | 1 |  |  |  | 13 | 1 | linear-gradient |
| S | spa-reminder | claude-haiku-4-5 | 1 |  |  |  |  |  | 1 |  |  |  | 4 | 1 | display-flex, linear-gradient, flag: display:flex, flag: no table layout |
| S | wellness-giftcard | claude-haiku-4-5 |  |  |  |  | 1 |  | 2 |  |  |  | 4 | 1 | transform, linear-gradient, flag: no table layout |
| S | wellness-giftcard | claude-sonnet-4-6 |  |  | 1 |  |  |  | 2 |  |  |  | 3 | 2 | position, linear-gradient, flag: no table layout, flag: position |
| S | wellness-giftcard | gpt-6-luna__low |  |  |  |  |  | 3 |  |  |  |  | 1 |  | float |
| S | yoga-newsletter | claude-haiku-4-5 |  |  |  |  |  |  | 2 |  |  | 1 | 5 |  | linear-gradient, html-button-submit, html-form, flag: <form> element, flag: no table layout |
| S | yoga-newsletter | claude-sonnet-4-6 | 6 | 15 | 1 | 1 |  |  | 1 | 1 | 1 |  | 9 |  | align-items, display-flex, gap, justify-content, left-right-top-bottom, position, linear-gradient, pseudo-element-before, html-svg, flag: display:flex, flag: inline <svg>, flag: position |
| F | s01 | claude-haiku-4-5 |  |  |  |  |  |  |  |  |  |  | 3 | 1 | flag: no table layout |
| F | s01 | claude-sonnet-4-6 | 3 | 10 |  |  |  |  |  |  |  |  | 7 | 1 | align-items, display-flex, gap, justify-content, flag: display:flex, flag: no table layout |
| F | s02 | claude-haiku-4-5 |  |  | 1 |  |  |  |  | 1 |  |  | 4 | 1 | left-right-top-bottom, position, pseudo-element-before, flag: no table layout, flag: position |
| F | s02 | claude-sonnet-4-6 | 1 | 1 |  |  |  |  | 2 |  |  |  | 7 | 1 | align-items, display-flex, linear-gradient, flag: display:flex, flag: no table layout |
| F | s03 | claude-haiku-4-5 |  |  |  |  |  |  |  |  |  |  | 5 | 1 | flag: no table layout |
| F | s03 | claude-sonnet-4-6 |  |  | 1 |  |  |  |  | 1 |  |  | 5 | 1 | left-right-top-bottom, position, pseudo-element-before, flag: no table layout, flag: position |
| F | s04 | claude-haiku-4-5 |  |  |  |  |  |  |  |  |  |  | 6 | 1 | flag: no table layout |
| F | s04 | claude-sonnet-4-6 | 1 | 3 |  |  |  |  |  |  |  |  | 7 | 1 | display-flex, gap, flag: display:flex |
| F | s05 | claude-haiku-4-5 |  |  |  |  |  |  |  |  |  |  | 1 | 1 | flag: no table layout |
| F | s05 | claude-sonnet-4-6 | 2 | 3 |  |  |  |  |  |  |  |  | 6 | 1 | align-items, display-flex, justify-content, flag: display:flex, flag: no table layout |
| F | s06 | claude-haiku-4-5 |  |  |  |  |  |  | 1 |  |  |  | 3 | 1 | linear-gradient, flag: no table layout |
| F | s06 | claude-sonnet-4-6 | 1 | 3 |  |  |  |  |  |  |  |  | 6 | 1 | align-items, display-flex, gap, flag: display:flex |
| F | s07 | claude-haiku-4-5 |  |  |  |  |  |  |  | 1 |  |  | 2 |  | pseudo-element-before, flag: no table layout |
| F | s07 | claude-sonnet-4-6 |  |  | 1 |  |  |  |  | 1 |  |  | 5 | 1 | left-right-top-bottom, position, pseudo-element-before, flag: no table layout, flag: position |
| F | s08 | claude-haiku-4-5 |  |  |  |  |  |  | 1 |  |  |  | 3 | 1 | linear-gradient, flag: no table layout |
| F | s08 | claude-sonnet-4-6 | 1 | 1 |  |  |  |  |  |  |  |  | 7 | 2 | align-items, display-flex, flag: display:flex |
| F | s09 | claude-haiku-4-5 |  |  |  |  |  |  | 1 |  |  |  | 4 | 1 | linear-gradient, flag: no table layout |
| F | s09 | claude-sonnet-4-6 | 2 | 5 |  |  |  |  | 1 |  |  |  | 9 | 1 | align-items, display-flex, gap, justify-content, linear-gradient, flag: display:flex, flag: no table layout |
| F | s10 | claude-haiku-4-5 |  |  |  |  |  |  |  |  |  |  | 4 | 1 | flag: no table layout |
| F | s11 | claude-haiku-4-5 | 1 | 3 |  |  |  |  |  |  |  |  | 2 | 1 | display-flex, flex-wrap, gap, justify-content, flag: display:flex, flag: no table layout |
| F | s11 | claude-sonnet-4-6 |  |  |  |  |  |  | 2 |  |  |  | 7 | 1 | linear-gradient |
| F | s12 | claude-haiku-4-5 |  |  |  |  |  |  | 1 |  |  |  | 4 | 1 | linear-gradient, flag: no table layout |
| F | s12 | claude-sonnet-4-6 |  |  |  |  |  |  | 1 |  |  |  | 5 | 1 | linear-gradient, flag: no table layout |
| F | s13 | claude-haiku-4-5 | 1 | 1 |  |  |  |  | 1 |  |  |  | 4 |  | align-items, display-flex, linear-gradient, flag: display:flex, flag: no table layout |
| F | s13 | claude-sonnet-4-6 |  |  |  |  |  |  | 2 |  |  |  | 8 | 1 | linear-gradient |
| F | s14 | claude-haiku-4-5 |  |  |  |  |  |  | 1 |  |  |  | 3 | 1 | linear-gradient, flag: no table layout |
| F | s14 | claude-sonnet-4-6 |  |  |  |  |  |  | 3 |  |  |  | 7 | 1 | linear-gradient |
| F | s14 | claude-sonnet-5-5 |  |  |  |  |  | 1 |  |  |  |  | 6 |  | float |
| F | s15 | claude-haiku-4-5 | 1 | 1 |  |  |  |  |  |  |  |  | 4 | 1 | align-items, display-flex, flag: display:flex, flag: no table layout |
| F | s15 | claude-sonnet-4-6 |  |  |  |  |  |  | 2 |  |  |  | 7 | 1 | linear-gradient |
| F | s16 | claude-haiku-4-5 |  |  | 1 |  |  |  | 1 | 1 |  |  | 1 |  | left-right-top-bottom, position, linear-gradient, pseudo-element-before, flag: no table layout, flag: position |
| F | s16 | claude-sonnet-4-6 |  |  |  |  |  |  | 1 |  |  |  | 12 |  | linear-gradient |
| F | s17 | claude-haiku-4-5 |  |  |  |  |  |  |  |  |  |  | 3 | 1 | flag: no table layout |
| F | s17 | claude-sonnet-4-6 | 1 | 2 |  |  |  |  |  |  |  |  | 6 |  | align-items, display-flex, flag: display:flex, flag: no table layout |
| F | s18 | claude-haiku-4-5 |  |  |  |  |  |  | 1 |  |  |  | 4 | 1 | linear-gradient, flag: no table layout |
| F | s18 | claude-sonnet-4-6 |  |  |  |  |  |  |  |  |  |  | 4 | 1 | flag: no table layout |
| F | s19 | claude-haiku-4-5 |  |  |  |  |  |  | 1 |  |  |  | 4 |  | linear-gradient, flag: no table layout |
| F | s19 | claude-sonnet-4-6 | 1 | 1 |  |  |  |  |  |  |  |  | 6 | 1 | align-items, display-flex, flag: display:flex, flag: no table layout |
| F | s20 | claude-haiku-4-5 |  |  |  |  |  |  |  |  |  |  | 2 |  | flag: no table layout |
| F | s20 | claude-sonnet-4-6 | 1 | 1 |  |  |  |  |  |  |  |  | 4 |  | align-items, display-flex, flag: display:flex, flag: no table layout |

Render checks: no degraded email rendered blank (pixel standard deviation of every render ≥ 26); desktop page height changed on 11 of 52 (mean 1,774 → 1,786 px); 8 desktop renders differ from the original on fewer than 0.5 % of pixels (border-radius-only emails). Two phone renders scroll sideways after degradation where the originals did not: S skin-winback claude-sonnet-4-6 (392 px); F s11 claude-sonnet-4-6 (407 px). Expected side effects seen in the renders: gradient cards lose their background so white text on them disappears (e.g. F s09 Sonnet 4.6), flex rows stack, SVG logos and the one `<form>`-wrapped button vanish.

## Results

### Claude Opus 5.5 (52 of 52 pairs re-judged)

| render of the HTML arm | HTML | MJML | split | HTML share | MJML share |
|---|---|---|---|---|---|
| original (before) | 38 | 8 | 6 | 73 % | 15 % |
| degraded (after) | 21 | 27 | 4 | 40 % | 52 % |
| safe pairs, original render (baseline) | 101 | 113 | 44 | 39 % | 44 % |

Mean scores (1–10, averaged over the two orders), HTML arm and MJML arm, and the HTML − MJML difference:

| dimension | before HTML | before MJML | before diff | after HTML | after MJML | after diff | change in diff [95 % CI] | change in HTML score [95 % CI] | change in MJML score [95 % CI] |
|---|---|---|---|---|---|---|---|---|---|
| design | 7.88 | 6.93 | +0.94 | 6.66 | 7.38 | -0.71 | -1.65 [-2.12, -1.22] | -1.21 [-1.60, -0.88] | +0.44 [+0.30, +0.60] |
| readability | 7.90 | 7.01 | +0.89 | 7.04 | 7.35 | -0.31 | -1.20 [-1.68, -0.76] | -0.87 [-1.27, -0.52] | +0.34 [+0.20, +0.49] |
| briefCoverage | 9.44 | 9.12 | +0.32 | 8.67 | 9.21 | -0.54 | -0.86 [-1.30, -0.47] | -0.77 [-1.15, -0.44] | +0.09 [-0.03, +0.21] |
| phone | 8.16 | 7.48 | +0.68 | 7.38 | 7.62 | -0.24 | -0.92 [-1.34, -0.55] | -0.79 [-1.13, -0.47] | +0.13 [+0.01, +0.26] |
| overall | 7.88 | 6.76 | +1.12 | 6.68 | 7.30 | -0.62 | -1.74 [-2.31, -1.24] | -1.20 [-1.63, -0.82] | +0.54 [+0.38, +0.71] |

Tests:

- HTML wins the pair, before vs after (McNemar, exact): HTML won both times in 21 pairs, before only in 17, after only in 0, neither in 14; p < 0.0001.
- MJML wins the pair: before only 0, after only 19; p < 0.0001.
- Orders preferring HTML: 82 → 46 of 104; pairs where the count went up 0, down 22, unchanged 30; sign test p < 0.0001.
- Per-pair overall difference (HTML − MJML), Wilcoxon signed-rank before vs after: W = 6, p < 0.0001.
- HTML-win share against the safe baseline (39 %): before 73 % (Wilson 95 % [60 %, 83 %], Fisher p < 0.0001); after 40 % (Wilson [28 %, 54 %], Fisher p = 0.877). MJML-win share after: 52 % vs 44 % on safe pairs.
- Items the judge listed as missing from the HTML email, mean per order: 0.37 before, 0.87 after.
- pairs that lost a layout / content feature (n = 44): 32:6:6 → 16:25:3 (HTML share 73 % → 36 %); overall diff +1.08 → -0.93; McNemar p < 0.0001.
- pairs that lost only border-radius / box-shadow (n = 8): 6:2:0 → 5:2:1 (HTML share 75 % → 62 %); overall diff +1.38 → +1.12; McNemar p = 1.000.
- set S (n = 12): 8:2:2 → 3:9:0.
- set F (n = 40): 30:6:4 → 18:18:4.

Words in the stated reasons (share of orders mentioning the word, by which email that order preferred):

| word | HTML preferred, before | HTML preferred, after | MJML preferred, before | MJML preferred, after |
|---|---|---|---|---|
| polished | 36 / 82 | 17 / 46 | 12 / 22 | 18 / 58 |
| card | 27 / 82 | 8 / 46 | 6 / 22 | 9 / 58 |
| modern | 0 / 82 | 0 / 46 | 0 / 22 | 0 / 58 |
| premium | 3 / 82 | 1 / 46 | 0 / 22 | 0 / 58 |
| contrast | 10 / 82 | 3 / 46 | 3 / 22 | 8 / 58 |
| cut off | 0 / 82 | 0 / 46 | 2 / 22 | 2 / 58 |
| overflow / sideways | 0 / 82 | 0 / 46 | 0 / 22 | 0 / 58 |
| missing / invisible | 18 / 82 | 11 / 46 | 0 / 22 | 28 / 58 |
| broken | 7 / 82 | 7 / 46 | 1 / 22 | 5 / 58 |
| cramped / stacked | 13 / 82 | 9 / 46 | 9 / 22 | 2 / 58 |
| plain / basic | 14 / 82 | 8 / 46 | 5 / 22 | 10 / 58 |

### GPT-6.1 Sol (52 of 52 pairs re-judged)

| render of the HTML arm | HTML | MJML | split | HTML share | MJML share |
|---|---|---|---|---|---|
| original (before) | 35 | 11 | 6 | 67 % | 21 % |
| degraded (after) | 16 | 30 | 6 | 31 % | 58 % |
| safe pairs, original render (baseline) | 98 | 121 | 39 | 38 % | 47 % |

Mean scores (1–10, averaged over the two orders), HTML arm and MJML arm, and the HTML − MJML difference:

| dimension | before HTML | before MJML | before diff | after HTML | after MJML | after diff | change in diff [95 % CI] | change in HTML score [95 % CI] | change in MJML score [95 % CI] |
|---|---|---|---|---|---|---|---|---|---|
| design | 8.40 | 7.77 | +0.63 | 7.51 | 8.05 | -0.54 | -1.17 [-1.55, -0.84] | -0.89 [-1.20, -0.62] | +0.28 [+0.16, +0.39] |
| readability | 8.23 | 7.50 | +0.73 | 7.62 | 7.76 | -0.14 | -0.88 [-1.21, -0.58] | -0.62 [-0.89, -0.38] | +0.26 [+0.14, +0.38] |
| briefCoverage | 9.54 | 9.50 | +0.04 | 9.19 | 9.51 | -0.32 | -0.36 [-0.64, -0.12] | -0.35 [-0.62, -0.14] | +0.01 [-0.08, +0.11] |
| phone | 8.41 | 8.07 | +0.35 | 8.03 | 8.15 | -0.12 | -0.47 [-0.80, -0.17] | -0.38 [-0.66, -0.12] | +0.09 [+0.00, +0.18] |
| overall | 8.24 | 7.62 | +0.62 | 7.47 | 7.97 | -0.50 | -1.12 [-1.53, -0.76] | -0.77 [-1.08, -0.50] | +0.36 [+0.22, +0.49] |

Tests:

- HTML wins the pair, before vs after (McNemar, exact): HTML won both times in 15 pairs, before only in 20, after only in 1, neither in 16; p < 0.0001.
- MJML wins the pair: before only 1, after only 20; p < 0.0001.
- Orders preferring HTML: 76 → 38 of 104; pairs where the count went up 1, down 25, unchanged 26; sign test p < 0.0001.
- Per-pair overall difference (HTML − MJML), Wilcoxon signed-rank before vs after: W = 32, p < 0.0001.
- HTML-win share against the safe baseline (38 %): before 67 % (Wilson 95 % [54 %, 78 %], Fisher p = 0.0002); after 31 % (Wilson [20 %, 44 %], Fisher p = 0.349). MJML-win share after: 58 % vs 47 % on safe pairs.
- Items the judge listed as missing from the HTML email, mean per order: 0.27 before, 0.42 after.
- pairs that lost a layout / content feature (n = 44): 31:9:4 → 12:28:4 (HTML share 70 % → 27 %); overall diff +0.64 → -0.68; McNemar p < 0.0001.
- pairs that lost only border-radius / box-shadow (n = 8): 4:2:2 → 4:2:2 (HTML share 50 % → 50 %); overall diff +0.56 → +0.50; McNemar p = 1.000.
- set S (n = 12): 8:3:1 → 2:9:1.
- set F (n = 40): 27:8:5 → 14:21:5.

Words in the stated reasons (share of orders mentioning the word, by which email that order preferred):

| word | HTML preferred, before | HTML preferred, after | MJML preferred, before | MJML preferred, after |
|---|---|---|---|---|
| polished | 37 / 76 | 17 / 38 | 10 / 28 | 19 / 66 |
| card | 13 / 76 | 6 / 38 | 7 / 28 | 7 / 66 |
| modern | 0 / 76 | 0 / 38 | 0 / 28 | 0 / 66 |
| premium | 0 / 76 | 1 / 38 | 0 / 28 | 0 / 66 |
| contrast | 13 / 76 | 8 / 38 | 4 / 28 | 12 / 66 |
| cut off | 1 / 76 | 0 / 38 | 2 / 28 | 2 / 66 |
| overflow / sideways | 0 / 76 | 0 / 38 | 0 / 28 | 0 / 66 |
| missing / invisible | 3 / 76 | 5 / 38 | 1 / 28 | 10 / 66 |
| broken | 1 / 76 | 2 / 38 | 0 / 28 | 0 / 66 |
| cramped / stacked | 12 / 76 | 2 / 38 | 5 / 28 | 2 / 66 |
| plain / basic | 0 / 76 | 0 / 38 | 2 / 28 | 3 / 66 |

## Cost

OpenRouter spend as reported in the responses: GPT-6.1 Sol $1.81, Opus 5.5 $3.61, total $5.42 (budget about $5, stop at $6). Rendering cost nothing.

## Limits

- The degradation is a proxy: Outlook for Windows (Word engine) also mishandles `max-width` on divs, `margin` on some elements, `padding` on `<div>` / `<p>`, and ignores `@media`; none of that is simulated, so a div-built email is shown kinder than Outlook would. The 8 "no table layout"-only emails lost nothing but corners and shadows for the same reason.
- MSO conditional fallbacks are not activated, and Chromium still applies Outlook-unsupported cosmetics that are not in the removal list (letter-spacing, opacity, rgba, web fonts). A real Outlook render would differ further in both directions.
- The Opus before-verdicts were obtained through the Anthropic API and the after-verdicts through OpenRouter (same model id, same effort setting); the GPT judge took the same route both times and shows the same movement, which argues against the route being the cause.
- Re-judging the same screenshots twice already moves some verdicts (judge noise); the McNemar counts give the asymmetry of the movement, not its total, and a noise-only control (re-judging the *original* renders) was not run within the budget.
