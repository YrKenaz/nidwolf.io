import json,sys,os,re,subprocess,time,urllib.parse,difflib
S=sys.argv[1]; d=json.load(open(S+'/result.json'))['whiskies']
cache=S+'/ds.json'; C=json.load(open(cache)) if os.path.exists(cache) else {}
Q=json.load(open(S+'/tools/dsq.json')) if os.path.exists(S+'/tools/dsq.json') else {}
def nz(s): return re.sub(r'[\s\[\]()년]','',s).lower()
for w in d:
    i=w['id']
    q=Q.get(i,w['ko'])
    if i in C and C[i].get('q')==q: continue
    u='https://dailyshot.co/m/search/result?q='+urllib.parse.quote(q)
    r=subprocess.run(['curl','-sL','-m','30','-A','Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36',u],capture_output=True)
    t=r.stdout.decode('utf-8','replace')
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',t,re.S)
    best=None
    if m:
        try:
            j=json.loads(m.group(1)); res=[]
            for qq in j['props']['pageProps']['dehydratedState']['queries']:
                dd=qq['state'].get('data')
                if isinstance(dd,dict) and 'pages' in dd:
                    for p in dd['pages']: res+=p.get('results',[])
            cands=[]
            for x in res:
                if x.get('category')!='위스키' or not x.get('thumbnail_image'): continue
                nm=x.get('top_product_name') or x['name']
                sc=difflib.SequenceMatcher(None,nz(nm),nz(q)).ratio()
                if re.search(r'세트|전용잔|미니어처|50ml|200ml|패키지|기획|바이알|375ml|&',x['name']): sc-=0.25
                cands.append((sc,nm,x.get('en_name'),x['thumbnail_image'],x.get('review_rate'),x.get('review_count')))
            cands.sort(key=lambda c:-c[0])
            if cands: best=cands[0]
        except Exception as e: print('ERR',i,e)
    C[i]={'q':q,'match':best}
    json.dump(C,open(cache,'w'),ensure_ascii=False,indent=0)
    time.sleep(0.35)
for w in d:
    b=C[w['id']]['match']
    print(w['id'],'|',w['ko'],'=>',(f"{b[0]:.2f} {b[1]} / {b[2]}" if b else 'NONE'))
