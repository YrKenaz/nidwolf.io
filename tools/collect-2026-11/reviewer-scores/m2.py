import re,sys,json,glob,html as H,unicodedata
D=sys.argv[1]+'/dl/'
B=json.load(open('/mnt/h/Dev/Tier/nidwolf.io/data/bottles.json'))
def norm(s):
    s=s.replace('’',"'").replace('‘',"'")
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
    s=s.replace("'s",'s').replace('&',' and ').replace('d.e.w.','dew').replace('no.','no ')
    return re.sub(r'[^a-z0-9.%]+',' ',s).strip()
STOP={'the','year','years','old','yo','single','malt','whisky','whiskey','scotch','ob','label','edition','of','and','straight','kentucky','bourbon','islay','speyside','highland'}
wf={}
for f in glob.glob(D+'www.whiskyfun.com_*.html'):
    if 'FTC' in f: continue
    h=open(f,'rb').read().decode('latin-1')
    for li in re.findall(r'(?is)<li[^>]*>(.*?)</li>',h):
        m=re.findall(r'href="([^"]*archive[^"]*#(\d{6}))"',li)
        name=re.sub(r'\s+',' ',H.unescape(re.sub(r'<[^>]+>',' ',li))).strip()
        if m and len(name)<260:
            u,d=m[-1]
            try: yy=int(d[4:6])
            except: continue
            if 19<=yy<=26: wf[name]=(u if u.startswith('http') else 'https://www.whiskyfun.com/'+u, yy)
print(len(wf),'wf entries 2019+',file=sys.stderr)
wn=[u.strip() for u in open(D+'wn_urls.txt') if '/whisky-news/' not in u and re.match(r'https://www.whiskynotes.be/(2019|202\d)/',u)]
df=[u.strip() for u in open(D+'df_urls.txt')]
out={}
for b in B:
    en=b['en']; n=norm(en); toks=[t for t in n.split() if t not in STOP]
    age=b['age']; 
    words=[t for t in toks if not (age and t==str(age))]
    brand=words[0] if words else ''
    rest=words[1:]
    r={'wf':[],'wn':[],'df':[]}
    for name,(u,yy) in wf.items():
        nn=norm(name); head=nn.split('(')[0] if '(' in name else nn
        headn=norm(name.split('(')[0])
        if not headn.startswith(brand): continue
        if ', ob' not in name.lower().replace('(ob','(, ob') and 'OB' not in name: continue
        par=name[name.find('('):].lower() if '(' in name else ''
        if re.search(r'cask #|single cask|\bfor [a-z]|hand.?fill|distillery only|feis|festival|exclusive|\d+ bottles',par): continue
        if age:
            if not re.search(r'\b'+str(age)+r' yo\b',headn): continue
            if re.search(r'\b(19|20)\d\d\b',headn): continue
        else:
            if re.search(r'\b\d+ yo\b',headn): continue
        ht=[t for t in headn.split() if t not in STOP and t!='yo' and not (age and t==str(age))]
        if set(ht)!=set(words): continue
        ab=re.search(r'\(([\d.,]+) ?%',name)
        if ab and b['abv']:
            a=float(ab.group(1).replace(',','.'))
            if abs(a-b['abv'])>(6 if 'cs' in b['style'] else 3.01): continue
        r['wf'].append((yy,name,u))
    r['wf'].sort(reverse=True)
    def slugmatch(u):
        s=u.rstrip('/').split('/')[-1].lower()
        st=[t for t in re.split(r'[^a-z0-9]+',s) if t]
        st2=[re.sub(r'^(\d+)(yo|y|years?)$',r'\1',t) for t in st]
        st3=[t for t in st2 if t not in STOP and not re.fullmatch(r'20\d\d|review|reviewed|batch',t)]
        want=[w.replace('.','') for w in words]+([str(age)] if age else [])
        want=[w for w in want if w]
        return sorted(st3)==sorted(want)
    r['wn']=sorted([u for u in wn if slugmatch(u)],reverse=True)
    r['df']=sorted([u for u in df if slugmatch(u)],reverse=True)
    if any(r.values()): out[b['id']]=r
json.dump(out,open(D+'m2.json','w'),indent=1,ensure_ascii=False)
import collections
print(len(out),'bottles matched;', {s:sum(1 for v in out.values() if v[s]) for s in('wf','wn','df')},file=sys.stderr)
bm={b['id']:b for b in B}
for k,v in out.items():
    print(k,'|',bm[k]['en'],bm[k]['abv'],'||',' ## '.join([f"WF{y}:{n[:70]}" for y,n,u in v['wf'][:2]]+['WN:'+u.split('/',4)[-1][:55] for u in v['wn'][:2]]+['DF:'+u.split('/',4)[-1][:45] for u in v['df'][:2]]))
