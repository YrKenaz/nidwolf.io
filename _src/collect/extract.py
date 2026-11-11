import re,sys,html,json,glob,os
D=sys.argv[1]; out={}
def rd(n): return open(os.path.join(D,n+'.html'),encoding='utf-8',errors='replace').read()
def clean(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',s))).strip()
def seq(t):
    t=re.sub(r'(?s)<style.*?</style>','',t)
    t2=re.sub(r'(?s)<script.*?</script>','',t)
    r=[]
    for m in re.finditer(r'(?s)<(h[1-4])[^>]*>(.*?)</\1>|<img[^>]*?(?:data-src|data-lazy-src|src)="([^"]+)"',t2):
        if m.group(1): r.append(('h',m.group(1),clean(m.group(2))))
        elif not m.group(3).startswith('data:'): r.append(('i',html.unescape(m.group(3))))
    return r
def ranked(name,tag,img_after=True,pat=r'^(\d+)\.\s*(.+)$'):
    s=seq(rd(name)); res=[]
    for k,x in enumerate(s):
        if x[0]=='h' and x[1]==tag:
            m=re.match(pat,x[2])
            if not m: continue
            img=None
            rng=range(k+1,min(k+4,len(s))) if img_after else range(k-1,max(k-4,-1),-1)
            for j in rng:
                if s[j][0]=='h':
                    if img_after: break
                    else: continue
                u=s[j][1]
                if 'wp-content/uploads' in u and '400x' not in u and 'w=48' not in u: img=u;break
            res.append({'rank':int(m.group(1)),'name':m.group(2),'img':img})
    return res
out['uproxx_scotch100']=ranked('uproxx_scotch','h2')
out['uproxx_bourbon100']=ranked('uproxx_bourbon','h2')
out['uproxx_sm10']=ranked('uproxx_sm','h3')
out['uproxx_irish20']=ranked('uproxx_irish','h3')+ranked('uproxx_irish','h2')
out['uproxx_intl35']=ranked('uproxx_intl','h2')+ranked('uproxx_intl','h3')
out['mom_scotch']=ranked('mom_scotch','h3',False)
out['mom_jp']=ranked('mom_jp','h3',False)
# whiskey wash
s=seq(rd('wash25')); res=[]
for k,x in enumerate(s):
    if x[0]=='h' and x[1]=='h3' and re.search(r'\d%',x[2]):
        img=None
        for j in range(k+1,min(k+4,len(s))):
            if s[j][0]=='i': img=s[j][1];break
            else: break
        res.append({'name':x[2].split(',')[0],'img':img})
out['wash25']=res
# boozemakers json-ld
bz={}
for f in sorted(glob.glob(os.path.join(D,'bz_*.html'))+glob.glob(os.path.join(D,'booze_*.html'))):
    t=open(f,encoding='utf-8',errors='replace').read()
    for m in re.finditer(r'(?s)<script[^>]*application/ld\+json[^>]*>(.*?)</script>',t):
        try: j=json.loads(m.group(1))
        except Exception: continue
        def walk(o):
            if isinstance(o,dict):
                if o.get('@type')=='Product' and 'aggregateRating' in o:
                    n=o.get('name'); r=o['aggregateRating'].get('ratingValue')
                    if n and r: bz.setdefault(n,{'scores':[], 'img':o.get('image'),'lists':[]}); bz[n]['scores'].append(float(r)); bz[n]['lists'].append(os.path.basename(f)[:-5])
                for v in o.values(): walk(v)
            elif isinstance(o,list):
                for v in o: walk(v)
        walk(j)
out['boozemakers']=[{'name':n,'score':max(v['scores']),'img':v['img'] if isinstance(v['img'],str) else (v['img'][0] if v['img'] else None),'lists':sorted(set(v['lists']))} for n,v in bz.items()]
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False,indent=1)
for k,v in out.items(): print(k,len(v),sum(1 for e in v if e.get('img')))
