import re,html,json,sys,difflib,unicodedata
S=sys.argv[1]; R=sys.argv[2]
t=open(S+'/dl2/wa_meta.html',encoding='utf-8',errors='replace').read()
rows=[]
for r in re.findall(r'(?s)<tr[^>]*>(.*?)</tr>',t):
    c=[re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x))).strip() for x in re.findall(r'(?s)<t[dh][^>]*>(.*?)</t[dh]>',r)]
    if len(c)==10 and c[0]!='Whisky':
        try: rows.append({'name':c[0],'meta':float(c[1]),'sd':float(c[2]) if c[2] else None,'n':int(c[3]),'cost':c[4],'cls':c[5],'cluster':c[7] or c[6],'country':c[8],'type':c[9]})
        except ValueError: pass
json.dump(rows,open(S+'/wa_rows.json','w'),ensure_ascii=False)
STOP=set("the single malt scotch whisky whiskey bourbon kentucky straight year years old yo aged label blended irish japanese rye bottled edition islay highland speyside of and".split())
def nz(s):
    s=unicodedata.normalize('NFKD',s); s=''.join(ch for ch in s if not unicodedata.combining(ch)).lower().replace("'","").replace("’","")
    s=re.sub(r'(\d+)\s*yo\b',r'\1',s); s=re.sub(r'[^a-z0-9 ]',' ',s)
    return [w for w in s.split() if w not in STOP]
B=json.load(open(R+'/data/bottles.json'))
W=[(r,set(nz(r['name'])),nz(r['name'])) for r in rows]
out={}
for b in B:
    q=nz(b['en']); qs=set(q); best=[]
    for r,ws,wl in W:
        if not qs or not ws: continue
        inter=len(qs&ws); 
        if inter==0: continue
        j=inter/len(qs|ws); sm=difflib.SequenceMatcher(None,' '.join(q),' '.join(wl)).ratio()
        nums_q={x for x in q if x.isdigit()}; nums_w={x for x in wl if x.isdigit()}
        pen=0.3 if nums_q!=nums_w else 0
        best.append((0.6*j+0.4*sm-pen,r))
    best.sort(key=lambda x:-x[0])
    out[b['id']]=[(round(s,2),r['name'],r['meta'],r['n']) for s,r in best[:2]]
json.dump(out,open(S+'/wa_cand.json','w'),ensure_ascii=False)
for b in B:
    c=out[b['id']]
    print(f"{b['id']}|{b['en']}|"+(' || '.join(f"{s} {n} ({m},{k})" for s,n,m,k in c) if c else 'NONE'))
