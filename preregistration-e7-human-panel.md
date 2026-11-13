# Pre-registration E7: a human panel on the 52 risky pairs, written before the panel opened

Companion to `preregistration-2026-11-08.md`. Committed before any participant saw the page.

## Question

When people, rather than model judges, choose between the two emails of a risky pair, does the choice depend on
whether they see the pair as a Chrome render or as a classic-Outlook render?

## Material

The 52 risky pairs (free-HTML email with an Outlook-Windows layout or content feature, or a linter flag).
For each pair, four Preflight renders from October 2026: the free-HTML and the MJML email, each in desktop
Chrome and in classic Outlook for Windows (the same images the model judges saw in the target-render
pass; the Outlook capture shows the top of the reading pane, the Chrome capture the full email). Images are
resized to 720 px wide and served under opaque names. Within a pair the letters A and B are assigned to the
two formats once, at random (seed in the build script), and kept for every participant and both clients.

## Procedure

Each participant gets 10 pairs drawn at random from the 52, seeded by a participant id, 5 shown as Chrome
renders and 5 as Outlook renders, in random order. The page says both emails "were opened in the same email
program and photographed" and does not name the program. Per pair the participant answers "Which email would
you send?" (A, B, can't choose) and, optionally, "Does anything look broken or missing?" (A, B, neither).
A background field (designer, marketer, business owner, developer, other) is optional. Answers are stored per
participant with the pair id and the client condition.

Recruitment: people the author asks directly (colleagues, designers, small-business owners), not a paid
crowd; no personal data beyond the optional background. The panel closes after 30 participants or 14 days
from opening, whichever is first; participants with fewer than 5 answered pairs are excluded; a participant
id that appears twice is counted once.

## Outcomes and tests

Primary: the share of answers choosing the free-HTML email, by client. H7: the share is higher under Chrome
than under Outlook. Test: for each pair with at least one answer under each client, the difference between
its Chrome share and its Outlook share; Wilcoxon signed-rank test across pairs, two-sided, alpha 0.05, and
the pooled shares with Wilson 95% intervals. Secondary: a mixed logistic regression of "chose free HTML" on
client with a random intercept per pair and per participant, if the sample allows it; the share of "broken"
reports for the free-HTML email by client; agreement between the participants' majority choice per pair and
condition and the two model judges' verdicts in the same condition.

Decision rule: a Chrome share above the Outlook share with p < 0.05 supports the model-judge result; no
difference or the reverse is reported as a limit of the model-judge result. The panel's size gives it
modest power; it is reported as a pilot if fewer than 20 participants finish.

Reporting: whatever the outcome, in the article's revision if it closes before the deadline, otherwise in
this repository with the per-answer data (participant id replaced by a sequence number).
