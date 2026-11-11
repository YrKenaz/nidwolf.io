#!/usr/bin/env python3
"""검수에서 채택한 사진을 받아 img/<id>.webp로 저장하고 bottles.json에 저작자 표시 필드를 기록.  apply_img.py <임시폴더>"""
import json,os,sys,subprocess,io,time
from PIL import Image,ImageOps
H=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(os.path.dirname(os.path.dirname(H))); T=sys.argv[1]; os.makedirs(T+'/orig',exist_ok=True); os.makedirs(ROOT+'/img',exist_ok=True)
UA='nidwolf-photo-collect/0.1 (https://nidwolf.com; bottle photos with licence and attribution)'
R=json.load(open(H+'/review.json')); CROP=json.load(open(H+'/crops.json'))
pool={}
for f in ('candidates.json','user_candidates.json'):
    if os.path.exists(H+'/'+f):
        for i,rows in json.load(open(H+'/'+f)).items():
            for r in rows: pool[i+'|'+r['title']]=r
B=json.load(open(ROOT+'/data/bottles.json')); by={b['id']:b for b in B}
picked={}
for key,v in R.items():
    if v['verdict'] in('Y','C'):
        assert v['bottle'] not in picked, v['bottle']; picked[v['bottle']]=(key,v)
LURL={'Public domain':None}
n=0
for i,(key,v) in picked.items():
    r=pool[key]; f=T+'/orig/'+i
    if not os.path.exists(f):
        b=subprocess.run(['curl','-sSL','-m','120','-A',UA,r['url']],capture_output=True).stdout; open(f,'wb').write(b); time.sleep(2)
    im=ImageOps.exif_transpose(Image.open(f)); im=im.convert('RGBA'); bg=Image.new('RGBA',im.size,'white'); bg.alpha_composite(im); im=bg.convert('RGB')
    ch=['크기 축소','WebP 변환']
    if v['verdict']=='C':
        x0,y0,x1,y1=CROP[i]; w,h=im.size; im=im.crop((int(x0*w),int(y0*h),int(x1*w),int(y1*h))); ch.insert(0,'잘라 냄')
    im.thumbnail((340,340),Image.LANCZOS); im.save(f"{ROOT}/img/{i}.webp",'WEBP',quality=82,method=6)
    b=by[i]; b.update(img=f'img/{i}.webp',img_source='Wikimedia Commons',img_author=r['artist'] or r['uploader'],img_license=r['license'],img_license_url=r['license_url'] or None,img_page=r['page'],img_changes=', '.join(ch)); n+=1
open(ROOT+'/data/bottles.json','w',encoding='utf-8').write('[\n'+',\n'.join(json.dumps(x,ensure_ascii=False) for x in B)+'\n]\n')
print(n,'장 반영'); json.dump({i:{'title':v['title'],'page':v['page'],'why':v['why']} for i,(k,v) in picked.items()},open(H+'/picked.json','w'),ensure_ascii=False,indent=1)
