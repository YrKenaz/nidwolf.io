#!/usr/bin/env python3
"""검색 결과를 기준에 맞게 기계 선별. candidates.json(통과)과 rejected.json(사유별)을 만든다."""
import json,re,os,unicodedata,collections,sys
H=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(os.path.dirname(os.path.dirname(H)))
B={b['id']:b for b in json.load(open(ROOT+'/data/bottles.json'))}
S=json.load(open(H+'/search.json'))
if os.path.exists(H+'/catsearch.json'):
    for k,v in json.load(open(H+'/catsearch.json')).items():
        S.setdefault(k,{'rows':[]}); seen={r['title'] for r in S[k]['rows']}; S[k]['rows']+=[r for r in v['rows'] if r['title'] not in seen]
def norm(s):
    s=s.replace('’',"'"); s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
    s=s.replace("'s",'s').replace('&',' and ').replace('d.e.w.','dew')
    return re.sub(r'[^a-z0-9]+',' ',s).strip()
STOP={'the','year','years','old','yo','single','malt','whisky','whiskey','scotch','label','edition','of','and','straight','kentucky','bourbon','no','us','1'}
LIC=re.compile(r'^(CC0|Public domain|CC BY(-SA)? \d)',re.I)
BAD=re.compile(r'distiller|brennerei|usine|statue|building|warehouse|logo|wordmark|\bsign\b|pot still|stills|advert|poster|truck|\bbus\b|racing|nascar|\bmap\b|visitor|museum|\bshop\b|store|shelf|shelves|collection|line.?up|range|bottles of|tasting|flight|\bbar\b|glass of|cocktail|empty|leer|miniature|\bad\b|ads\b|display',re.I)
cand={}; rej=collections.Counter(); rejlog=[]
for i,v in S.items():
    b=B.get(i)
    if not b: continue
    toks=[t for t in norm(b['en']).split() if t not in STOP]
    c=[]
    for r in v['rows']:
        text=norm(r['title']+' '+r['desc']); tt=set(text.split())
        why=None
        if r['mime'] not in('image/jpeg','image/png'): why='형식'
        elif not all((t in tt) or (t.isdigit() and re.search(r'\b'+t+r' ?(y|yo|years?|jahre|ans|anos|anni|jaar)\b',text)) for t in toks): why='다른 병(이름 불일치)'
        elif not LIC.match(r['license'] or '') or re.search(r'NC|ND',r['license'] or ''): why='라이선스'
        elif 'own work' not in (r['credit'] or '').lower(): why='라이선스(다른 곳에서 가져온 사진)'
        elif BAD.search(r['title']+' '+r['desc'][:120]): why='상태 불량(병 단독 사진 아님)'
        elif not re.search(r'bottle|flasche|bouteille|botella|bottiglia|\bfles\b|whisk|bourbon|scotch|ボトル|ウイスキー|위스키|威士忌',(r['title']+' '+r['desc']+' '+r.get('cats','')),re.I): why='상태 불량(병 단독 사진 아님)'
        else:
            y=None
            m=re.search(r'(19|20)\d\d',r['taken'] or '') or re.search(r'(19|20)\d\d',r['uploaded'] or '')
            y=int(m.group(0)) if m else None; r['year']=y
            if not y or y<2019: why='옛 라벨 가능성(촬영·게시 2018년 이전)'
        if why:
            rej[why]+=1
            if why!='다른 병(이름 불일치)' and why!='형식': rejlog.append({'bottle':i,'title':r['title'],'page':r['page'],'why':why})
        else: c.append(r)
    if c: cand[i]=c
json.dump(cand,open(H+'/candidates.json','w'),ensure_ascii=False,indent=1); json.dump({'counts':rej,'log':rejlog},open(H+'/rejected_machine.json','w'),ensure_ascii=False,indent=1)
print(len(S),'병 검색 /',sum(len(v['rows']) for v in S.values()),'건 →',len(cand),'병',sum(len(c) for c in cand.values()),'장 통과'); print(dict(rej))
