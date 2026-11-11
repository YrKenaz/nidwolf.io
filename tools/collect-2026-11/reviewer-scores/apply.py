#!/usr/bin/env python3
"""2026-11-11 리뷰어 점수 반영. 실행 위치 무관.  python3 apply.py [--dry]
입력(이 폴더): existing_obs.json(기존 병 관측값), final_2019.json(새 병 후보), ds_match.json(데일리샷 대조), calibration.json
동작: sources.json에 whiskyfun/whiskynotes/dramface 추가, 기존 병·새 병 관측값 추가, 새 병 등록, wash25 관측값 제거."""
import json,re,sys,os,collections
H=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(os.path.dirname(os.path.dirname(H))); DATA=ROOT+'/data/'
DRY='--dry' in sys.argv
src=json.load(open(DATA+'sources.json')); B=json.load(open(DATA+'bottles.json')); O=json.load(open(DATA+'observations.json'))
assert 'whiskyfun' not in src, '이미 반영됨'
cal=json.load(open(H+'/calibration.json')); ex=json.load(open(H+'/existing_obs.json')); cand=json.load(open(H+'/final_2019.json')); dsm=json.load(open(H+'/ds_match.json'))
SID={'wf':'whiskyfun','wn':'whiskynotes','df':'dramface'}
def conv(s,x): 
    c=cal[s]; return max(50.0,min(100.0,round(c['intercept']+c['slope']*x,1)))
def xval(s,o):
    if 'x' in o: return o['x']
    if s=='df':
        n=[int(v) for v in re.findall(r'(\d+)/10',o['raw'])]; return sum(n)/len(n)
    return int(re.search(r'\d\d',o['raw']).group())
def raw(s,o):
    who=(' '+o['author']) if o.get('author') and s!='wn' else ''
    return f"{o['raw']} · {o['name'][:90]} · {str(o['date'])[:10]}{who}"
IDMAP={'ardbeg-wee-beastie':'ardbeg-weebeastie','ardbeg-traigh-bhan-19':'ardbeg-19','glen-scotia-15':'glenscotia-15','glen-scotia-18':'glenscotia-18','glenfiddich-23-grand-cru':'glenfiddich-23','balvenie-16-french-oak':'balvenie-16','old-pulteney-18':'oldpulteney-18','oban-little-bay':'oban-littlebay','cardhu-gold-reserve':'cardhu-gold','deanston-virgin-oak':'deanston-virgin','ncnean-organic':'ncnean','ardnamurchan-ad':'ardnamurchan','royal-brackla-18':'royalbrackla-18','arran-quarter-cask':'arran-qc','chichibu-the-first-ten':'chichibu-first10','shizuoka-united-s':'shizuoka-united','redbreast-px-edition':'redbreast-px','gold-spot-9':'gold-spot','powers-gold-label':'powers-gold','jameson-caskmates-ipa':'jameson-ipa','knappogue-castle-12':'knappogue-12','tullamore-dew-12':'tullamore-12','tullamore-dew-14':'tullamore-14','dingle-single-malt':'dingle-sm','glendalough-double-barrel':'glendalough-db','kilbeggan-single-pot-still':'kilbeggan-sps','drumshanbo-single-pot-still':'drumshanbo-sps','kavalan-distillery-select-1':'kavalan-ds1','kavalan-distillery-select-2':'kavalan-ds2','starward-two-fold':'starward-twofold','high-coast-hav':'highcoast-hav','cotswolds-founders-choice':'cotswolds-fc','rampur-double-cask':'rampur-dc','milk-and-honey-classic':'mh-classic','milk-and-honey-elements-sherry':'mh-sherry','armorik-double-maturation':'armorik-dm','kyro-malt-rye':'kyro-rye','millstone-100-rye':'millstone-100','alberta-premium-cask-strength-rye':'alberta-cs'}
COUNTRY={'kavalan':'대만','starward':'호주','high':'스웨덴','stauning':'덴마크','cotswolds':'영국','rampur':'인도','indri':'인도','milk':'이스라엘','armorik':'프랑스','kyr':'핀란드','millstone':'네덜란드','alberta':'캐나다'}
DS_MANUAL={'ardbeg-traigh-bhan-19':'Traigh Bhan 19yo Batch','glenfiddich-23-grand-cru':'Grand Cru 23yo','arran-quarter-cask':'Arran Quarter Cask','nikka-tailored':'Nikka Tailored','dingle-single-malt':'Dingle Single Malt','kavalan-solist-fino':'Solist Fino Sherry Single Cask Strength','milk-and-honey-elements-sherry':'ELEMENTS Sherry Cask','kyro-malt-rye':'Kyro Malt Rye'}
DS_REJECT={'aberlour-14','longmorn-18','high-coast-hav','kavalan-distillery-select-2','mortlach-16','cardhu-gold-reserve','indri-agneya','ardnamurchan-ad','laphroaig-16','bladnoch-14'}
JUNK=re.compile(r'바이알|vial|세트|전용잔|미니어처|50ml|30ml|200ml|패키지|기획',re.I)
def norm(s): return re.sub(r'[^a-z0-9]','',s.lower())
reg_by_brand={}
for b in B:
    if b['type']=='SM': reg_by_brand.setdefault(norm(b['en'].split(' ')[0]+(b['en'].split(' ')[1] if b['en'].split(' ')[0] in('Glen','Old','Royal','Ben','Port','Loch','Isle','Blair','Caol') else '')),b['region'])
def ds_info(cid):
    ms=dsm.get(cid) or []
    if cid in DS_REJECT: return None
    keep=[]
    for sc,y in ms:
        en=y.get('en_name') or ''
        if JUNK.search(y['name']) or JUNK.search(en): continue
        if sc>=0.95 or (cid in DS_MANUAL and DS_MANUAL[cid].lower() in en.lower()) or (sc>=0.9 and re.search(r'1L|750ml|700ml',en)): keep.append(y)
    if not keep: return None
    prod={}
    for y in keep: prod[y.get('top_product_id') or y['id']]=y
    n=sum((y.get('review_count') or 0) for y in prod.values())
    rate=round(sum((y.get('review_rate') or 0)*(y.get('review_count') or 0) for y in prod.values())/n,1) if n else None
    std=[y for y in keep if not re.search(r'1L|1l|500ml|375ml',y['name']+(y.get('en_name') or '')) and y.get('price') and y['price']%100==0]
    p=min(std,key=lambda y:y['price']) if std else None
    return {'price':p['price'] if p else None,'price_product':p['name'] if p else None,'ds_rating':rate if n>=5 else None,'ds_reviews':n if n>=5 else None,'img_url':(p or keep[0]).get('thumbnail_image'),'names':sorted({y['name'] for y in keep})}
have={(o['bottle'],o['source']) for o in O}
add_ex=[]; 
for bid,v in ex.items():
    for s,o in v.items():
        add_ex.append({'bottle':bid,'source':SID[s],'value':conv(s,xval(s,o)),'raw':raw(s,o)})
sel=[x for x in cand if x['tier2019']=='A' or (x['tier2019']=='B' and x['type'] in('JP','IR','WD'))]
newb=[]; add_new=[]; report=[]
ids={b['id'] for b in B}
for x in sel:
    nid=IDMAP.get(x['id'],x['id']); assert nid not in ids, nid; ids.add(nid)
    obs={s:o for s,o in x['obs'].items() if s in SID and int(str(o['date'])[:4])>=2019}
    assert obs
    names=' | '.join(o['name'] for o in obs.values())
    abv=None
    for s in ('wf','wn'):
        if s in obs:
            m=re.search(r'\(([\d.,]+) ?%',obs[s]['name'])
            if m: abv=float(m.group(1).replace(',','.')); break
    if abv is None and 'df' in obs and obs['df'].get('abv'):
        m=re.search(r'([\d.]+)%',obs['df']['abv'][0]); abv=float(m.group(1)) if m else None
    m=re.search(r'\b(\d{1,2}) ?(?:yo|y\.o|years?|year old)\b',names,re.I); age=int(m.group(1)) if m else None
    brand=norm(x['en'].split(' ')[0]+(x['en'].split(' ')[1] if x['en'].split(' ')[0] in('Glen','Old','Royal','Ben','Port','Loch','Isle','Blair','Caol') else ''))
    if x['type']=='JP': region='일본'
    elif x['type']=='IR': region='아일랜드'
    elif x['type']=='WD': region=COUNTRY[norm(x['en'].split(' ')[0])]
    else: region=reg_by_brand.get(brand) or '스코틀랜드'
    style=[]
    if re.search(r'cask strength|batch strength',names+' '+x['en'],re.I): style.append('cs')
    if re.search(r'sherry|oloroso|\bPX\b|fino',x['en']+' '+(obs.get('wf',{}).get('name','').split('(')[0]),re.I): style.append('sherry')
    d=ds_info(x['id'])
    if d and 'CS' in ' '.join(d['names']) and 'cs' not in style: style.append('cs')
    b={'id':nid,'ko':x['ko'],'en':x['en'],'type':x['type'],'region':region,'age':age,'abv':abv,'style':sorted(style),'cask':[],'spec':[],'beginner':False,
       'price':d['price'] if d else None,'price_product':d['price_product'] if d else None,'price_date':'2026-11-11' if d and d['price'] else None,'img':None,'img_source':None,
       'ds_rating':d['ds_rating'] if d else None,'ds_reviews':d['ds_reviews'] if d else None}
    newb.append(b); report.append({'id':nid,'cand_id':x['id'],'region_fallback':x['type']=='SM' and brand not in reg_by_brand,'ds':d})
    for s,o in obs.items(): add_new.append({'bottle':nid,'source':SID[s],'value':conv(s,xval(s,o)),'raw':raw(s,o)})
# wash25: 단독 병의 관측값만 남기고 제거(관측값 없는 병은 build 검증 오류가 되므로)
cnt=collections.Counter(o['bottle'] for o in O); newcnt=collections.Counter(o['bottle'] for o in add_ex)
lone=[o['bottle'] for o in O if o['source']=='wash25' and cnt[o['bottle']]==1 and not newcnt[o['bottle']]]
O2=[o for o in O if o['source']!='wash25' or o['bottle'] in lone]
removed=len(O)-len(O2)
def rule(s,unit): c=cal[s]; return f"{unit} × {c['slope']} + {c['intercept']} (기존 병과의 공통 {c['n']}병에서 기존 관측값 평균과 평균·표준편차를 맞춘 선형 변환, 상관 {c['r']}). 2019년 이후 리뷰만. "
src['whiskyfun']={'name':'Whiskyfun (Serge Valentin·Angus MacRaild 시음 기록)','lang':'EN','kind':'100점 평점','url':'https://www.whiskyfun.com/','rule':rule('wf','점수')+'같은 병을 여러 번 시음했으면 가장 최근 병입분','collected':'2026-11-11','group':'whiskyfun','group_name':'Whiskyfun','in_score':True,'note':'원문 표기 SGP:xxx - NN points. 근거는 Whiskey/data/snapshots/whiskyfun__20261111.txt'}
src['whiskynotes']={'name':'WhiskyNotes (Ruben Luyten 리뷰)','lang':'EN','kind':'100점 평점','url':'https://www.whiskynotes.be/','rule':rule('wn','점수')+'같은 병의 리뷰가 여럿이면 가장 최근 것','collected':'2026-11-11','group':'whiskynotes','group_name':'WhiskyNotes','in_score':True,'note':'근거는 Whiskey/data/snapshots/whiskynotes__20261111.txt'}
src['dramface']={'name':'Dramface (필진 리뷰)','lang':'EN','kind':'10점 평점','url':'https://www.dramface.com/all-reviews','rule':rule('df','10점 척도 점수')+'한 글에 여러 명이 채점했으면 평균','collected':'2026-11-11','group':'dramface','group_name':'Dramface','in_score':True,'note':'근거는 Whiskey/data/snapshots/dramface__20261111.txt'}
if not lone: src.pop('wash25')
for o in add_ex+add_new: assert (o['bottle'],o['source']) not in have
O3=O2+add_ex+add_new; B2=B+newb
print('새 병',len(newb),dict(collections.Counter(b['type'] for b in newb)),'| 관측값 추가: 기존 병',len(add_ex),dict(collections.Counter(o['source'] for o in add_ex)),'새 병',len(add_new),dict(collections.Counter(o['source'] for o in add_new)),'| wash25 제거',removed,'남김',len(lone),lone)
print('데일리샷 확인',sum(1 for r in report if r['ds']),'미확인',sum(1 for r in report if not r['ds']),'| 지역 대체(스코틀랜드)',[r['id'] for r in report if r['region_fallback']])
json.dump({'new_bottles':report,'wash25_kept':lone},open(H+'/apply_report.json','w'),ensure_ascii=False,indent=1)
if not DRY:
    def lines(a): return '[\n'+',\n'.join(json.dumps(x,ensure_ascii=False) for x in a)+'\n]\n'
    open(DATA+'bottles.json','w',encoding='utf-8').write(lines(B2)); open(DATA+'observations.json','w',encoding='utf-8').write(lines(O3))
    open(DATA+'sources.json','w',encoding='utf-8').write(json.dumps(src,ensure_ascii=False,indent=1)+'\n'); print('written')
