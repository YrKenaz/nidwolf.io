import json,re,sys,os,unicodedata
sys.path.insert(0,sys.argv[1]+'/bin')
from t import txt
D=sys.argv[1]+'/dl/'
P=json.load(open(D+'e_picks.json'))
SNAP='/mnt/h/Dev/Tier/Whiskey/data/snapshots/'
SID={'wf':'whiskyfun','wn':'whiskynotes','df':'dramface'}
def fn(host,u): return D+'pg/'+host+'__'+re.sub(r'[^A-Za-z0-9._-]','_',u.split('//',1)[1])[:180]
def norm(s):
    s=s.replace('’',"'").replace('‘',"'")
    return re.sub(r'[^a-z0-9%]+',' ',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()).strip()
# load existing snapshot lines
L={s:open(SNAP+SID[s]+'__20261111.txt',encoding='utf-8').read().split('\n') for s in SID}
for s in L:
    if L[s] and L[s][-1]=='': L[s].pop()
have={s:{l[12:-6] for l in L[s] if l.startswith('===== PAGE: ')} for s in SID}
start={}
def add(s,u,f):
    if u in have[s]:
        i=L[s].index('===== PAGE: '+u+' ====='); start[(s,u)]=i+1; return True
    if not os.path.exists(f) or os.path.getsize(f)<3000: return False
    L[s].append('===== PAGE: '+u+' ====='); start[(s,u)]=len(L[s])
    L[s]+=[x.rstrip() for x in txt(f).split('\n')]; L[s].append('===== END PAGE ====='); have[s].add(u); return True
def rng(s,u):
    a=start[(s,u)]; b=a
    while L[s][b]!='===== END PAGE =====': b+=1
    return a,b
out={}; miss=[]
for bid,p in P.items():
    o={}
    if 'wf' in p:
        name,u=p['wf']; pu=u.split('#')[0]
        if add('wf',pu,D+'wf/'+pu.split('/')[-1]):
            a,b=rng('wf',pu); core=re.sub(r' - (by Angus - )?\d{5,6}.*$','',name); core=re.sub(r' ?- ?by Angus.*$','',core).strip()
            head=norm(core.split('(')[0]); abv=re.search(r'\(([\d.,]+ ?%)',core)
            yr=re.findall(r'20[12]\d',core)
            hit=None
            for i in range(a,b):
                ln=L['wf'][i]
                if len(ln)<10 or len(ln)>600: continue
                if norm(ln).startswith(head) and (not abv or abv.group(1).replace(' ','') in ln.replace(' ','')) and (not yr or yr[-1] in ln):
                    for j in range(i,min(b,i+12)):
                        m=re.search(r'S[GP][GP]\s*:?\s*\d{3}\s*[-–]\s*(\d{2})\s*points',L['wf'][j])
                        if m: hit=(i,j,m.group(1)); break
                        if j>i and re.search(r'\([\d.,]+ ?%, ',L['wf'][j][:120]) : break
                    if hit: break
            if hit:
                d=re.search(r'#(\d{6})',u).group(1)
                o['wf']={'raw':hit[2]+' points','name':L['wf'][hit[0]].strip()[:160],'url':u,'date':'20'+d[4:]+'-'+d[2:4]+'-'+d[:2],'author':'Angus MacRaild' if 'Angus' in name else 'Serge Valentin','line_name':hit[0]+1,'line_score':hit[1]+1,'x':int(hit[2])}
            else: miss.append((bid,'wf',core[:60]))
        else: miss.append((bid,'wf','nofile'))
    if 'wn' in p:
        u=p['wn']; f=fn('wn',u)
        if add('wn',u,f):
            a,b=rng('wn',u); h=open(f,'rb').read().decode('utf-8','replace')
            box=re.findall(r'class="entry-score">(\d\d)<',h)
            inl=[(i,m.group(1)) for i in range(a,b) for m in [re.search(r'Score:\s*(\d{2})\s*/\s*100',L['wn'][i])] if m]
            heads=[i for i in range(a,b) if re.search(r'\([\d.,]+ ?%, [^)]{2,120}\)\s*$',L['wn'][i]) and len(L['wn'][i])<160]
            ln=heads[0] if heads else a
            if len(heads)<=1 and len({s for _,s in inl})==1 and not box: o['wn']={'raw':'Score: '+inl[0][1]+'/100','line_score':inl[0][0]+1,'x':int(inl[0][1])}
            elif len(heads)<=1 and box and not inl:
                ls=next((i for i in range(a,b) if L['wn'][i].strip()==box[0]),None)
                if ls is not None: o['wn']={'raw':box[0]+' (score box)','line_score':ls+1,'x':int(box[0])}
            if 'wn' in o: o['wn'].update({'name':L['wn'][ln].strip()[:160],'url':u,'date':u.split('/')[3],'author':'Ruben Luyten','line_name':ln+1})
            else: miss.append((bid,'wn','heads%d box%s inl%s'%(len(heads),box,[s for _,s in inl])))
        else: miss.append((bid,'wn','nofile'))
    if 'df' in p:
        u=p['df']; f=fn('df',u)
        if add('df',u,f):
            a,b=rng('df',u)
            sc=[(i,m.group(1),m.group(2)) for i in range(a,b) for m in [re.search(r'Score:\s*(\d+)/10\*?\s*([A-Z][A-Za-z]{1,3})?\s*$',L['df'][i])] if m]
            vals=[s for _,s,_ in sc]; ini=[(i,s) for i,s,t in sc if t]
            title=next((i for i in range(a,b) if '— Dramface' in L['df'][i] or 'Dramface' in L['df'][i]),a)
            date=re.search(r'/all-reviews/(20\d\d)/',u).group(1)
            if vals and len(set(vals))==1: o['df']={'raw':'Score: '+vals[0]+'/10','x':float(vals[0]),'line_score':sc[0][0]+1}
            elif len(ini)>=2: o['df']={'raw':'Score: '+', '.join(s+'/10' for _,s in ini)+' (리뷰어 %d명)'%len(ini),'x':sum(int(s) for _,s in ini)/len(ini),'line_score':ini[0][0]+1}
            if 'df' in o: o['df'].update({'name':L['df'][title].strip()[:120],'url':u,'date':date,'line_name':title+1})
            else: miss.append((bid,'df',str(vals)))
        else: miss.append((bid,'df','nofile'))
    if o: out[bid]=o
json.dump(out,open(D+'e_obs.json','w'),indent=1,ensure_ascii=False)
if '--write' in sys.argv:
    for s in SID: open(SNAP+SID[s]+'__20261111.txt','w',encoding='utf-8').write('\n'.join(L[s])+'\n')
print(len(out),{s:sum(1 for v in out.values() if s in v) for s in SID}); print('miss',len(miss)); 
for m in miss: print('  ',m)
