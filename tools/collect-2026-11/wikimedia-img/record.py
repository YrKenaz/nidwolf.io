#!/usr/bin/env python3
"""눈 검수 결과 기록.  record.py <임시폴더> 'k:판정:사유' ...   판정 Y=채택 C=잘라서 채택 N=제외. 적지 않은 번호는 'N:병 사진 아님'."""
import json,os,sys
H=os.path.dirname(os.path.abspath(__file__)); T=sys.argv[1]
items=json.load(open(T+'/items.json')); cand=json.load(open(H+'/candidates.json'))
R=json.load(open(H+'/review.json')) if os.path.exists(H+'/review.json') else {}
given={}
for a in sys.argv[2:]:
    k,v,why=a.split(':',2); given[int(k)]=(v,why)
done=set(json.load(open(T+'/done.json'))) if os.path.exists(T+'/done.json') else set()
for k,(i,n,title) in enumerate(items):
    key=i+'|'+title
    if key in R and k not in given: continue
    v,why=given.get(k,('N','병 사진 아님 또는 다른 대상'))
    r=next(x for x in cand[i] if x['title']==title)
    R[key]={'bottle':i,'title':title,'page':r['page'],'verdict':v,'why':why}
json.dump(R,open(H+'/review.json','w'),ensure_ascii=False,indent=1)
import collections; print(collections.Counter(x['verdict'] for x in R.values()))
