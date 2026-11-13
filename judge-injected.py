"""E3 of preregistration-2026-11-08.md, judging step: re-judge the injected pairs (free-HTML email with the injected
gradient, rendered by render-degraded.mjs into <pair>/injected/) against the unchanged MJML opponent, same
instruction, schema, tiles and both orders. Writes <run>/judge-injected/<judge>/<brief>/<slug>.json.

usage: python3 -I judge-injected.py <gpt|opus> [concurrency=4] [budget usd=6]
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judgelib as J


def main():
    judge = sys.argv[1]
    conc = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    budget = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
    log = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "injected-log.json")))
    injected = {x["pair"] for x in log if x["injected"]}
    pairs = [p for p in J.safe_sample() if f"{p['set']}/{p['brief']}/{p['slug']}" in injected]
    print(f"{len(pairs)} injected pairs", flush=True)
    J.run(judge, pairs, "judge-injected", conc, budget, html_sub="injected", html_render="injected")


if __name__ == "__main__":
    main()
