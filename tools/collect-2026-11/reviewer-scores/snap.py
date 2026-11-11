import sys,re,os,json,difflib,unicodedata
sys.path.insert(0,sys.argv[1]+'/bin')
from t import txt
D=sys.argv[1]+'/dl/'
OUT='/mnt/h/Dev/Tier/Whiskey/data/snapshots/'
res=json.load(open(D+'final.json'))
SID={'wf':'whiskyfun','wn':'whiskynotes','df':'dramface'}
def pgfile(s,u):
    if s=='wf': return D+'wf/'+u.split('#')[0].split('/')[-1]
    return D+'pg/'+s+'__'+re.sub(r'[^A-Za-z0-9._-]','_',u.split('//',1)[1])[:180]
pages={s:{} for s in SID}
for r in res:
    for s,o in r['obs'].items():
        if s in SID: pages[s][o['url'].split('#')[0]]=pgfile(s,o['url'])
lines={}; start={}
for s,ps in pages.items():
    L=['# source: '+SID[s],'# collected: 2026-11-11','# method: raw HTML fetched with curl, script/style removed, tags stripped, entities decoded, whitespace collapsed. No summarising or translation.','']
    for u in sorted(ps):
        L.append('===== PAGE: '+u+' ====='); start[(s,u)]=len(L)
        L+= [x.rstrip() for x in txt(ps[u]).split('\n')]
        L.append('===== END PAGE =====')
    lines[s]=L
    open(OUT+SID[s]+'__20261111.txt','w',encoding='utf-8').write('\n'.join(L)+'\n')
    print(SID[s],len(ps),'pages',len(L),'lines',round(os.path.getsize(OUT+SID[s]+'__20261111.txt')/1e6,2),'MB')
def norm(x): return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',x.replace('’',"'")).encode('ascii','ignore').decode().lower()).strip()
bad=0
for r in res:
    for s,o in r['obs'].items():
        if s not in SID: continue
        u=o['url'].split('#')[0]; L=lines[s]; a=start[(s,u)]
        b=a
        while L[b]!='===== END PAGE =====': b+=1
        nm=norm(o['name'])[:40]
        ln=next((i for i in range(a,b) if nm and nm in norm(L[i])),None)
        if s=='wf':
            sc=re.search(r'(\d\d) points',o['raw']).group(1)
            ls=next((i for i in range(ln or a,b) if re.search(r'S[GP][GP]\s*:?\s*\d{3}\s*[-–]\s*'+sc+r'\s*points',L[i])),None)
            auth='Angus MacRaild' if any('ngus' in L[i] for i in range(max(a,(ln or a)-1),(ln or a)+1)) or 'by Angus' in json.load(open(D+'wf_res.json')).get(r['id'],{}).get('index_name','') else 'Serge Valentin'
            o['author']=auth
        elif s=='wn':
            sc=re.search(r'(\d\d)',o['raw']).group(1)
            if 'score box' in o['raw']: ls=next((i for i in range(a,b) if L[i].strip()==sc),None)
            else: ls=next((i for i in range(ln or a,b) if re.search(r'Score:\s*'+sc+r'\s*/\s*100',L[i])),None)
            o['author']='Ruben Luyten'
        else:
            scs=re.findall(r'(\d+)/10',o['raw'])
            ls=next((i for i in range(a,b) if re.search(r'Score:\s*'+scs[0]+'/10',L[i])),None)
        o['snapshot']=SID[s]+'__20261111.txt'; o['line_name']=ln+1 if ln is not None else None; o['line_score']=ls+1 if ls is not None else None
        if ln is None or ls is None: bad+=1; print('CHECK',r['id'],s,o['raw'],'| name line',ln,'| score line',ls,'|',o['name'][:50])
print('unverified',bad)
# master check
B=json.load(open('/mnt/h/Dev/Tier/nidwolf.io/data/bottles.json'))
ids={b['id'] for b in B}
def toks(x): return set(norm(x).replace('year','').replace('yo','').split())
for r in res:
    if r['id'] in ids: print('ID CLASH',r['id'])
    t=toks(r['en']); best=[]
    for b in B:
        tb=toks(b['en']); j=len(t&tb)/len(t|tb)
        if j>=0.6: best.append((round(j,2),b['id'],b['en'],b['abv']))
    r['master_near']=sorted(best,reverse=True)[:3]
    if best: print('NEAR',r['id'],'|',r['en'],'->',r['master_near'])
json.dump(res,open(D+'final2.json','w'),indent=1,ensure_ascii=False)
