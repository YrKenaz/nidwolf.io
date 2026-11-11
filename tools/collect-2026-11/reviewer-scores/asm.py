import sys,re,os,json,html as H
sys.path.insert(0,sys.argv[1]+'/bin')
from t import txt
from targets import T
D=sys.argv[1]+'/dl/'
m=json.load(open(D+'matches.json')); px=json.load(open(D+'px.json')); wf=json.load(open(D+'wf_res.json'))
def fn(host,u): return host+'__'+re.sub(r'[^A-Za-z0-9._-]','_',u.split('//',1)[1])[:180]
out={}
for id,en,ty,slug,wfre in T:
    o={}
    w=wf.get(id)
    if w and w.get('found'):
        d=re.search(r'#(\d{6})',w['url']).group(1)
        o['wf']=[{'raw':w['score']+' points','name':w['line'][:160],'url':w['url'],'date':'20'+d[4:]+'-'+d[2:4]+'-'+d[:2],'quote':w['block']}]
    for host in ['wn','df','bb','ww']:
        for u in m[id][host]:
            f=fn(host,u); p=px.get(f)
            if not p or not os.path.exists(D+'pg/'+f): continue
            if host=='bb' and p.get('score'):
                o.setdefault('bb',[]).append({'raw':p['score']+' (5 barrels scale)','name':p['title'].replace(' Review | Breaking Bourbon',''),'url':u,'date':p['date'],'author':(p.get('author') or '').split('"')[0],'proof':p.get('Proof'),'age':p.get('Age')})
            if host=='df' and p.get('scores'):
                s=list(dict.fromkeys(p['scores']))
                o.setdefault('df',[]).append({'raw':'Score: '+s[0] if len(s)==1 else 'MULTI '+','.join(p['scores']),'name':p['title'].replace(' — Dramface','').strip(),'url':u,'date':p['date'],'author':p.get('author'),'abv':p.get('abv')})
            if host=='ww':
                t=txt(D+'pg/'+f)
                old=re.search(r'(?i)(?:score|rating)\s*:?\s*(\d{2,3})\s*/\s*100',t)
                raw=None
                if p.get('score'): raw='OVERALL RATING '+p['score']+' (bestRating 10)'
                elif old: raw=old.group(0)
                a=re.search(r'\n ?by ?\n ?([^\n]+)\n',t)
                if raw: o.setdefault('ww',[]).append({'raw':raw,'name':p['title'][:90],'url':u,'date':p['date'],'author':a.group(1).strip() if a else None})
            if host=='wn':
                t=txt(D+'pg/'+f)
                # per-bottle: header then Score
                segs=[(mm.start(),mm.group(1).strip()) for mm in re.finditer(r'\n ?([^\n]{4,110}\([\d.,]+ ?%, [^\n]{2,120}\))\s*\n',t)]
                found=None
                for i,(pos,hd) in enumerate(segs):
                    if re.search(wfre,hd) or re.search(slug.replace('-','.{0,3}'),hd,re.I):
                        end=segs[i+1][0] if i+1<len(segs) else len(t)
                        sc=re.search(r'Score:\s*(\d{2})\s*/\s*100',t[pos:end+0]) or re.search(r'Score:\s*(\d{2})\s*/\s*100',t[pos:pos+4000] if i+1==len(segs) else '')
                        if sc: found=(hd,'Score: '+sc.group(1)+'/100'); break
                        if len(segs)==1 and p['scores']: found=(hd,p['scores'][0]+' (score box)'); break
                if not found and len(segs)<=1:
                    sc=re.findall(r'Score:\s*(\d{2})\s*/\s*100',t)
                    if len(set(sc))==1: found=(segs[0][1] if segs else p['title'],'Score: '+sc[0]+'/100')
                    elif p['scores'] and not sc: found=(segs[0][1] if segs else p['title'],p['scores'][0]+' (score box)')
                if found: o.setdefault('wn',[]).append({'raw':found[1],'name':found[0][:140],'url':u,'date':u.split('/')[3]})
    if o: out[id]={'en':en,'type':ty,'obs':o}
json.dump(out,open(D+'cand_raw.json','w'),indent=1,ensure_ascii=False)
n2=0
for id,v in out.items():
    o=v['obs']; n2+= len(o)>=2
    print(id,'|',' || '.join(s+': '+' ; '.join(x['raw'].replace(' (5 barrels scale)','/5').replace('OVERALL RATING ','').replace(' (bestRating 10)','/10').replace(' points','')+' ['+x['name'][:48]+' '+str(x.get('date'))[:4]+']' for x in xs) for s,xs in o.items()))
print(len(out),'cands',n2,'with 2+ src')
