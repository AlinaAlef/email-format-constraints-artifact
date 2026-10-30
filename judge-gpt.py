"""Second blind pairwise judge, from another vendor: GPT-6.1 Sol via OpenRouter, same instructions and
scoring schema as the Opus judge in the runner, same screenshots (desktop 700 px and phone 375 px, tiled
1,500 px high, at most 6 tiles each), both orders. Writes <run>/judge-gpt/<brief>/<slug>.json.

usage: python3 -I judge-gpt.py <run folder> <prompts json> [concurrency]
"""
import json, os, re, sys, io, base64, socket, urllib.request, concurrent.futures as cf
from PIL import Image

_gai = socket.getaddrinfo
socket.getaddrinfo = lambda *a, **k: [r for r in _gai(*a, **k) if r[0] == socket.AF_INET]
ENV = "<home>/alpaca-relay/saas/next/email-platform/.env.local"
KEY = next(l.split("=", 1)[1].strip().strip('"') for l in open(ENV) if l.startswith("OPENROUTER_API_KEY="))
MODEL = "openai/gpt-6.1-sol"
TILE, MAX_TILES = 1500, 6
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["A", "B", "preferred", "reason"],
          "properties": {k: {"type": "object", "additionalProperties": False, "required": ["design", "readability", "briefCoverage", "phone", "overall", "missing"],
                             "properties": {"design": {"type": "integer"}, "readability": {"type": "integer"}, "briefCoverage": {"type": "integer"}, "phone": {"type": "integer"}, "overall": {"type": "integer"}, "missing": {"type": "array", "items": {"type": "string"}}}}
                         for k in ("A", "B")} | {"preferred": {"type": "string", "enum": ["A", "B", "tie"]}, "reason": {"type": "string"}}}


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


def call(content):
    body = {"model": MODEL, "max_tokens": 4000, "reasoning": {"effort": "medium"},
            "messages": [{"role": "user", "content": content}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "verdict", "strict": True, "schema": SCHEMA}}}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=600))
    text = r["choices"][0]["message"]["content"] or ""
    v = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    return v, float(r.get("usage", {}).get("cost") or 0)


def job(run, brief, slug, prompt):
    out = os.path.join(run, "judge-gpt", brief, f"{slug}.json")
    if os.path.exists(out): return "skip", 0.0
    dirs = {"mjml": os.path.join(run, brief, f"raw__{slug}"), "html": os.path.join(run, brief, f"raw-html__{slug}")}
    for d in dirs.values():
        if not (os.path.exists(os.path.join(d, "screenshot.png")) and os.path.exists(os.path.join(d, "screenshot-phone.png"))): return "no screenshots", 0.0
    orders, cost = [], 0.0
    for a, b in (("mjml", "html"), ("html", "mjml")):
        err = None
        for _ in range(3):
            try:
                v, c = call([{"type": "text", "text": instructions(prompt)}, *blocks("A", dirs[a]), *blocks("B", dirs[b])])
                orders.append({"a": a, "b": b, **v}); cost += c; break
            except Exception as e:
                err = str(e)[:200]
        else:
            return "FAILED " + str(err), cost
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"promptId": brief, "slug": slug, "model": MODEL, "orders": orders, "costUsd": cost}, open(out, "w"), indent=2)
    return "ok", cost


def main():
    run, prompts_path = sys.argv[1:3]
    conc = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    prompts = {p["id"]: p["prompt"] for p in json.load(open(prompts_path))}
    jobs = []
    for brief in sorted(os.listdir(run)):
        if brief not in prompts: continue
        for combo in sorted(os.listdir(os.path.join(run, brief))):
            if combo.startswith("raw-html__"):
                jobs.append((run, brief, combo.split("__", 1)[1], prompts[brief]))
    total = 0.0; done = 0
    with cf.ThreadPoolExecutor(conc) as ex:
        for j, (status, cost) in zip(jobs, ex.map(lambda t: job(*t), jobs)):
            total += cost; done += status == "ok"
            if status not in ("ok", "skip"): print(j[1], j[2], status, flush=True)
    print(f"done {done} of {len(jobs)} pairs, ${total:.2f}", flush=True)


if __name__ == "__main__":
    main()
