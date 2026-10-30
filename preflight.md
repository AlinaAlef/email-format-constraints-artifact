# Real-client renders of the 52 risky pairs (Preflight, 2026-10-30)

- Renders: Preflight screenshot API (https://preflight.qa), classic Outlook for Windows (`outlook_classic_win`, light) and Chrome desktop (`chrome_desktop`, light), both arms of the 52 risky pairs = 104 emails, 208 screenshots, 0 failures (`preflight-render.py`, `preflight-results.json`; PNGs under `<run>/<brief>/<combo>/preflight/`). 208 of 650 trial credits.
- Judges: same instruction and schema as the original pairwise judge, desktop render only (phone criterion neutralised), both orders, verdict = both orders agree (`judge-preflight.py`, `analyze-preflight.py` → `results-preflight.json`). Both arms shown in the SAME client.
- Cost: Opus $4.15 (Chrome) + $2.97 (Outlook); GPT $2.15 + $1.52; total $10.79.

| Judge | Renderer | HTML | MJML | Split | HTML share | mean overall diff (HTML − MJML) |
|---|---|---|---|---|---|---|
| Opus 5.5 | Chrome (Preflight) | 37 | 11 | 4 | 71% | +1.06 |
| Opus 5.5 | Outlook classic | 2 | 48 | 2 | 4% | −3.17 |
| GPT-6.1 Sol | Chrome (Preflight) | 36 | 9 | 7 | 69% | +0.80 |
| GPT-6.1 Sol | Outlook classic | 2 | 48 | 2 | 4% | −2.02 |

- Chrome replicates the original Chromium verdicts (73% / 67%).
- McNemar exact on "HTML wins", Chrome vs Outlook: Opus 35 Chrome-only vs 0 Outlook-only, p = 5.8e-11; GPT 34 vs 0, p = 1.2e-10.
- Change in overall-score difference (Outlook − Chrome): Opus −4.23, GPT −2.82 points; Wilcoxon p = 3.3e-10 and 3.7e-10.
- Opus reasons on Outlook renders mention "broken" 49 times, "invisible" 17, "unreadable" 9 (summed over 104 orders).
- Caveat: in Outlook both arms are shown in Outlook, and MJML is built for it, so this measures what an Outlook reader would prefer, not a judge bias; the safe-pair baseline (Chromium) is not directly comparable. Outlook share among opens is 3.5% (Litmus, Sept 2026) and much higher on corporate lists.
- Figure: `figures/article2/fig4-outlook-real.png` (F s02 and S medspa-aftercare, Claude Sonnet 4.6: free HTML in Chrome, free HTML in Outlook, MJML in Outlook).
