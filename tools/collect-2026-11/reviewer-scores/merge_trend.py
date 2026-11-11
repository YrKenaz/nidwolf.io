#!/usr/bin/env python3
"""트렌드 발견 병 합치기, ds_reviews 정정, 카발란 올로로소 정정, 이미지 받기.  python3 merge_trend.py [--dry]"""
import json,re,sys,os,io,subprocess,collections,tempfile,shutil
H=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(os.path.dirname(os.path.dirname(H))); DATA=ROOT+'/data/'; TD=ROOT+'/tools/trend-data/'
DRY='--dry' in sys.argv
B=json.load(open(DATA+'bottles.json')); O=json.load(open(DATA+'observations.json')); src=json.load(open(DATA+'sources.json'))
N=json.load(open(TD+'new_bottles.json')); notes=json.load(open(TD+'new_bottles_notes.json')); merged=json.load(open(TD+'ds_merged.json'))
cal=json.load(open(H+'/calibration.json')); rep=json.load(open(H+'/apply_report.json')); cand={x['id']:x for x in json.load(open(H+'/final_2019.json'))}
RENAME={'ardbeg-weebeastie':'ardbeg-wee-beastie','arran-qc':'arran-quarter'}
SAME={'ardbeg-wee-beastie','arran-quarter','kavalan-ds1','mortlach-16'}
for b in B: b['id']=RENAME.get(b['id'],b['id'])
for o in O: o['bottle']=RENAME.get(o['bottle'],o['bottle'])
by={b['id']:b for b in B}
imgurl={}
for r in rep['new_bottles']:
    i=RENAME.get(r['id'],r['id'])
    if r['ds'] and r['ds'].get('img_url'): imgurl[i]=r['ds']['img_url']
added=[];held=[];over=[]
for n in N:
    u=notes.get(n['id'],{}).get('img_url')
    if n['id'] in SAME:
        b=by[n['id']]
        for k in('price','price_product','price_date','ds_rating','ds_reviews'): b[k]=n[k]
        if u: imgurl[n['id']]=u
        over.append(n['id']); continue
    assert n['id'] not in by
    if n['id']=='jw-black-ruby':
        o=cand['jw-black-ruby']['obs']['df']; c=cal['df']
        B.append(n); by[n['id']]=n; added.append(n['id'])
        O.append({'bottle':n['id'],'source':'dramface','value':round(c['intercept']+c['slope']*5,1),'raw':f"{o['raw']} · {o['name'][:90]} · {str(o['date'])[:10]}"})
        if u: imgurl[n['id']]=u
    else: held.append(n)
# ds_reviews 정정
changed=[]
for i,m in merged.items():
    if i in('akashi','angels-envy') or i not in by: continue
    b=by[i]; r=m.get('reviews')
    if r and r>=5 and b.get('ds_rating') is not None and b.get('ds_reviews')!=r: changed.append((i,b.get('ds_reviews'),r)); b['ds_reviews']=r
k=by['kavalan-oloroso']
for f in('price','price_product','price_date','ds_rating','ds_reviews','img','img_source'): k[f]=None
# 이미지
from PIL import Image
noimg=[]; got=[]
def fetch(i,u,outdir):
    p=subprocess.run(['curl','-sSL','-m','40','-A','Mozilla/5.0 (compatible; research-fetch)',u],capture_output=True)
    try:
        im=Image.open(io.BytesIO(p.stdout)).convert('RGBA'); bg=Image.new('RGBA',im.size,'white'); bg.alpha_composite(im); im=bg.convert('RGB'); im.thumbnail((340,340),Image.LANCZOS)
        os.makedirs(outdir,exist_ok=True); im.save(outdir+'/'+i+'.webp','WEBP',quality=80,method=6); return True
    except Exception as e: return False
if not DRY:
    import time
    for i,u in imgurl.items():
        if fetch(i,u,ROOT+'/img'): by[i]['img']='img/'+i+'.webp'; by[i]['img_source']='데일리샷 상품 이미지'; got.append(i)
        else: noimg.append(i)
        time.sleep(1)
    for n in held:
        u=notes.get(n['id'],{}).get('img_url')
        if not(u and fetch(n['id'],u,H+'/staged-img')): noimg.append(n['id'])
        time.sleep(1)
    def lines(a): return '[\n'+',\n'.join(json.dumps(x,ensure_ascii=False) for x in a)+'\n]\n'
    open(DATA+'bottles.json','w',encoding='utf-8').write(lines(B)); open(DATA+'observations.json','w',encoding='utf-8').write(lines(O))
    open(H+'/staged_trend_bottles.json','w',encoding='utf-8').write(lines(held))
print('겹침(한 번만 등록)',over,'| 등록',added,'| 보류(관측값 없음)',len(held),[n['id'] for n in held])
print('ds_reviews 변경',len(changed),changed[:8]); print('이미지 받음',len(got),'못 받음',noimg)
