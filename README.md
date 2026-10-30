# Format constraints: raw HTML vs MJML-constrained generation (article 2, "Constrained by Design")

Question: when a model is forced to write an email in a component language (MJML) instead of free HTML, what does
the constraint cost (copy, coverage, invention, cost, a judge's impression) and what does it buy (mail-client
compatibility)? And does a browser-screenshot judge's preference follow the compatibility risk or run against it?

## Data

- **Set S** (2026-10-09): `generation-approaches/2026-10-09-raw-formats/` — six wellness briefs (`prompts-setS.json`,
  exported from `scripts/v3/prompts.ts`) × 12 model configurations × raw MJML / raw HTML = 72 HTML + 71 MJML (one MJML
  did not compile: `<body>` for `<mj-body>`). Also 24 + 24 MJML with a styling reference (v1 / v2), Claude 5.x only.
- **Set F** (2026-10-29): `generation-approaches/2026-10-29-raw-formats-setF/` — the 20 synthetic-20 businesses (brief +
  "Details about the business:" + fact sheet, `prompts.json`) × 12 configurations × 2 formats = 240 HTML + 239 MJML (one
  MJML had a doubled `<mjml>` root and compiled to nothing). Generated with `scripts/compare-setf.ts` (UNTRACKED copy of
  `scripts/compare-generation-approaches.ts`: `--prompt-file`, in-memory usage reporter instead of the database, no
  harness import, judge wording "for a small business"), `--combos 'raw__*,raw-html__*' --concurrency 4 --compat-tool
  research/generation-approaches/tools/doiuse --judge`. Generation $19.95, Opus judge $13.22.
- Can I Email database: scratchpad `caniemail/data.json`, `last_update 2026-09-16`, 308 features, downloaded 2026-10-28.

## Scripts (all `python3 -I`)

| script | what |
|---|---|
| `audit.py` | Can I Email audit primitives (Collector, css_features, html_features, latest). Patched 2026-10-29: `float: none` and `position: static` are not feature uses (mj-social emits `float:none`). |
| `analyze-formats.py <set> <run> <caniemail> <prompts> [claims dir]` | per-email measures (features outside `@media` only; classes layout / content / fonts / cosmetic; MSO, media query, table layout, Google Fonts, bytes, words, placeholders, unsubscribe, phone scroll, pipeline flags), both screenshot judges (`judge/`, `judge-gpt/`), claims judges, paired bootstrap CIs → `results-<set>.json`, printed summary (`analysis-<set>.txt`). `analyze_formats.py` is a copy for import. |
| `claims-judge-formats.py <set> <run> <prompts>` | text-only claims + coverage judges (Opus 5.5, GPT-6.1 Sol via OpenRouter) → `claims-judge/<set>/<judge>/<brief>__<combo>.json`. S $4.77, F $9.83. |
| `judge-gpt.py <run> <prompts> [conc]` | second blind screenshot judge, GPT-6.1 Sol via OpenRouter, same instruction/schema/tiles as the runner's Opus judge → `<run>/judge-gpt/`. S $2.29, F $6.36. |
| `styled-arm.py <run> <caniemail>` | the MJML + styling-reference arms on set S → `results-styled.json`. |
| `pooled.py results-S.json results-F.json` | pooled contrasts, shares, judges by family and by risk → `pooled.txt`. |
| `figures.py <out> results-S.json results-F.json --sheet <run F>` | fig1-pairs (s17 contact sheet), fig2-risk, fig3-models → `o1-articles/figures/article2/` (venv in scratchpad: matplotlib, Pillow). |

## Final numbers (pooled, 312 HTML / 310 MJML, 310 pairs; HTML − MJML, 95 % bootstrap)

- words 218 vs 214 (+4 [−1, +8]); coverage 0.993 vs 0.995 (Opus), 0.972 vs 0.969 (GPT); invented claims 2.77 vs 2.79
  (Opus), 3.15 vs 3.20 (GPT); placeholders 0.142 vs 0.084 (+0.058 [+0.016, +0.106]); unsubscribe 40 % both.
- tokens 2,595 vs 1,975 (+620 [+519, +723], ratio 1.30); cost $0.053 vs $0.039 (+$0.014, ratio 1.29); 24 s vs 21 s;
  bytes 7.1 KB vs 24.1 KB.
- MSO fallback 15/312 vs 310/310; media query 110/312 vs 310/310; table layout 273/312; phone overflow 8 vs 2.
- Outlook Windows: layout 28/312 (9.0 %) vs 1/310; content 32/312 (10.3 %) vs 1/310. Gmail web: layout 24/312 (7.7 %) vs
  1/310; content 8/312 vs 0. Web fonts: 6/312 vs 36/310 (MJML loads Google Fonts more). Apple Mail: 0 both.
- Features: flex 16, align-items 13, position 8, offsets 7, gap 7, transform 3; gradient 28, ::before 8, form/svg 1 each.
- Family (HTML): Claude 4.x 52 emails → no-table 39, Outlook layout 26, content 32; Claude 5.x 104 → layout 1, MSO 14, mq 74;
  GPT-6 156 → layout 1, MSO 0, mq 18. doiuse flags 44 HTML / 0 MJML.
- Opus judge: 139 HTML : 121 MJML : 50 split; design +0.32 [+0.20, +0.44], readability +0.22, coverage +0.06 n.s., phone
  −0.05 n.s., overall +0.23 [+0.09, +0.37]; first-slot 56 % (S) / 51 % (F). GPT judge: 133 : 132 : 45; design +0.14
  [+0.05, +0.24], readability +0.16, phone −0.12 [−0.22, −0.03], overall +0.04 n.s.; second slot 55 % / 51 %. Agreement
  198/224 decided pairs; score-difference correlation 0.70 (S), 0.69 (F).
- By family (Opus / GPT): Claude 5.x 59:19:25 / 54:34:15; Claude 4.x 36:8:8 / 35:11:6; GPT-6 44:94:17 / 44:87:24.
- **Renderer bias:** HTML risky (Outlook layout/content or flag, 52 pairs): Opus 38:8:6, GPT 35:11:6; HTML safe (258):
  Opus 101:113:44, GPT 98:121:39. No-table HTML (39): Opus 30:5:4. Reasons: "polished" 36, "card" 27 of 82 risky wins.
- Styled arm (24 pairs, Claude 5.x, set S): plain MJML 1:17:6 (7.65 vs 8.44); ref v1 5:14:5 (7.69 vs 8.19); ref v2
  5:15:4 (7.81 vs 8.25); all MSO + mq, 0 layout/content risk; tokens 2,865 → 3,099 / 2,893.

## Limits to state

Support is looked up, not rendered in real clients; "unsupported" with a fallback degrades rather than breaks. Database
hand-maintained and dated. One instruction, no images/brand. Judges are models. Prices on one day.
