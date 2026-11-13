import json,pathlib,sys,numpy as np
from scipy.stats import wilcoxon,pearsonr
from scipy.optimize import brentq
import statsmodels.api as sm
root=pathlib.Path(__file__).parent
pairs=[]
for st in ['S','F']:
 d=json.loads((root/f'results-{st}.json').read_text())
 by={(e['brief'],e['combo']):e for e in d['emails'] if e['ok']}
 for p in d['pairs']:
  h=by[(p['brief'],'raw-html__'+p['slug'])];m=by[(p['brief'],'raw__'+p['slug'])]
  pairs.append(p|{'set':st,'html':h,'mjml':m})
for key in ['words','out_tokens','cost']:
 h=np.array([p['html'][key] for p in pairs]);m=np.array([p['mjml'][key] for p in pairs]);print(key,'p',wilcoxon(h,m).pvalue,'delta',np.sign(h[:,None]-m[None,:]).mean())
for judge in ['opus-5.5','gpt-6.1-sol']:
 for key in ['coverage','invented_real','placeholders']:
  h=np.array([p['html']['claims'][judge][key] for p in pairs]);m=np.array([p['mjml']['claims'][judge][key] for p in pairs]);print(judge,key,'p',wilcoxon(h,m).pvalue,'delta',np.sign(h[:,None]-m[None,:]).mean())
for judge in ['judge_scores','judge_gpt_scores']:
 for key in ['design','readability','overall']:
  h=np.array([p[judge]['html'][key] for p in pairs]);m=np.array([p[judge]['mjml'][key] for p in pairs]);print(judge,key,'p',wilcoxon(h,m).pvalue,'delta',np.sign(h[:,None]-m[None,:]).mean())
# reproduce live E6 directly from supplied measures, avoiding missing original CSVs
X=[]
for p in pairs:
 h,m=p['html'],p['mjml'];c=h['clients']['Outlook Windows']
 X.append([bool(c['layout'] or c['content'] or h['pipeline_flags']),h['bytes']-m['bytes'],h['words']-m['words'],len(c['cosmetic']),len(h['features_outside']),p['set']=='F'])
X=np.array(X,float)
for k in [1,2,3,4]:X[:,k]=(X[:,k]-X[:,k].mean())/X[:,k].std()
X=sm.add_constant(X)
def ci(y,X,k,res):
 b,se=res.params[k],res.bse[k];rest=np.delete(X,k,axis=1)
 def f(v):return 2*(res.llf-sm.GLM(y,rest,family=sm.families.Binomial(),offset=v*X[:,k]).fit().llf)-3.841458820694124
 return [float(np.exp(brentq(f,b-6*se,b))),float(np.exp(brentq(f,b,b+6*se)))]
for judge in ['judge_consistent','judge_gpt_consistent']:
 y=np.array([p[judge]=='html' for p in pairs],float);res=sm.Logit(y,X).fit(disp=False,maxiter=200)
 print(judge,'E6 risky OR',np.exp(res.params[1]),'Wald',np.exp(res.conf_int()[1]),'profile',ci(y,X,1,res),'cosmetic OR',np.exp(res.params[4]),'profile',ci(y,X,4,res))
