"""E4 of preregistration-2026-11-08.md: a third judge from a third vendor (Gemini 3.1 Pro preview via OpenRouter) on
the 52 risky pairs and the 52-pair safe sample, original browser screenshots, same instruction, schema, tiles and
both orders. Writes <run>/judge-gemini/gemini/<brief>/<slug>.json.

usage: python3 -I judge-third.py [risky|safe|both] [concurrency=3] [budget usd=25] [--test]  (--test judges one pair, one order, prints cost)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judgelib as J


def main():
    which = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "both"
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    conc = int(args[0]) if args else 3
    budget = float(args[1]) if len(args) > 1 else 25.0
    pairs = []
    if which in ("risky", "both"): pairs += [{"set": p["set"], "run": p["run"], "brief": p["brief"], "slug": p["slug"]} for p in J.risky_pairs()]
    if which in ("safe", "both"): pairs += J.safe_sample()
    if "--test" in sys.argv:
        p = pairs[0]; pr = J.prompts(); d = J.pair_dirs(p)
        v, c, u = J.call("gemini", [{"type": "text", "text": J.instructions(pr[p["set"]][p["brief"]])}, *J.blocks("A", d["mjml"]), *J.blocks("B", d["html"])])
        print("test pair", p["set"], p["brief"], p["slug"], "| preferred", v["preferred"], "| cost $%.4f" % c, "| usage", u); return
    J.run("gemini", pairs, "judge-gemini", conc, budget)


if __name__ == "__main__":
    main()
