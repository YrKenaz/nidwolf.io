import json,re,sys,unicodedata,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from master import M,DC
S=sys.argv[1]; src=json.load(open(S+'/sources.json'))
def norm(s):
    s=unicodedata.normalize('NFKD',s); s=''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+',' ',s.replace('’',"'").replace('‘',"'").lower()).strip()
# extra sources
t=open(S+'/dl/booze_scotch.html',encoding='utf-8').read()
bzs=[(norm(re.sub(r'<[^>]+>','',a)),float(b)) for a,b in re.findall(r'<h2[^>]*>\s*\d+\.\s*(.*?)\s*(?:—|&mdash;|-)\s*(\d+)/100',t)]
names_bz={norm(e['name']) for e in src['boozemakers']}
for n,sc in bzs: src['boozemakers'].append({'name':n,'score':sc,'img':None,'lists':['top-10-scotch-2026']})
src['minnick10']=[{'rank':r,'name':n} for r,n in [(10,"Maker's Mark Cask Strength"),(9,"Elijah Craig Small Batch"),(8,"Evan Williams Bottled-in-Bond"),(7,"Wild Turkey 101"),(6,"Buffalo Trace"),(5,"Four Roses Small Batch"),(4,"Old Forester 100 Proof"),(3,"Knob Creek 9 Year"),(2,"Russell's Reserve 10 Year"),(1,"Old Grand-Dad 114")]]
src['vinepair26']=[{'name':"Russell's Reserve 10-Year-Old Bourbon",'score':94},{'name':"Monkey Shoulder Blended Malt Scotch Whisky",'score':91},{'name':"The Balvenie Single Barrel 12 Year Old",'score':94},{'name':"FUJI Single Grain",'score':91}]
def lin(top,bot,n): return lambda e:(top-(top-bot)*(e['rank']-1)/(n-1))
CONV={'uproxx_scotch100':lin(94,82,100),'uproxx_bourbon100':lin(96,86,100),'uproxx_sm10':lin(95,89,10),'uproxx_irish20':lin(95,86,20),'uproxx_intl35':lin(96,88,35),
 'mom_scotch':lin(92,86,24),'mom_jp':lin(92,86,12),'wash25':lambda e:89,'minnick10':lin(92,86,10),'vinepair26':lambda e:e['score'],'boozemakers':lambda e:e['score']}
META={'winter':('위스키 종합 티어 리스트 (윈터 / 위스키코냑클럽)','KR','점수표','https://www.fmkorea.com/8231491027'),
 'dcintro':('입문자를 위한 위스키 추천제품 v02 (세계 주류 마이너 갤러리)','KR','추천 목록','https://m.dcinside.com/board/nuncestbibendum/6464'),
 'boozemakers':('BoozeMakers 2026 리뷰·랭킹 (13개 리스트)','EN','100점 평점','https://www.boozemakers.com/articles/top-10-scotch-2026'),
 'uproxx_scotch100':('Uproxx — 100 Best Scotch Under $100','EN','순위','https://uproxx.com/life/100-best-scotch-whiskeys-under-100-ranked-2023'),
 'uproxx_sm10':('Uproxx — Sipping Single Malts Under $100','EN','순위','https://uproxx.com/life/best-sipping-single-malt-whisky-under-100-ranked'),
 'uproxx_bourbon100':('Uproxx — 100 Best Bourbons of 2025','EN','순위','https://uproxx.com/life/100-best-bourbons-of-2025/'),
 'uproxx_irish20':('Uproxx — 20 Best Irish Whiskeys','EN','순위','https://uproxx.com/life/20-best-irish-whiskeys-ranked-march-2024/'),
 'uproxx_intl35':('Uproxx — 35 Best International Whiskeys','EN','순위','https://uproxx.com/life/best-international-whiskeys-of-2023-list/'),
 'mom_scotch':('Man of Many — 24 Best Scotch Whiskies','EN','순위','https://manofmany.com/culture/drinks/best-scotch-whisky-brands'),
 'mom_jp':('Man of Many — 12 Best Japanese Whiskies','EN','순위','https://manofmany.com/culture/drinks/best-japanese-whisky'),
 'wash25':('The Whiskey Wash — 25 American Whiskeys for 2026','EN','추천 목록','https://thewhiskeywash.com/whiskey-articles/25-american-whiskeys-to-try-in-2026-ranked-by-type-of-drinker/'),
 'minnick10':('Fred Minnick — 10 Best Bourbons Around $40','EN','순위','https://www.fredminnick.com/2022/03/20/10-best-bourbons-around-40-ranked/'),
 'vinepair26':('VinePair — Best Whiskeys to Drink in 2026','EN','부문 선정','https://vinepair.com/buy-this-booze/best-whiskey-brands-2026/')}
W={}
for (i,ko,en,ty,rg,w,rx,ex) in M:
    W[i]={'id':i,'ko':ko,'en':en,'type':ty,'region':rg,'scores':{},'imgs':[],'raw':{}}
    if w is not None: W[i]['scores']['winter']=float(w); W[i]['raw']['winter']=('79점 이하 (E)' if w==78 else f'{w:g}점')
for i in DC: W[i]['scores']['dcintro']=87.0; W[i]['raw']['dcintro']='추천 목록 포함'
unm={}
for k,conv in CONV.items():
    agg={}; rawl={}
    for e in src[k]:
        n=norm(e['name']); hit=None
        for (i,ko,en,ty,rg,w,rx,ex) in M:
            if rx and re.search(rx,n) and not (ex and re.search(ex,n)): hit=i;break
        if not hit: unm.setdefault(k,[]).append(e['name']); continue
        agg.setdefault(hit,[]).append(conv(e)); rawl.setdefault(hit,[]).append(e)
        if e.get('img'): W[hit]['imgs'].append((k,e['img']))
    for i,v in agg.items():
        W[i]['scores'][k]=round(sum(v)/len(v),1); es=rawl[i]
        if 'rank' in es[0]: W[i]['raw'][k]=f"{len(src[k]) if k!='uproxx_scotch100' else 100}개 중 {min(e['rank'] for e in es)}위"
        elif k=='boozemakers': W[i]['raw'][k]=(f"{es[0]['score']:g}점" if len(es)==1 else f"리뷰 {len(es)}건 평균 {sum(e['score'] for e in es)/len(es):.1f}점")
        elif k=='vinepair26': W[i]['raw'][k]='부문 1위' if es[0]['score']>=94 else '부문 차점(Honorable Mention)'
        else: W[i]['raw'][k]='추천 목록 포함'
PRIOR,K=86.0,1.0
WL={'redbreast-12','jameson','teeling-sb','bushmills-12','rittenhouse','kc-rye','michters-rye','highwest-dr','yoichi','toki','amrut-fusion','chita','kakubin','taketsuru','wlw','pappy-15','westward-sm','famous-grouse','jw-red','cc-12','green-spot-lb','eht-sb','glenfiddich-18','glenlivet-18','glenmorangie-18','ballantines-21','royalsalute-21','ballantines-17','starward-solera','teeling-blackpitts','suntory-ao','glenfiddich-15','springbank-15','bowmore-18','aberlour-12','tamdhu-12','glendronach-cs','1792-fp','kavalan-exbourbon','glendronach-18'}
out=[]
for i,w in W.items():
    n=len(w['scores'])
    if n==0: continue
    if n<2 and i not in WL: continue
    sc=(sum(w['scores'].values())+K*PRIOR)/(n+K)
    w['score']=round(sc,1); w['n']=n; out.append(w)
out.sort(key=lambda w:-w['score'])
def tier(s): return 'S' if s>=91 else 'A' if s>=89.5 else 'B' if s>=88.5 else 'C' if s>=87.5 else 'D' if s>=86 else 'E'
for w in out: w['tier']=tier(w['score'])
json.dump({'whiskies':out,'meta':META},open(S+'/result.json','w'),ensure_ascii=False,indent=1)
if len(sys.argv)>2:
    for k,v in unm.items(): print('UNMATCHED',k,len(v),'|'.join(x[:38] for x in v[:70]))
import collections
print(len(out),collections.Counter(w['tier'] for w in out),collections.Counter(w['type'] for w in out))
for w in out: print(w['tier'],w['score'],w['n'],w['type'],w['ko'],'|',' '.join(f"{k[:6]}={v}" for k,v in w['scores'].items()),'| img',len(w['imgs']))
