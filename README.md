# Constrained by Design: anonymous re-analysis package

This package accompanies a paired comparison of LLM-generated free HTML and compiled MJML email, and screenshot judging across renderers. It contains records of 624 original generation attempts (622 successful emails, 310 complete pairs), the supplied analysis results and scripts, follow-up verdicts, and prospective follow-up plans with dated amendments.

## Run offline checks

Use Python 3.11 or later. Install `requirements-reanalysis.txt`, then run from this directory:

```bash
python3 verify-summary.py
python3 reproduce-statistics.py
python3 e6-baseline-regression.py
python3 pooled.py results-S.json results-F.json
python3 figures.py figures results-S.json results-F.json
```

The first command writes `verification-summary.json` and prints aggregate savings, Fisher tests and exploratory request-cluster bootstrap intervals. `reproduce-statistics.py` prints the paired Wilcoxon tests, marginal Cliff deltas and E6 profile intervals directly from JSON records. The E6 script reads derived CSVs in `data/` and prints profile and Wald intervals. The saved reference E6 output is `e6-baseline-regression.txt`. The original pair-bootstrap summary is `pooled.txt`. No API key, model call or rendering service is needed for these commands. The additional risk-plus-family diagnostic may warn about non-convergence; it illustrates the reported family collinearity and is not used as an estimable main effect. Tested package versions are pinned in the requirements file.

## Data and interpretation

`results-S.json` and `results-F.json` store per-email measures and pair verdicts; `prompts-setS.json` and `prompts-setF.json` contain fictional briefs and fact sheets. S has 144 attempts, F has 480. The two failed MJML compilations remain recorded; paired quality and cost estimates condition on success in both arms.

The pooled token means are 2,595 (HTML) and 1,975 (MJML); costs are $0.053 and $0.039. The aggregate saving, `1 - sum(MJML)/sum(HTML)` over complete pairs, is 24% for output tokens and 27% for cost. The mean of per-pair HTML/MJML ratios is separately 1.30 and 1.29; it is a different estimand.

`data/emails.csv` (622 rows) and `data/pairs.csv` (310 rows) are derived from the JSON records for portable E6 re-analysis. They do not substitute for primary generation logs. `results-degraded.json`, `degraded-removals.json`, `results-preflight.json`, `followups.csv`, `results-R.json`, `results-styled.json`, and their text reports document the interventions and follow-ups. P-values are nominal, two-sided and unadjusted across the registered questions. The pair-level analysis does not account for all dependence from reused briefs and configurations.

## Study sequence

The original format comparison, post-hoc risk split, feature-removal intervention and first real-client renders were exploratory. `preregistration-2026-11-08.md` specifies follow-ups and includes Amendments 1--3. E1, E3, E4, E5 and E6 ran. E2 (safe-pair Outlook controls) did not run. The initial E6 analysis printed Wald intervals; Amendment 3 adds the prospectively specified profile intervals without changing the point estimates. The main registration is included in full. `preregistration-e7-human-panel.md` registers a separate human panel; it is open, has no recorded answers yet, and is not reported in the paper.

## Re-analysis versus full replication

The package supports re-analysis of stored measurements and verdicts. It currently omits original HTML/MJML, rendered screenshots, the frozen Can I Email database and parts of the generation harness. The author reports retaining generated artifacts and judge outputs; raw API request/response logs are incomplete. Accordingly, the audit cannot be independently rerun against original markup from this package alone, and target screenshots cannot be visually verified here.

Other generation, rendering and judging scripts are archived for methodological inspection. They require original run directories, the support-database snapshot, appropriate dependencies and service credentials; placeholder paths must be configured. Do not interpret those scripts as a self-contained regeneration pipeline.

E6 controls do not resolve generator-family collinearity. Real-client results concern only the 52 risky pairs, and Outlook/Chrome capture extents differ. Unsupported CSS is an audited risk, not proof that every affected email visibly breaks. An audit-informed judge is not a replacement for a target-client render.

See `CHANGES-2026-11-13.md` for changes made while preparing this package.
