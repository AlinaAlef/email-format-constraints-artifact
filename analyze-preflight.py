"""Verdicts on the 52 risky pairs from real-client renders (Preflight, desktop only): Chrome vs classic Outlook, both judges.
usage: python3 -I analyze-preflight.py -> results-preflight.json + printed table"""
import json, os, sys, glob, math, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import degrade
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__))
pairs = degrade.risky_pairs([os.path.join(HERE, 'results-S.json'), os.path.join(HERE, 'results-F.json')])
def verdict(f):
    d = json.load(open(f)); w = []
    for o in d['orders']:
        p = o['preferred']; w.append('tie' if p == 'tie' else (o['a'] if p == 'A' else o['b']))
    v = w[0] if w[0] == w[1] and w[0] != 'tie' else 'split'
    sc = {fmt: {s: sum((o['A'] if o['a'] == fmt else o['B'])[s] for o in d['orders']) / 2 for s in ('design', 'readability', 'briefCoverage', 'overall')} for fmt in ('html', 'mjml')}
    reasons = ' '.join(o['reason'] for o in d['orders'])
    return v, sc, reasons, d.get('costUsd', 0)
out = {}; per = collections.defaultdict(dict)
for judge in ('opus', 'gpt'):
    for render in ('chrome', 'outlook'):
        vs = []; cost = 0
        for p in pairs:
            f = os.path.join(p['run'], 'judge-preflight-' + render, judge, p['brief'], p['slug'] + '.json')
            v, sc, rs, c = verdict(f); vs.append(v); cost += c; per[(p['set'], p['brief'], p['slug'])][(judge, render)] = (v, sc, rs)
        cnt = collections.Counter(vs)
        out[f'{judge}-{render}'] = {'html': cnt['html'], 'mjml': cnt['mjml'], 'split': cnt['split'], 'html_share': cnt['html'] / len(vs), 'cost': round(cost, 2),
                                    'overall_diff': sum(per[k][(judge, render)][1]['html']['overall'] - per[k][(judge, render)][1]['mjml']['overall'] for k in per) / len(per)}
    # McNemar on HTML-wins, chrome vs outlook
    b = sum(1 for k in per if per[k][(judge, 'chrome')][0] == 'html' and per[k][(judge, 'outlook')][0] != 'html')
    c = sum(1 for k in per if per[k][(judge, 'chrome')][0] != 'html' and per[k][(judge, 'outlook')][0] == 'html')
    out[f'{judge}-mcnemar'] = {'chrome_only': b, 'outlook_only': c, 'p': stats.binomtest(min(b, c), b + c, 0.5).pvalue if b + c else 1.0}
    # paired overall diff change
    ch = [per[k][(judge, 'outlook')][1]['html']['overall'] - per[k][(judge, 'outlook')][1]['mjml']['overall'] - (per[k][(judge, 'chrome')][1]['html']['overall'] - per[k][(judge, 'chrome')][1]['mjml']['overall']) for k in per]
    out[f'{judge}-diffchange'] = {'mean': sum(ch) / len(ch), 'wilcoxon_p': stats.wilcoxon(ch).pvalue if any(ch) else 1.0}
    # vs safe baseline
    safe = {'opus': (101, 113 + 44), 'gpt': (98, 121 + 39)}[judge]
    o = out[f'{judge}-outlook']
    out[f'{judge}-outlook-vs-safe'] = stats.fisher_exact([[o['html'], o['mjml'] + o['split']], [safe[0], safe[1]]])[1]
    words = collections.Counter()
    for k in per:
        rs = per[k][(judge, 'outlook')][2].lower()
        for w in ('missing', 'invisible', 'unreadable', 'broken', 'white text', 'blank', 'polished', 'card'): words[w] += rs.count(w)
    out[f'{judge}-outlook-words'] = dict(words)
json.dump(out, open(os.path.join(HERE, 'results-preflight.json'), 'w'), indent=1)
for k, v in out.items(): print(k, v)
