import json,re,difflib,sys
C=json.load(open('ds_cand.json')); r={x['id']:x for x in json.load(open('final_2019.json'))}
def nz(s): return re.sub(r'[^a-z0-9]','',(s or '').lower().replace('years','').replace('year','').replace('yo','').replace('old','').replace('the ',''))
M={}
for k,v in C.items():
    x=r[k]; c=[]
    for y in v['results']:
        sc=difflib.SequenceMatcher(None,nz(y.get('en_name')),nz(x['en'])).ratio()
        c.append((round(sc,2),y))
    c.sort(key=lambda t:-t[0])
    good=[t for t in c if t[0]>=0.72]
    M[k]=good
    if '-v' in sys.argv: print(x['tier2019'],x['type'],k,'|',x['en'],'=>',[(s,y['name'],y.get('en_name'),y.get('price'),y.get('review_count')) for s,y in good[:4]] or ('NONE',[(s,y.get('en_name')) for s,y in c[:1]]))
json.dump(M,open('ds_match.json','w'),ensure_ascii=False)
print(len(C),'queried;',sum(1 for v in M.values() if v),'matched')
print('MISS',[k for k,v in M.items() if not v])
