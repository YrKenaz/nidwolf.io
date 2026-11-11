#!/usr/bin/env python3
"""후보 축소본을 임시 폴더에 받아 검수용 모아보기를 만든다(저장소에 넣지 않음).  sheet.py <임시폴더> [시작번호]"""
import json,os,sys,subprocess,io,time
from PIL import Image,ImageDraw
H=os.path.dirname(os.path.abspath(__file__)); T=sys.argv[1]; os.makedirs(T+'/th',exist_ok=True)
UA='nidwolf-photo-collect/0.1 (https://nidwolf.com; bottle photos with licence and attribution)'
cand=json.load(open(H+'/candidates.json')); order=json.load(open(H+'/search.json'))
R=json.load(open(H+'/review.json')) if os.path.exists(H+'/review.json') else {}
items=[(i,n,r) for i in order if i in cand for n,r in enumerate(cand[i][:4]) if i+'|'+r['title'] not in R]
for f in os.listdir(T):
    if f.startswith('sheet_'): os.remove(T+'/'+f)
json.dump([(i,n,r['title']) for i,n,r in items],open(T+'/items.json','w'),ensure_ascii=False)
for k,(i,n,r) in enumerate(items):
    f=f"{T}/th/{i}__{n}.jpg"
    if os.path.exists(f): continue
    b=subprocess.run(['curl','-sS','-m','40','-A',UA,r['thumb']],capture_output=True).stdout
    try: Image.open(io.BytesIO(b)).convert('RGB').save(f,quality=88)
    except Exception: print('ERR',i,n)
    time.sleep(1.2)
P=8
for s in range(0,len(items),P):
    sh=Image.new('RGB',(4*330,2*400),'white'); d=ImageDraw.Draw(sh)
    for k,(i,n,r) in enumerate(items[s:s+P]):
        x,y=(k%4)*330,(k//4)*400
        try:
            im=Image.open(f"{T}/th/{i}__{n}.jpg"); im.thumbnail((320,370)); sh.paste(im,(x+5,y+24))
        except Exception: pass
        d.text((x+5,y+2),f"{s+k} {i}#{n} {r.get('year')}",fill='black'); d.text((x+5,y+12),r['license'],fill='blue')
    sh.save(f"{T}/sheet_{s//P:03d}.jpg",quality=85)
print(len(items),'장',(len(items)+P-1)//P,'시트')
