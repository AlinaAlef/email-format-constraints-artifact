"""Claims and coverage judge for the format comparison (raw HTML vs raw MJML), text only.

A judge sees the request the generator received and the email's visible text (extracted from the final
HTML; for MJML, the compiled HTML), and lists (1) factual claims the request does not support, flagging
placeholders, and (2) what the request asks the email to say or do, and whether it does. Two judges from
different vendors. Writes claims-judge/<set>/<judge>/<brief>__<combo>.json next to this script.

usage: python3 -I claims-judge-formats.py <set name> <run folder> <prompts json> [combo prefix,...]
  set S: prompts json = a list of {id, prompt} (exported from scripts/v3/prompts.ts); set F: prompts.json of the run.
"""
import json, os, re, sys, socket, html as htmlmod, urllib.request, concurrent.futures as cf
from html.parser import HTMLParser

_gai = socket.getaddrinfo
socket.getaddrinfo = lambda *a, **k: [r for r in _gai(*a, **k) if r[0] == socket.AF_INET]
ENV = "<home>/alpaca-relay/saas/next/email-platform/.env.local"
KEY = next(l.split("=", 1)[1].strip().strip('"') for l in open(ENV) if l.startswith("OPENROUTER_API_KEY="))
HERE = os.path.dirname(os.path.abspath(__file__))
JUDGES = {"opus-5.5": ("anthropic/claude-opus-5.5", None), "gpt-6.1-sol": ("openai/gpt-6.1-sol", "medium")}
INSTR = """You check a marketing email against the request the business sent. Return JSON only.

1. "invented": every factual claim in the email about the business, its offer or its customers that the request does not state or clearly imply. Examples: prices, discounts, deadlines, dates, opening hours, addresses, phone numbers, founding year, staff or founder names, locations, product or menu details, features, statistics, customer counts, ratings, testimonials, awards. Do not count generic marketing language, greetings, calls to action, legal footer boilerplate such as an unsubscribe line, or merge tags in curly braces. For each claim give "type": one of "offer", "business", "social proof", "product", "statistic", "other"; and "placeholder": true if it is obviously a stand-in the business must replace (such as "123 Main Street", "[Your address]", "Jane Doe"), else false.
2. "required": the things the request asks the email to say or do (its explicit content and purpose), each with "covered": true or false.

{"invented": [{"claim": "...", "type": "...", "placeholder": false}], "required": [{"item": "...", "covered": true}]}"""


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "title", "head"):
            self.skip += 1
        if tag in ("p", "div", "td", "tr", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table"):
            self.out.append("\n")
        if tag == "img":
            alt = dict(attrs).get("alt")
            if alt:
                self.out.append(f" [image: {alt}] ")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "title", "head") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def visible_text(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    raw = re.sub(r"<!--\[if[\s\S]*?<!\[endif\]-->", " ", raw, flags=re.I)  # MSO conditional blocks
    raw = re.sub(r"<!--[\s\S]*?-->", " ", raw)
    p = Text(); p.feed(raw)
    t = htmlmod.unescape("".join(p.out))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t.strip()


def job(set_name, jkey, brief, combo, request, html_path):
    out = os.path.join(HERE, "claims-judge", set_name, jkey, f"{brief}__{combo}.json")
    if os.path.exists(out):
        return "skip", 0.0
    text = visible_text(html_path)[:12000]
    model, effort = JUDGES[jkey]
    body = {"model": model, "max_tokens": 6000,
            "messages": [{"role": "user", "content": f"{INSTR}\n\nRequest sent by the business:\n{request}\n\nEmail text:\n{text}"}]}
    if effort:
        body["reasoning"] = {"effort": effort}
    err = None
    for _ in range(3):
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                         headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=600))
            v = json.loads(re.search(r"\{.*\}", r["choices"][0]["message"]["content"] or "", re.S).group(0))
            if not isinstance(v.get("invented"), list) or not isinstance(v.get("required"), list):
                raise ValueError("bad shape")
            res = {"set": set_name, "brief": brief, "combo": combo, "judge": model, **v,
                   "words": len(text.split()), "costUsd": float(r.get("usage", {}).get("cost") or 0)}
            os.makedirs(os.path.dirname(out), exist_ok=True)
            json.dump(res, open(out, "w"), indent=1)
            return "ok", res["costUsd"]
        except Exception as e:
            err = str(e)[:200]
    return "FAILED " + str(err), 0.0


def main():
    set_name, run, prompts_path = sys.argv[1:4]
    prefixes = sys.argv[4].split(",") if len(sys.argv) > 4 else ["raw__", "raw-html__"]
    prompts = {p["id"]: p["prompt"] for p in json.load(open(prompts_path))}
    jobs = []
    for brief in sorted(os.listdir(run)):
        if brief not in prompts:
            continue
        for combo in sorted(os.listdir(os.path.join(run, brief))):
            if not any(combo.startswith(p) for p in prefixes):
                continue
            html_path = os.path.join(run, brief, combo, "email.html")
            if not os.path.exists(html_path):
                continue
            for jkey in JUDGES:
                jobs.append((set_name, jkey, brief, combo, prompts[brief], html_path))
    total = 0.0
    with cf.ThreadPoolExecutor(8) as ex:
        for j, (status, cost) in zip(jobs, ex.map(lambda t: job(*t), jobs)):
            total += cost
            if status not in ("ok", "skip"):
                print(j[1], j[2], j[3], status, flush=True)
    print(f"done {len(jobs)} judgments, ${total:.2f}")


if __name__ == "__main__":
    main()
