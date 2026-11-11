import json,sys,re,html as H,unicodedata
sys.path.insert(0,sys.argv[1]+'/bin')
from t import txt
D=sys.argv[1]+'/dl/'
picks=json.load(open(D+'wf_picks.json'))
def norm(s):
    s=s.replace('’',"'").replace('‘',"'").replace('`',"'")
    return re.sub(r'[^a-z0-9%]+',' ',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()).strip()
cache={}
res={}
for k,(n,u) in picks.items():
    p=u.split('#')[0].split('/')[-1]
    if p not in cache: cache[p]=txt(D+'wf/'+p)
    t=cache[p]
    core=re.sub(r' - (by Angus - )?\d{5,6}.*$','',n).strip()
    core=re.sub(r' - by Angus.*$','',core)
    # find name: use first 25 normalized chars + abv
    head=norm(core.split('(')[0]); abv=re.search(r'\(([\d.,]+ ?%)',core)
    best=None
    for mm in re.finditer(r'[^\n]{0,400}',t):
        line=mm.group(0)
        if len(line)<10: continue
        nl=norm(line)
        if head and head in nl and (not abv or abv.group(1).replace(' ','') in line.replace(' ','')):
            after=t[mm.start():mm.start()+6000]
            sc=re.search(r'S[GP][GP]\s*:?\s*\d{3}\s*[-–]\s*(\d{2})\s*points',after)
            if sc:
                # ensure no other bottle header between: count 'points' occurrences before
                best=(mm.start(),line.strip()[:200],sc.group(1),after[sc.start():sc.end()],after[:sc.end()]); break
    res[k]={'index_name':n,'url':u,'found':bool(best)}
    if best: res[k].update({'line':best[1],'score':best[2],'score_txt':best[3],'block':best[4]})
    print(k,'|',(best[2]+' | '+best[1][:110]) if best else 'NOT FOUND: '+core[:80])
json.dump(res,open(D+'wf_res.json','w'),indent=1,ensure_ascii=False)
