import json,sys,os,re,subprocess,time,urllib.parse
D=sys.argv[1]+'/dl/'
r=json.load(open(D+'final_2019.json'))
todo=[x for x in r if x['tier2019'] in('A','B')]
cache=D+'ds_cand.json'; C=json.load(open(cache)) if os.path.exists(cache) else {}
Q=json.load(open(D+'ds_q.json')) if os.path.exists(D+'ds_q.json') else {}
for x in todo:
    q=Q.get(x['id'],x['ko'])
    if x['id'] in C and C[x['id']]['q']==q: continue
    u='https://dailyshot.co/m/search/result?q='+urllib.parse.quote(q)
    p=subprocess.run(['curl','-sL','-m','40','-w','\n%{http_code}','-A','Mozilla/5.0 (compatible; research-fetch)',u],capture_output=True)
    t=p.stdout.decode('utf-8','replace'); code=t.rsplit('\n',1)[-1]
    if code in('403','429'): print('BLOCKED',code); break
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',t,re.S); res=[]
    if m:
        try:
            j=json.loads(m.group(1))
            for qq in j['props']['pageProps']['dehydratedState']['queries']:
                dd=qq['state'].get('data')
                if isinstance(dd,dict) and 'pages' in dd:
                    for pg in dd['pages']: res+=pg.get('results',[])
        except Exception as e: print('ERR',x['id'],e)
    keep=[{k:y.get(k) for k in ('id','name','en_name','top_product_name','top_product_id','subcategory','thumbnail_image','review_rate','review_count','price','status','tags')} for y in res if y.get('category')=='위스키'][:30]
    C[x['id']]={'q':q,'http':code,'n':len(res),'results':keep}
    json.dump(C,open(cache,'w'),ensure_ascii=False,indent=0)
    time.sleep(6)
print('DONE',len(C))
