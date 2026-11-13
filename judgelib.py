"""Shared pieces for the pre-registered re-judging runs of 8 November 2026 (E1 warned judge, E3 injection,
E4 third judge): the same instruction, schema, tiling (desktop 700 px and phone 375 px, 1,500 px tiles, at most
six each) and both orders as the runner's Opus judge, judge-gpt.py and judge-degraded.py. All judges go through
OpenRouter; the key is read from email-platform/.env.local. Verdict files: <run>/<out_subdir>/<judge>/<brief>/<slug>.json
"""
import base64, concurrent.futures as cf, csv, io, json, os, random, re, socket, sys, threading, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = "<venv-site-packages>"
sys.path.insert(0, VENV); sys.path.insert(0, HERE)
from PIL import Image
import degrade

_gai = socket.getaddrinfo
socket.getaddrinfo = lambda *a, **k: [r for r in _gai(*a, **k) if r[0] == socket.AF_INET]
ENV = "<repo-root>/.env.local"
KEY = next(l.split("=", 1)[1].strip().strip('"') for l in open(ENV) if l.startswith("OPENROUTER_API_KEY="))
MODELS = {"gpt": "openai/gpt-6.1-sol", "opus": "anthropic/claude-opus-5.5", "gemini": "google/gemini-3.1-pro-preview"}
MAX_TOKENS = {"gpt": 4000, "opus": 16000, "gemini": 16000}
TILE, MAX_TILES = 1500, 6
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["A", "B", "preferred", "reason"],
          "properties": {k: {"type": "object", "additionalProperties": False, "required": ["design", "readability", "briefCoverage", "phone", "overall", "missing"],
                             "properties": {"design": {"type": "integer"}, "readability": {"type": "integer"}, "briefCoverage": {"type": "integer"}, "phone": {"type": "integer"}, "overall": {"type": "integer"}, "missing": {"type": "array", "items": {"type": "string"}}}}
                         for k in ("A", "B")} | {"preferred": {"type": "string", "enum": ["A", "B", "tie"]}, "reason": {"type": "string"}}}
GA = "<runs>"
RUNS = {"S": os.path.join(GA, "2026-10-09-raw-formats"), "F": os.path.join(GA, "2026-10-29-raw-formats-setF")}
PROMPTS = {"S": os.path.join(HERE, "prompts-setS.json"), "F": os.path.join(RUNS["F"], "prompts.json")}
RESULTS = {"S": os.path.join(HERE, "results-S.json"), "F": os.path.join(HERE, "results-F.json")}
PAIRS_CSV = "<data-repo>/data/pairs.csv"


def prompts():
    return {s: {x["id"]: x["prompt"] for x in json.load(open(f))} for s, f in PROMPTS.items()}


BASE = """Two marketing emails were made from the same brief for a small business. Judge them as the business owner deciding which one to send, and as a client reading it.

Brief:
\"\"\"
{brief}
\"\"\"
{extra}
Score each email from 1 (unusable) to 10 (excellent) on:
- design: does it look professional and fit this kind of business;
- readability: clear hierarchy, easy to scan, comfortable text;
- briefCoverage: does it include everything the brief asked for (list anything missing in "missing");
- phone: does the phone render work — nothing cut off, no sideways scrolling, readable text, tappable button;
- overall: which you would rather send, all things considered.

Neither email had real images: ignore broken or placeholder images and judge everything else. Both were rendered the same way, so don't guess how they were made. Then say which one you would send — "A", "B", or "tie" when you genuinely can't choose — and why, in one or two sentences."""


def instructions(brief, extra=""):
    return BASE.format(brief=brief, extra=("\n" + extra.strip() + "\n") if extra else "")


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


def risky_pairs():
    """The 52 risky pairs (degrade.risky_pairs), as {set, run, brief, slug, layout, content, flags}."""
    return degrade.risky_pairs([RESULTS["S"], RESULTS["F"]])


def safe_sample():
    """The 52-pair safe sample of preregistration-2026-11-08.md: seed 'renderer-bias-2026-11-08' over the sorted keys."""
    rows = list(csv.DictReader(open(PAIRS_CSV)))
    keys = sorted((r["set"], r["brief"], r["model"]) for r in rows if r["risky"] not in ("True", "true", "1"))
    sample = sorted(random.Random("renderer-bias-2026-11-08").sample(keys, 52))
    return [{"set": s, "run": RUNS[s], "brief": b, "slug": m} for s, b, m in sample]


def email_features():
    """(set, brief, combo) -> Outlook-Windows layout + content feature slugs and linter flags, from the results files."""
    out = {}
    for s, f in RESULTS.items():
        for e in json.load(open(f))["emails"]:
            if not e["ok"]: continue
            ow = e["clients"]["Outlook Windows"]
            out[(s, e["brief"], e["combo"])] = {"layout": ow["layout"], "content": ow["content"], "flags": e["pipeline_flags"]}
    return out


def pair_dirs(p, html_sub=None):
    html = os.path.join(p["run"], p["brief"], f"raw-html__{p['slug']}")
    if html_sub: html = os.path.join(html, html_sub)
    return {"mjml": os.path.join(p["run"], p["brief"], f"raw__{p['slug']}"), "html": html}


def judge_pair(judge, p, prompt, out_subdir, spend, extra_fn=None, html_sub=None, html_render="original"):
    out = os.path.join(p["run"], out_subdir, judge, p["brief"], f"{p['slug']}.json")
    if os.path.exists(out): return "skip", 0.0
    if spend.exhausted(): return "budget", 0.0
    dirs = pair_dirs(p, html_sub)
    for d in dirs.values():
        if not (os.path.exists(os.path.join(d, "screenshot.png")) and os.path.exists(os.path.join(d, "screenshot-phone.png"))): return "no screenshots " + d, 0.0
    orders, usages, cost = [], [], 0.0
    for a, b in (("mjml", "html"), ("html", "mjml")):
        extra = extra_fn(p, a, b) if extra_fn else ""
        err, structured = None, True
        for attempt in range(4):
            try:
                v, c, u = call(judge, [{"type": "text", "text": instructions(prompt, extra)}, *blocks("A", dirs[a]), *blocks("B", dirs[b])], structured)
                orders.append({"a": a, "b": b, **v}); usages.append(u); cost += c; spend.add(c); break
            except urllib.error.HTTPError as e:
                err = f"HTTP {e.code} {e.read()[:200]!r}"
                if e.code == 400 and structured: structured = False
                time.sleep(5 * (attempt + 1))
            except Exception as e:
                err = type(e).__name__ + ": " + str(e)[:200]
                time.sleep(5 * (attempt + 1))
        else:
            return "FAILED " + str(err), cost
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"promptId": p["brief"], "slug": p["slug"], "set": p["set"], "model": MODELS[judge], "judge": judge, "html_render": html_render,
               "instruction_extra": extra_fn(p, "mjml", "html") if extra_fn else "", "orders": orders, "usage": usages, "costUsd": cost}, open(out, "w"), indent=2)
    return "ok", cost


def run(judge, pairs, out_subdir, conc=4, budget=3.0, extra_fn=None, html_sub=None, html_render="original"):
    pr = prompts(); spend = Spend(budget); total, done = 0.0, 0
    with cf.ThreadPoolExecutor(conc) as ex:
        for p, (status, cost) in zip(pairs, ex.map(lambda p: judge_pair(judge, p, pr[p["set"]][p["brief"]], out_subdir, spend, extra_fn, html_sub, html_render), pairs)):
            total += cost; done += status == "ok"
            print(p["set"], p["brief"], p["slug"], status, f"${cost:.3f}", f"(total ${spend.total:.2f})", flush=True)
    print(f"{judge} {out_subdir}: done {done} of {len(pairs)} pairs, ${total:.2f} this run", flush=True)


def verdict(orders):
    """Stable verdict over the two orders: 'html', 'mjml' or 'split' (ties count as split)."""
    picks = []
    for o in orders:
        picks.append(None if o["preferred"] == "tie" else o[o["preferred"].lower()])
    return picks[0] if len(picks) == 2 and picks[0] == picks[1] and picks[0] else "split"


def load_verdicts(run_dir, out_subdir, judge):
    """{(brief, slug): verdict} for every verdict file of one run / subdir / judge."""
    out = {}
    base = os.path.join(run_dir, out_subdir, judge)
    for brief in (os.listdir(base) if os.path.isdir(base) else []):
        for f in os.listdir(os.path.join(base, brief)):
            if f.endswith(".json"):
                d = json.load(open(os.path.join(base, brief, f)))
                out[(brief, f[:-5])] = verdict(d["orders"])
    return out
