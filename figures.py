#!/usr/bin/env python3
"""Figures for the format-constraints article, from results-<set>.json files (pooled) and the run folders.

usage: <venv python> figures.py <out dir> <results json>... [--sheet <run folder>]
  fig1-pairs.png      contact sheet: one brief, three models, HTML (left) vs MJML (right), first screen
  fig2-risk.png       share of emails with an unsupported layout / content feature outside @media, by client
  fig3-models.png     per model: output tokens HTML vs MJML (dumbbell) and the judge's verdicts (stacked bar)
Palette: dataviz reference instance (HTML = slot 1 blue, MJML = slot 2 orange, split = muted gray); validated.
"""
import json, os, sys, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
from PIL import Image, ImageDraw, ImageFont

HTML, MJML, SPLIT = "#2a78d6", "#eb6834", "#898781"
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
rcParams.update({"font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"], "font.size": 10,
                 "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": INK2,
                 "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                 "savefig.facecolor": SURFACE, "axes.titlecolor": INK, "axes.titleweight": "bold", "axes.titlesize": 11})
CLIENTS = ["Outlook Windows", "Gmail web", "Gmail iOS", "Gmail Android", "Outlook.com", "Yahoo web", "Apple Mail iOS"]
MODEL_LABEL = {"claude-opus-5-5": "Claude Opus 5.5", "claude-sonnet-5-5": "Claude Sonnet 5.5", "claude-fable-5-1": "Claude Fable 5.1",
               "claude-haiku-5-5": "Claude Haiku 5.5", "claude-sonnet-4-6": "Claude Sonnet 4.6", "claude-haiku-4-5": "Claude Haiku 4.5",
               "gpt-6.1-sol__high": "GPT-6.1 Sol (high)", "gpt-6.1-sol__low": "GPT-6.1 Sol (low)", "gpt-6-astra__high": "GPT-6 Astra (high)",
               "gpt-6-astra__low": "GPT-6 Astra (low)", "gpt-6-luna__high": "GPT-6 Luna (high)", "gpt-6-luna__low": "GPT-6 Luna (low)"}
ORDER = list(MODEL_LABEL)


def load(files):
    emails, pairs = [], []
    for f in files:
        d = json.load(open(f))
        s = d["summary"]["set"]
        ok = [e | {"set": s} for e in d["emails"] if e["ok"]]
        emails += ok
        by = {(e["brief"], e["combo"]): e for e in ok}
        for (b, c), e in by.items():
            if c.startswith("raw-html__"):
                m = by.get((b, "raw__" + e["slug"]))
                if m: pairs.append({"set": s, "brief": b, "slug": e["slug"], "html": e, "mjml": m})
    return emails, pairs


def fig_risk(emails, out):
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, cls, title in zip(axes, ("layout", "content"), ("Layout feature the client drops", "Content-bearing feature the client drops")):
        ys = list(range(len(CLIENTS)))[::-1]
        for y, cl in zip(ys, CLIENTS):
            vals = {}
            for fmt, col in (("html", HTML), ("mjml", MJML)):
                xs = [e for e in emails if e["format"] == fmt]
                vals[fmt] = 100 * sum(1 for e in xs if e["clients"][cl][cls]) / len(xs)
            ax.plot([vals["mjml"], vals["html"]], [y, y], color=GRID, lw=2, zorder=1)
            ax.scatter([vals["html"]], [y], s=64, color=HTML, zorder=3, edgecolor=SURFACE, lw=1)
            ax.scatter([vals["mjml"]], [y], s=64, color=MJML, zorder=3, edgecolor=SURFACE, lw=1)
            ax.text(vals["html"] + 1.2, y + 0.18, f"{vals['html']:.0f}%", color=INK2, fontsize=8.5, va="bottom")
            ax.text(vals["mjml"] - 1.2, y - 0.18, f"{vals['mjml']:.0f}%", color=INK2, fontsize=8.5, va="top", ha="right")
        ax.set_yticks(ys); ax.set_yticklabels(CLIENTS)
        ax.set_xlim(-2, max(16, ax.get_xlim()[1])); ax.set_xlabel("share of emails, %", color=INK2)
        ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True); ax.set_title(title, loc="left")
    n_h = sum(1 for e in emails if e["format"] == "html"); n_m = sum(1 for e in emails if e["format"] == "mjml")
    fig.legend(handles=[plt.Line2D([], [], marker="o", color=HTML, ls="", ms=8, label=f"free HTML (n = {n_h})"),
                        plt.Line2D([], [], marker="o", color=MJML, ls="", ms=8, label=f"MJML, compiled (n = {n_m})")],
               loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig(out, dpi=200); plt.close(fig)


def fig_models(emails, pairs, out):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.6), gridspec_kw={"width_ratios": [1.15, 1]})
    slugs = [s for s in ORDER if any(e["slug"] == s for e in emails)]
    ys = list(range(len(slugs)))[::-1]
    for y, s in zip(ys, slugs):
        v = {}
        for fmt, col in (("html", HTML), ("mjml", MJML)):
            xs = [e["out_tokens"] for e in emails if e["slug"] == s and e["format"] == fmt]
            v[fmt] = sum(xs) / len(xs)
        ax1.plot([v["mjml"], v["html"]], [y, y], color=GRID, lw=2, zorder=1)
        ax1.scatter([v["html"]], [y], s=56, color=HTML, zorder=3, edgecolor=SURFACE); ax1.scatter([v["mjml"]], [y], s=56, color=MJML, zorder=3, edgecolor=SURFACE)
    ax1.set_yticks(ys); ax1.set_yticklabels([MODEL_LABEL[s] for s in slugs]); ax1.set_xlabel("mean output tokens per email", color=INK2)
    ax1.grid(axis="x", color=GRID, lw=0.6); ax1.set_axisbelow(True); ax1.set_title("Output tokens", loc="left"); ax1.set_xlim(0)
    # judge verdicts
    for y, s in zip(ys, slugs):
        c = collections.Counter(p["judge_consistent"] for p in pairs if p["slug"] == s and p.get("judge_consistent"))
        n = sum(c.values()) or 1
        left = 0
        for key, col in (("html", HTML), ("split", SPLIT), ("mjml", MJML)):
            w = 100 * c.get(key, 0) / n
            if w: ax2.barh(y, w, left=left, color=col, height=0.62, edgecolor=SURFACE, lw=1.5)
            if w >= 12: ax2.text(left + w / 2, y, f"{c.get(key, 0)}", ha="center", va="center", color="#ffffff" if key != "split" else INK, fontsize=8)
            left += w
    ax2.set_yticks(ys); ax2.set_yticklabels([]); ax2.set_xlim(0, 100); ax2.set_xlabel("pairs, % (numbers = pairs)", color=INK2)
    ax2.set_title("Blind judge: which email it would send", loc="left")
    ax2.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=HTML, label="HTML in both orders"), plt.Rectangle((0, 0), 1, 1, color=SPLIT, label="depends on order"),
                        plt.Rectangle((0, 0), 1, 1, color=MJML, label="MJML in both orders")], loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=3, frameon=False, fontsize=8.5)
    ax1.legend(handles=[plt.Line2D([], [], marker="o", color=HTML, ls="", ms=7, label="free HTML"), plt.Line2D([], [], marker="o", color=MJML, ls="", ms=7, label="MJML")],
               loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=2, frameon=False, fontsize=8.5)
    fig.tight_layout(); fig.savefig(out, dpi=200); plt.close(fig)


def fig_sheet(run, brief, slugs, out, crop=900, scale=0.5):
    cols, rows = 2, len(slugs)
    w = int(700 * scale); h = int(crop * scale); pad = 14; head = 26; side = 150
    sheet = Image.new("RGB", (side + cols * (w + pad) + pad, head + rows * (h + pad) + pad), "#fcfcfb")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15); small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    except Exception:
        font = small = ImageFont.load_default()
    draw.text((side + pad, 6), "free HTML", fill=HTML, font=font); draw.text((side + pad + w + pad, 6), "MJML, compiled", fill=MJML, font=font)
    for r, s in enumerate(slugs):
        y = head + pad + r * (h + pad)
        draw.text((pad, y + 4), MODEL_LABEL.get(s, s), fill=INK, font=small)
        for c, prefix in enumerate(("raw-html__", "raw__")):
            p = os.path.join(run, brief, prefix + s, "screenshot.png")
            im = Image.open(p).convert("RGB"); im = im.crop((0, 0, 700, min(crop, im.height))); im = im.resize((w, int(im.height * scale)), Image.LANCZOS)
            x = side + pad + c * (w + pad)
            sheet.paste(im, (x, y)); draw.rectangle([x - 1, y - 1, x + w, y + im.height], outline="#e1e0d9")
    sheet.save(out)


def main():
    args = sys.argv[1:]
    out_dir = args[0]; os.makedirs(out_dir, exist_ok=True)
    sheet_run = args[args.index("--sheet") + 1] if "--sheet" in args else None
    files = [a for a in args[1:] if a.endswith(".json")]
    emails, pairs = load(files)
    judge = {}
    for f in files:
        d = json.load(open(f))
        for p in d.get("pairs", []):
            judge[(d["summary"]["set"], p["brief"], p["slug"])] = p["judge_consistent"]
    for p in pairs:
        p["judge_consistent"] = judge.get((p["set"], p["brief"], p["slug"]))
    fig_risk(emails, os.path.join(out_dir, "fig2-risk.png"))
    fig_models(emails, pairs, os.path.join(out_dir, "fig3-models.png"))
    if sheet_run:
        fig_sheet(sheet_run, "s17", ["claude-sonnet-5-5", "gpt-6.1-sol__high", "claude-haiku-4-5"], os.path.join(out_dir, "fig1-pairs.png"))
    print("written", sorted(os.listdir(out_dir)))


if __name__ == "__main__":
    main()
