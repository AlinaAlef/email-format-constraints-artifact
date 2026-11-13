import json, pathlib, collections, numpy as np
from scipy.stats import fisher_exact, binomtest
root=pathlib.Path(__file__).resolve().parent
pairs=[]
for s in ['S','F']:
 d=json.load(open(root/f'results-{s}.json'))
 by={(e['brief'],e['combo']):e for e in d['emails'] if e['ok']}
 for p in d['pairs']:
  h=by.get((p['brief'],'raw-html__'+p['slug']));m=by.get((p['brief'],'raw__'+p['slug']))
  if h and m:pairs.append(dict(p,set=s,h=h,m=m))
rng=np.random.default_rng(20261113)
out={}
for metric in ['out_tokens','cost']:
 h=np.array([p['h'][metric] for p in pairs]);m=np.array([p['m'][metric] for p in pairs])
 out[metric]={'HTML_mean':float(h.mean()),'MJML_mean':float(m.mean()),'ratio_of_means':float(h.mean()/m.mean()),'aggregate_saving':float(1-m.mean()/h.mean()),'mean_HTML_over_MJML':float((h/m).mean()),'mean_paired_saving':float((1-m/h).mean())}
 # resample request clusters, preserving all configurations within a brief
 groups=[np.array([i for i,p in enumerate(pairs) if (p['set'],p['brief'])==k]) for k in sorted({(p['set'],p['brief']) for p in pairs})]
 vals=[]
 for _ in range(4000):
  ix=np.concatenate([groups[i] for i in rng.integers(0,len(groups),len(groups))]);vals.append((h[ix]-m[ix]).mean())
 out[metric]['request_cluster_difference_CI']=np.quantile(vals,[.025,.975]).tolist()
for j in ['judge_consistent','judge_gpt_consistent']:
 for decided in [True,False]:
  tab=[]
  for risk in [True,False]:
   ps=[p for p in pairs if bool(p['h']['clients']['Outlook Windows']['layout'] or p['h']['clients']['Outlook Windows']['content'] or p['h']['pipeline_flags'])==risk]
   tab.append([sum(p[j]=='html' for p in ps),sum((p[j]=='mjml' if decided else p[j]!='html') for p in ps)])
  r=fisher_exact(tab);out[j+('_decided' if decided else '_all')]={'table':tab,'OR':float(r.statistic),'p':float(r.pvalue)}
(root/'verification-summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
