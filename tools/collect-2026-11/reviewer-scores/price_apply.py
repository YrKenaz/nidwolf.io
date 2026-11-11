#!/usr/bin/env python3
"""가격을 700ml(미국 위스키 750ml) 기준으로 정리하고 price_ml을 기록.  python3 price_apply.py [--dry]"""
import json,re,sys,collections
DRY='--dry' in sys.argv; P='../../../data/bottles.json'
B=json.load(open(P)); C=json.load(open('price_cache.json'))
JUNK=re.compile(r'세트|전용잔|잔 |패키지|바이알|기획|미니어처|x2|x 2|하드케이스')
def vol(p):
    m=re.search(r'(\d{2,4})\s*ml',p,re.I)
    if m: return int(m.group(1))
    m=re.search(r'(\d(?:\.\d+)?)\s*L\b',p)
    return int(float(m.group(1))*1000) if m else None
def base(p):
    p=re.sub(r'\[[^\]]*\]|\([^)]*\)','',p); p=re.sub(r'\d+(\.\d+)?\s*(ml|L)\b','',p,flags=re.I)
    return re.sub(r'\s+','',p)
WRONG={'chichibu-505':'가격 상품이 "몰트&그레인 월드 블렌디드"(505가 아닌 제품)','royalsalute-21':'가격 상품이 "로얄살루트 21년 몰트"(블렌디드 몰트판) 500ml'}
changed=[];cleared=[];log=[]
for b in B:
    pp=b.get('price_product'); b['price_ml']=None
    if not pp: continue
    if b['id'] in WRONG:
        cleared.append((b['id'],b['ko'],pp,b['price'],WRONG[b['id']])); b['price']=b['price_product']=b['price_date']=None; continue
    us=b['type'] in('BB','RY'); std=(750,700) if us else (700,)
    v=vol(pp); bad=bool(JUNK.search(pp)) or '구형' in pp or (v is not None and v not in ((700,750) if us else (700,)))
    if b['id'] in C and bad:
        want=base(pp.replace('바이알',''))
        if b['id']=='laphroaig-cairdeas': want=None
        cands=[]
        for y in C[b['id']]['results']:
            n=y['name']
            if JUNK.search(n) or '구형' in n or not y.get('price') or y.get('service_type')==5: continue
            if want and base(n)!=want: continue
            if not want and '카디어스' not in n: continue
            vv=vol(n) or (int(re.sub(r'\D','',y['thumbnail_display_volume'])) if y.get('thumbnail_display_volume') else None)
            cands.append((vv,y['price'],n))
        pick=None
        for s in std:
            c=[x for x in cands if x[0]==s]
            if c: pick=min(c,key=lambda x:x[1]); break
        if not pick:
            c=[x for x in cands if x[0] is None]
            if c: pick=min(c,key=lambda x:x[1])
        if pick:
            changed.append((b['id'],b['ko'],pp,b['price'],pick[2],pick[1],pick[0])); b['price'],b['price_product'],b['price_date'],b['price_ml']=pick[1],pick[2],'2026-11-11',pick[0]; continue
        if JUNK.search(pp):
            cleared.append((b['id'],b['ko'],pp,b['price'],'단품 상품을 찾지 못함')); b['price']=b['price_product']=b['price_date']=None; continue
    b['price_ml']=v
if not DRY: open(P,'w',encoding='utf-8').write('[\n'+',\n'.join(json.dumps(x,ensure_ascii=False) for x in B)+'\n]\n')
c=collections.Counter(('가격 없음' if not b['price'] else b['price_ml']) for b in B); print(dict(c))
print('바꾼 병',len(changed)); 
for x in sorted(changed,key=lambda x:-abs(x[5]-x[3])/x[3]): print('  ',x[0],x[1],'|',x[2],x[3],'→',x[4],x[5],x[6])
print('비운 병',cleared)
print('700/750 아닌 용량으로 남은 병',[(b['id'],b['price_product'],b['price_ml']) for b in B if b['price'] and b['price_ml'] and b['price_ml'] not in(700,750)])
print('미국 외 750ml',[(b['id'],b['price_product']) for b in B if b['price'] and b['price_ml']==750 and b['type'] not in('BB','RY')])
print('구형 표기 남음',[(b['id'],b['price_product']) for b in B if b['price_product'] and '구형' in b['price_product']])
