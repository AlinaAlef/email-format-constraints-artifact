# Pre-registered follow-up tests, 8 November 2026

This file was written and committed before any of the tests below were run. It fixes the samples, the
conditions, the outcomes and the decision rules. Every test listed here will be reported, in the article
or in this repository, whatever its result.

## What was exploratory

The original study was not pre-registered. Its order, from file timestamps in the author's records:
generation of set S on 9 October and set F on 29 October 2026; the compatibility audit and the two
screenshot judges on 29 October (03:28 to 03:41); the split of pairs into risky and safe, the CSS-removal
counterfactual and its re-judging on 29 October (23:04 to 23:28), after the first judging had shown that
the judges preferred the free-HTML email more often where it carried a feature Outlook drops; the
Preflight renders in classic Outlook and Chrome and their judging on 30 October. The stratified
comparison was therefore an observation, and the CSS removal and the Outlook renders were tests of it
designed after it was seen. The tests below are the next round, fixed before running.

## Common material

- Pairs, emails and screenshots: the 310 pairs of `data/pairs.csv`, with the Chromium renders (desktop
  700 px and phone 375 px) used for the original judging. No email is regenerated for E1 to E4 and E6.
- Risky pairs: the 52 pairs with `risky = True` (free-HTML email with an Outlook-Windows layout or content
  feature per Can I Email, or a linter flag).
- Safe sample: 52 of the 258 safe pairs, drawn once with Python `random.Random("renderer-bias-2026-11-08").sample`
  over the sorted list of (set, brief, model) keys. The sample is listed at the end of this file.
- Judges: Claude Opus 5.5 and GPT-6.1 Sol through OpenRouter, reasoning effort medium, the instruction and
  JSON schema of `scripts/judge-prompt.md`, tiles of 1,500 px, at most six per render, both orders. A
  verdict is stable when the judge picks the same email in both orders; otherwise it is `split`.
- Statistics: shares as counts with Wilson 95% intervals; paired before-and-after verdicts on the same
  pairs by McNemar's exact test (discordant pairs); risky against safe by Fisher's exact test; logistic
  regression coefficients with 95% profile intervals. Two-sided tests, alpha 0.05, no correction across
  tests (each test answers a different question and all are reported).

## E1. A judge told about the target client

Question: is renderer bias a property of what the judge is shown, or does telling the judge about the
target client remove it?

Material: the 52 risky pairs, original browser screenshots. Two instruction variants, each run with both
judges in both orders:
- *generic*: the instruction adds, after the brief, that the recipients read mail in classic Outlook for
  Windows, which renders HTML with Word's engine and does not render flexbox, grid, CSS positioning,
  transforms, floats, gradient backgrounds, `::before`/`::after` content, inline SVG, forms, rounded
  corners or shadows, and ignores max-width on most elements; the judge is asked to score how each email
  will look there, not how the screenshot looks.
- *specific*: the generic text plus, for each email, the list of Outlook-dropped features the audit found
  in it (from `data/emails.csv`, columns `outlook_windows_layout` and `outlook_windows_content`, plus
  the linter flags), or "none found" for an email with none.

Outcome: the share of the 52 risky pairs in which the judge consistently picks the free-HTML email, per
judge and variant.

Decision rule: the browser verdicts gave 73% (Opus) and 67% (GPT) on these pairs; the safe stratum gave
39% and 38%; the real Outlook renders gave 4%. If a warned share's Wilson interval still excludes the
safe-stratum share and McNemar's test against the browser verdicts is not significant, the warning did
not remove the bias. If the warned share falls to the safe-stratum interval or below, telling the judge
about the client is a mitigation and the article's sentence that "no treatment of the judge removes it"
is withdrawn. Anything in between is reported as partial.

## E3. Injecting one dropped feature into safe emails

Question: does adding a feature Outlook drops to an email that had none raise the browser judge's
preference for it? (The CSS-removal test showed the reverse direction.)

Material: the free-HTML email of each pair in the safe sample. One intervention: the first block that
carries a non-white background colour (the hero or header band, found as the first `td`, `th`, `table`,
`div` or `section` with a `background-color`, `background` or `bgcolor` set to a colour other than white or
transparent) receives a `background-image: linear-gradient(135deg, C, C')` where C is its colour and C'
is C darkened by 22% in HSL lightness. Nothing else changes. The email is re-rendered with the same
Chromium build and settings as the original (`render-degraded.mjs`), re-audited, and re-judged against
its unchanged MJML opponent by both judges in both orders. An email with no such block is excluded and
counted.

Outcome: the share of injected pairs in which the judge consistently picks the free-HTML email, before
(original verdicts) and after.

Decision rule: McNemar's exact test on the paired verdicts, per judge. An increase in the free-HTML share
with p < 0.05 supports the causal reading; no change or a decrease is reported as a limit of that reading
(a gradient alone may not carry the "polish" the judges named).

## E4. A third judge from a third vendor

Question: do a third vendor's judge show the same stratified preference?

Material: Gemini 3.1 Pro (preview) through OpenRouter, same instruction, schema, tiles and both orders,
on the 52 risky pairs and the 52-pair safe sample, browser screenshots.

Outcome: the free-HTML consistent-win share in the risky pairs against the safe sample.

Decision rule: Fisher's exact test, risky against safe. A significantly higher risky share replicates the
bias in a third family; agreement with each of the two original judges (Cohen's kappa on stable
verdicts) is reported alongside.

## E5. Run-to-run variation

Question: how much do the audit shares and the token ratio move between two runs of the same prompt?

Material: two configurations, one from the risky family (Claude Sonnet 4.6) and one safe (GPT-6 Astra,
high effort), re-run on the 20 set-F briefs in both formats under the original instructions: 80 new
emails. Audited and costed as the originals; not judged.

Outcome: per configuration, the share of free-HTML emails with an Outlook layout or content feature and
the HTML/MJML output-token ratio, in the original run and the re-run. Descriptive; no hypothesis. The
re-run does not replace the original data.

## E6. A simple baseline for the judges' preference

Question: does compatibility risk still predict the judges' preference once simple size and complexity
measures are controlled?

Material: `data/pairs.csv` and `data/emails.csv`, no new calls.

Model: per judge, logistic regression of "consistent free-HTML win" (1) against "MJML win or split" (0)
on: risky (0/1); the HTML minus MJML difference in bytes; the same difference in visible words; the count
of Outlook-Windows cosmetic features in the HTML email; the count of distinct features outside media
queries in the HTML email; and set (S/F). Standardised continuous predictors.

Decision rule: the risky coefficient's 95% interval excludes zero in both judges' models supports the
claim; otherwise the article reports that risk and complexity cannot be separated on these data.

## E2, conditional on access to a rendering service

Question: in the real Outlook renders, do safe pairs also move to MJML, or only the risky ones? The
Outlook result (2 of 52 risky pairs to free HTML) has no safe-pair control; MJML's compiler targets
Outlook, so a general MJML advantage in that client and a loss of the risky features are confounded.

Material: the 52-pair safe sample rendered in desktop Chrome and classic Outlook for Windows by the same
service as before, judged as the risky pairs were (desktop only, both orders, both judges).

Outcome: the free-HTML consistent-win share among safe pairs in Outlook. Decision rule: compared with the
risky pairs' Outlook share (4%) and the browser safe share (39% and 38%) by Fisher's exact test. If the
safe pairs also fall to the risky pairs' level, the Outlook result is reported as a general advantage of
compiled MJML in that client, and the renderer-bias claim rests on the stratified comparison, the CSS
removal and E1 to E4. If they stay at the browser level, the Outlook result is specific to the dropped
features. This test runs only if the rendering service is available before the article's revision
deadline; if it does not run, this file says so.

## E7. Human panel (registered separately)

A panel in which people choose between the two emails of a pair shown as Chrome or as Outlook renders
will be registered in its own file before it opens.

## Safe sample (52 of 258; seed "renderer-bias-2026-11-08")

F/s01/gpt-6-astra__low, F/s01/gpt-6.1-sol__low, F/s02/claude-opus-5-5, F/s02/claude-sonnet-5-5,
F/s02/gpt-6-luna__high, F/s03/claude-fable-5-1, F/s03/claude-haiku-5-5, F/s03/gpt-6-astra__high,
F/s03/gpt-6-luna__low, F/s03/gpt-6.1-sol__low, F/s04/claude-opus-5-5, F/s04/gpt-6.1-sol__low,
F/s05/claude-haiku-5-5, F/s05/gpt-6-luna__high, F/s06/gpt-6-astra__low, F/s06/gpt-6-luna__low,
F/s07/gpt-6-astra__low, F/s08/gpt-6-astra__high, F/s08/gpt-6-astra__low, F/s08/gpt-6.1-sol__high,
F/s09/gpt-6-astra__low, F/s09/gpt-6.1-sol__high, F/s10/claude-fable-5-1, F/s11/claude-haiku-5-5,
F/s11/claude-sonnet-5-5, F/s11/gpt-6-luna__high, F/s11/gpt-6.1-sol__high, F/s12/claude-sonnet-5-5,
F/s12/gpt-6-astra__low, F/s12/gpt-6-luna__high, F/s13/gpt-6-astra__high, F/s13/gpt-6-luna__low,
F/s15/gpt-6.1-sol__low, F/s16/gpt-6-luna__high, F/s17/claude-fable-5-1, F/s17/claude-opus-5-5,
F/s17/claude-sonnet-5-5, F/s18/claude-fable-5-1, F/s18/claude-haiku-5-5, F/s18/claude-sonnet-5-5,
F/s18/gpt-6-astra__low, F/s19/gpt-6-luna__low, F/s19/gpt-6.1-sol__low, S/medspa-aftercare/claude-haiku-5-5,
S/medspa-aftercare/gpt-6-luna__high, S/medspa-aftercare/gpt-6-luna__low, S/salon-welcome/claude-sonnet-5-5,
S/salon-welcome/gpt-6-luna__low, S/skin-winback/claude-haiku-5-5, S/spa-reminder/gpt-6-astra__low,
S/wellness-giftcard/gpt-6-astra__low, S/yoga-newsletter/gpt-6.1-sol__low.

By family: 33 GPT-6, 19 Claude 5.x, 0 Claude 4.x (only two Claude 4.x pairs are safe).

## Amendment 1, 9 November 2026, written after the E3 injection and before its judging

Clarifications of E3 made while implementing it, before any injected pair was judged:
- "Non-white" was implemented as HSL lightness at most 0.9; lighter colours are page backgrounds, not bands,
  and transparent or alpha backgrounds were skipped. An element that already had a background image was
  skipped. The darker stop is C with its HSL lightness multiplied by 0.78.
- 47 of the 52 sample pairs received the gradient (44 on a `td`, 2 on a `table`, 1 on a `div`). Five free-HTML
  emails have no block with a non-white background and are excluded, as the plan allowed: F/s06/gpt-6-astra__low,
  F/s07/gpt-6-astra__low, F/s08/gpt-6.1-sol__high, F/s09/gpt-6-astra__low, F/s15/gpt-6.1-sol__low.
- The re-audit of all 47 injected emails shows exactly two added feature slugs, `css-linear-gradient` and its
  carrier property `css-background-image`, no removed feature, the same visible word count, and
  `css-linear-gradient` now listed as an Outlook-Windows content risk. One email (F/s17/claude-fable-5-1)
  scrolls sideways on the phone render after injection as it did before.
- E1 and E4 were started on 8 November before this amendment; E6 was computed on 8 November. The E5 re-run
  was started on 8 November.

## Amendment 2, 12 November 2026: status before the paper's revision deadline

- E2 did not run. The rendering service's account was closed on 6 November and its data deleted, so the
  safe-pair renders in classic Outlook could not be made before the revision deadline (13 November). The
  Outlook result for the risky pairs therefore keeps the caveat that a general advantage of compiled MJML in
  that client cannot be ruled out.
- E7, the human panel, is open; no human answer has been recorded yet. It will be reported here when it closes.

## Amendment 3, 13 November 2026: interval type in E6, and how the token and cost saving is stated

- E6. The plan names 95% profile intervals for the regression coefficients. The script first published
  (`e6-baseline-regression.py`, 8 November) printed Wald intervals from the fitted model instead, and the
  article draft quoted those: risk odds ratio 7.4 [3.0, 18.0] for Opus and 5.0 [2.1, 11.5] for GPT. The script
  now computes profile-likelihood intervals and prints the Wald ones beside them: 7.4 [3.1, 18.9] and
  5.0 [2.2, 11.9]. Point estimates, p-values and the decision under the registered rule are unchanged (both
  intervals exclude an odds ratio of 1).
- Not part of the pre-registered tests, corrected in the article at the same time: the saving of the MJML
  arm was stated as 23% of output tokens and 22% of cost, obtained by inverting the mean per-pair HTML/MJML
  ratio (1.30 and 1.29). Summed over the 310 pairs the saving is 24% of output tokens and 27% of cost; the
  article now gives these totals next to the per-pair ratios. The mean per-pair saving is 17% for both.
