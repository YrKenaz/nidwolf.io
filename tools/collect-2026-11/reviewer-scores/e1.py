import json,re,sys,subprocess,time,os
D=sys.argv[1]+'/dl/'
m=json.load(open(D+'m2.json'))
picks={}
BAD=re.compile(r'19\d\d|circa|c19|early|late|\d0s|proof|75cl|litre|liter|magnum|import|rotation|miniature',re.I)
for k,v in m.items():
    p={}
    c=[]
    for yy,name,u in v['wf']:
        par=name[name.find('('):]
        if BAD.search(par): continue
        ys=[int(y) for y in re.findall(r'\b(20[12]\d)\b',par.split(' - ')[0])]
        if not ys or max(ys)<2015: continue
        c.append((max(ys),yy,name,u))
    if c:
        c.sort(reverse=True); p['wf']=c[0][2:]
    if v['wn']: p['wn']=v['wn'][0]
    if v['df']: p['df']=v['df'][0]
    if p: picks[k]=p
picks.get('tomatin-15',{}).pop('df',None)
picks={k:v for k,v in picks.items() if v}
json.dump(picks,open(D+'e_picks.json','w'),indent=1,ensure_ascii=False)
print(len(picks),{s:sum(1 for v in picks.values() if s in v) for s in('wf','wn','df')})
def fn(host,u): return D+'pg/'+host+'__'+re.sub(r'[^A-Za-z0-9._-]','_',u.split('//',1)[1])[:180]
jobs={'wf':sorted({v['wf'][1].split('#')[0] for v in picks.values() if 'wf' in v}),'wn':sorted({v['wn'] for v in picks.values() if 'wn' in v}),'df':sorted({v['df'] for v in picks.values() if 'df' in v})}
print({k:len(v) for k,v in jobs.items()})
json.dump(jobs,open(D+'e_jobs.json','w'))
