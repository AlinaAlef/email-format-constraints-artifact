"""Export the pre-registered follow-up verdicts (E1, E3, E4) to renderer-bias-data/data/followups.csv: one row per pair
in the 52 risky pairs or the 52-pair safe sample, with the stable verdict (html / mjml / split) of every run.
usage: venv/bin/python -I export-followups.py"""
import csv, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import judgelib as J

rows = {(r["set"], r["brief"], r["model"]): r for r in csv.DictReader(open(J.PAIRS_CSV))}
risky = [(p["set"], p["brief"], p["slug"]) for p in J.risky_pairs()]
safe = [(p["set"], p["brief"], p["slug"]) for p in J.safe_sample()]
inj = json.load(open(os.path.join(HERE, "injected-log.json"))); injected = {x["pair"]: x for x in inj}


def verdicts(subdir, judge):
    out = {}
    for s, run in J.RUNS.items():
        out.update({(s, b, m): v for (b, m), v in J.load_verdicts(run, subdir, judge).items()})
    return out


cols = {"opus_warned_generic": verdicts("judge-warned-generic", "opus"), "opus_warned_specific": verdicts("judge-warned-specific", "opus"),
        "gpt_warned_generic": verdicts("judge-warned-generic", "gpt"), "gpt_warned_specific": verdicts("judge-warned-specific", "gpt"),
        "opus_injected": verdicts("judge-injected", "opus"), "gpt_injected": verdicts("judge-injected", "gpt"),
        "gemini_browser": verdicts("judge-gemini", "gemini")}
out = os.path.join(os.path.dirname(J.PAIRS_CSV), "followups.csv")
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["set", "brief", "model", "risky", "sample", "opus_browser", "gpt_browser", *cols, "injected", "injected_tag", "injected_colour"])
    for sample, keys in (("risky", risky), ("safe", safe)):
        for k in keys:
            r = rows[k]; key = "/".join(k); ij = injected.get(key, {})
            w.writerow([*k, r["risky"], sample, r["opus_verdict"], r["gpt_verdict"], *[c.get(k, "") for c in cols.values()],
                        "" if sample == "risky" else str(bool(ij.get("injected"))), ij.get("tag", ""), ij.get("colour", "")])
n = sum(1 for _ in open(out)) - 1
print(f"wrote {out}: {n} rows")
