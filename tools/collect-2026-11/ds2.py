import json,sys,os,re,subprocess,time,urllib.parse,difflib
S=sys.argv[1]; cache=S+'/ds2.json'; C=json.load(open(cache)) if os.path.exists(cache) else {}
Q=json.load(open(S+'/tools/dsq2.json')) if os.path.exists(S+'/tools/dsq2.json') else {}
items=[l.split('|')[:2] for l in open(S+'/tools/wa_new.txt',encoding='utf-8')]
def nz(s): return re.sub(r'[\s\[\]()년]','',s).lower()
for i,ko in items:
    q=Q.get(i,ko)
    if i in C and C[i]['q']==q: continue
    u='https://dailyshot.co/m/search/result?q='+urllib.parse.quote(q)
    t=subprocess.run(['curl','-sL','-m','30','-A','Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36',u],capture_output=True).stdout.decode('utf-8','replace')
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',t,re.S); best=None
    if m:
        try:
            j=json.loads(m.group(1)); cands=[]
            for qq in j['props']['pageProps']['dehydratedState']['queries']:
                dd=qq['state'].get('data')
                if isinstance(dd,dict) and 'pages' in dd:
                    for p in dd['pages']:
                        for x in p.get('results',[]):
                            if x.get('category')!='위스키' or not x.get('thumbnail_image'): continue
                            nm=x.get('top_product_name') or x['name']
                            sc=difflib.SequenceMatcher(None,nz(nm),nz(q)).ratio()
                            if re.search(r'세트|전용잔|미니어처|50ml|200ml|패키지|기획|바이알|375ml|&',x['name']): sc-=0.25
                            cands.append([round(sc,2),nm,x.get('en_name'),x['thumbnail_image'],x.get('review_rate'),x.get('review_count'),x.get('price'),x['name']])
            cands.sort(key=lambda c:-c[0]); best=cands[0] if cands else None
        except Exception as e: print('ERR',i,e)
    C[i]={'q':q,'match':best}; json.dump(C,open(cache,'w'),ensure_ascii=False); time.sleep(0.3)
for i,ko in items:
    b=C[i]['match']; print(i,'|',ko,'=>',(f"{b[0]} {b[1]} / {b[2]}" if b else 'NONE'))
