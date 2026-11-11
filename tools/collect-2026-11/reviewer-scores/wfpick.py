import json,sys,re,subprocess,time,os
D=sys.argv[1]+'/dl/'
m=json.load(open(D+'wf_matches.json'))
skip='glenlivet-14-cognac talisker-30 bunnahabhain-12-cs arran-21 ballantines-30 teachers islay-mist nikka-frontier hibiki-12 hibiki-blenders-choice ichiros-double-distilleries akkeshi fuji-single-malt togouchi kurayoshi shizuoka gold-spot knappogue-16 slane west-cork mcconnells penderyn-madeira indri templeton-rye michters-sour-mash old-ezra-7 benchmark old-forester-statesman wyoming-whiskey springbank-21 ardnamurchan-ad waterford'.split()
idx={'glenfiddich-23-grand-cru':2,'aberlour-14':2,'aberlour-18':1,'tullibardine-sovereign':1,'knockando-12':2,'glendronach-8-hielan':1,'royal-brackla-18':1,'aultmore-21':2,'craigellachie-23':1,'chichibu-first-ten':1,'mars-maltage-cosmo':2,'fercullen-falls':1,'kavalan-distillery-select-1':2,'david-nicholson':1,'yellowstone-select':2,'kilkerran-8-cs':1,'cardhu-gold-reserve':1,'stauning':1,'rampur':1}
picks={}
for k,v in m.items():
    if not v or k in skip: continue
    n,u=v[idx.get(k,0)]
    if not u.startswith('http'): u='https://www.whiskyfun.com/'+u
    picks[k]=(n,u)
json.dump(picks,open(D+'wf_picks.json','w'),indent=1)
pages=sorted({u.split('#')[0] for n,u in picks.values()})
print(len(picks),'picks',len(pages),'pages')
os.makedirs(D+'wf',exist_ok=True)
for p in pages:
    f=D+'wf/'+p.split('/')[-1]
    if os.path.exists(f) and os.path.getsize(f)>5000: continue
    r=subprocess.run(['curl','-sSL','-m','90','-A','Mozilla/5.0 (compatible; research-fetch)','-o',f,'-w','%{http_code}',p],capture_output=True,text=True)
    if r.stdout.strip()!='200': print(r.stdout,p)
    if r.stdout.strip() in('403','429'): break
    time.sleep(2.5)
print('DONE')
