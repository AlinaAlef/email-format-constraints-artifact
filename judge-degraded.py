"""Re-judge the 52 risky pairs with the HTML arm's DEGRADED render (degrade.py + render-degraded.mjs) against the
MJML arm's original render: same instruction, schema, tiling (desktop 700 px and phone 375 px, 1,500 px tiles,
at most 6 each) and both orders as the runner's Opus judge and judge-gpt.py. Both judges go through OpenRouter:
GPT-6.1 Sol (openai/gpt-6.1-sol) and Claude Opus 5.5 (anthropic/claude-opus-5.5), reasoning effort medium.
Writes <run>/judge-degraded/<judge>/<brief>/<slug>.json; skips pairs already judged; stops submitting new pairs
once the spend reported by OpenRouter passes the budget.

usage: python3 -I judge-degraded.py <gpt|opus> [concurrency=4] [budget usd=3]
"""
import json, os, re, sys, io, base64, socket, time, threading, urllib.request, urllib.error, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from PIL import Image
import degrade

_gai = socket.getaddrinfo
socket.getaddrinfo = lambda *a, **k: [r for r in _gai(*a, **k) if r[0] == socket.AF_INET]
ENV = "<home>/alpaca-relay/saas/next/email-platform/.env.local"
KEY = next(l.split("=", 1)[1].strip().strip('"') for l in open(ENV) if l.startswith("OPENROUTER_API_KEY="))
MODELS = {"gpt": "openai/gpt-6.1-sol", "opus": "anthropic/claude-opus-5.5"}
MAX_TOKENS = {"gpt": 4000, "opus": 16000}   # judge-gpt.py used 4,000; the runner gave Opus 16,000
TILE, MAX_TILES = 1500, 6
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["A", "B", "preferred", "reason"],
          "properties": {k: {"type": "object", "additionalProperties": False, "required": ["design", "readability", "briefCoverage", "phone", "overall", "missing"],
                             "properties": {"design": {"type": "integer"}, "readability": {"type": "integer"}, "briefCoverage": {"type": "integer"}, "phone": {"type": "integer"}, "overall": {"type": "integer"}, "missing": {"type": "array", "items": {"type": "string"}}}}
                         for k in ("A", "B")} | {"preferred": {"type": "string", "enum": ["A", "B", "tie"]}, "reason": {"type": "string"}}}
PROMPTS = {"S": os.path.join(HERE, "prompts-setS.json"),
           "F": "<repo>/research/generation-approaches/2026-10-29-raw-formats-setF/prompts.json"}


def instructions(brief):
    return f"""Two marketing emails were made from the same brief for a small business. Judge them as the business owner deciding which one to send, and as a client reading it.

Brief:
\"\"\"
{brief}
\"\"\"

Score each email from 1 (unusable) to 10 (excellent) on:
- design: does it look professional and fit this kind of business;
- readability: clear hierarchy, easy to scan, comfortable text;
- briefCoverage: does it include everything the brief asked for (list anything missing in "missing");
- phone: does the phone render work — nothing cut off, no sideways scrolling, readable text, tappable button;
- overall: which you would rather send, all things considered.

Neither email had real images: ignore broken or placeholder images and judge everything else. Both were rendered the same way, so don't guess how they were made. Then say which one you would send — "A", "B", or "tie" when you genuinely can't choose — and why, in one or two sentences."""


def tiles(png):
    im = Image.open(png).convert("RGB")
    out = []
    for top in range(0, im.height, TILE):
        if len(out) >= MAX_TILES: break
        buf = io.BytesIO(); im.crop((0, top, im.width, min(top + TILE, im.height))).save(buf, "PNG", optimize=True)
        out.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}})
    return out


def blocks(label, d):
    desk, phone = tiles(os.path.join(d, "screenshot.png")), tiles(os.path.join(d, "screenshot-phone.png"))
    return [{"type": "text", "text": f"Email {label} on desktop (700 px wide), {len(desk)} part(s), top to bottom:"}, *desk,
            {"type": "text", "text": f"Email {label} on a phone (375 px wide), {len(phone)} part(s), top to bottom:"}, *phone]


class Spend:
    def __init__(self, budget):
        self.budget, self.total, self.lock = budget, 0.0, threading.Lock()

    def add(self, c):
        with self.lock: self.total += c

    def exhausted(self):
        with self.lock: return self.total >= self.budget


def call(judge, content, structured=True):
    body = {"model": MODELS[judge], "max_tokens": MAX_TOKENS[judge], "reasoning": {"effort": "medium"},
            "messages": [{"role": "user", "content": content}], "usage": {"include": True}}
    if structured:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "verdict", "strict": True, "schema": SCHEMA}}
    else:
        body["messages"][0]["content"] = content + [{"type": "text", "text": "Answer with one JSON object only, no prose around it, with this schema: " + json.dumps(SCHEMA)}]
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=900))
    if "error" in r: raise RuntimeError(str(r["error"])[:300])
    text = r["choices"][0]["message"]["content"] or ""
    v = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    for k in ("A", "B"):
        for s in ("design", "readability", "briefCoverage", "phone", "overall"): v[k][s] = int(v[k][s])
    assert v["preferred"] in ("A", "B", "tie")
    u = r.get("usage", {})
    return v, float(u.get("cost") or 0), {"prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                                          "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens")}


def job(judge, p, prompt, spend):
    run = p["run"]; brief, slug = p["brief"], p["slug"]
    out = os.path.join(run, "judge-degraded", judge, brief, f"{slug}.json")
    if os.path.exists(out): return "skip", 0.0
    if spend.exhausted(): return "budget", 0.0
    dirs = {"mjml": os.path.join(run, brief, f"raw__{slug}"), "html": os.path.join(run, brief, f"raw-html__{slug}", "degraded")}
    for d in dirs.values():
        if not (os.path.exists(os.path.join(d, "screenshot.png")) and os.path.exists(os.path.join(d, "screenshot-phone.png"))): return "no screenshots " + d, 0.0
    orders, usages, cost = [], [], 0.0
    for a, b in (("mjml", "html"), ("html", "mjml")):
        err, structured = None, True
        for attempt in range(4):
            try:
                v, c, u = call(judge, [{"type": "text", "text": instructions(prompt)}, *blocks("A", dirs[a]), *blocks("B", dirs[b])], structured)
                orders.append({"a": a, "b": b, **v}); usages.append(u); cost += c; spend.add(c); break
            except urllib.error.HTTPError as e:
                err = f"HTTP {e.code} {e.read()[:200]!r}"
                if e.code == 400 and structured: structured = False   # model without structured output: ask for JSON in the prompt
                time.sleep(5 * (attempt + 1))
            except Exception as e:
                err = type(e).__name__ + ": " + str(e)[:200]
                time.sleep(5 * (attempt + 1))
        else:
            return "FAILED " + str(err), cost
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"promptId": brief, "slug": slug, "set": p["set"], "model": MODELS[judge], "judge": judge, "html_render": "degraded",
               "orders": orders, "usage": usages, "costUsd": cost}, open(out, "w"), indent=2)
    return "ok", cost


def main():
    judge = sys.argv[1]
    conc = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    budget = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    prompts = {s: {x["id"]: x["prompt"] for x in json.load(open(f))} for s, f in PROMPTS.items()}
    pairs = degrade.risky_pairs([os.path.join(HERE, "results-S.json"), os.path.join(HERE, "results-F.json")])
    spend = Spend(budget)
    total, done = 0.0, 0
    with cf.ThreadPoolExecutor(conc) as ex:
        for p, (status, cost) in zip(pairs, ex.map(lambda p: job(judge, p, prompts[p["set"]][p["brief"]], spend), pairs)):
            total += cost; done += status == "ok"
            print(p["set"], p["brief"], p["slug"], status, f"${cost:.3f}", f"(total ${spend.total:.2f})", flush=True)
    print(f"{judge}: done {done} of {len(pairs)} pairs, ${total:.2f} this run", flush=True)


if __name__ == "__main__":
    main()
