import json,sys,os,re,io,subprocess,collections,statistics as st
from PIL import Image
S,R=sys.argv[1],sys.argv[2]
def load(p): return json.load(open(p,encoding='utf-8'))
def dump(o,p):
    with open(p,'w',encoding='utf-8') as f:
        if isinstance(o,list): f.write('[\n'+',\n'.join(json.dumps(x,ensure_ascii=False) for x in o)+'\n]\n')
        else: json.dump(o,f,ensure_ascii=False,indent=1); f.write('\n')
src=load(R+'/data/sources.json'); B=load(R+'/data/bottles.json'); O=load(R+'/data/observations.json')
GROUP={'winter':('winter','윈터/위스키코냑클럽'),'dcintro':('dc','세계 주류 마이너 갤러리'),'boozemakers':('boozemakers','BoozeMakers'),'wash25':('whiskeywash','The Whiskey Wash'),'minnick10':('minnick','Fred Minnick'),'vinepair26':('vinepair','VinePair')}
for k,s in src.items():
    g=GROUP.get(k) or (('uproxx','Uproxx') if k.startswith('uproxx') else ('manofmany','Man of Many'))
    s['group'],s['group_name']=g
    s['in_score']=k not in ('dcintro','wash25','mom_scotch','mom_jp')
    if not s['in_score']:
        s['kind']='추천 목록'; s['rule']='점수에 넣지 않고 추천 횟수로만 센다'
src['mom_scotch']['name']='Man of Many — 24 Best Scotch Whiskies'; src['mom_jp']['name']='Man of Many — 12 Best Japanese Whiskies'
for o in O:
    if not src[o['source']]['in_score']:
        o['value']=None
        if o['source'].startswith('mom_'): o['raw']='추천 목록 포함 ('+o['raw'].replace('개 중 ','선 중 ').replace('위','번째')+')'
# --- WhiskyAnalysis
rows={r['name']:r for r in load(S+'/wa_rows.json')}; fin=load(S+'/wa_final.json')
new=[l.rstrip('\n').split('|') for l in open(S+'/tools/wa_new.txt',encoding='utf-8')]
by=collections.defaultdict(lambda: collections.defaultdict(list))
for o in O:
    if o['value'] is not None: by[o['bottle']][src[o['source']]['group']].append(o['value'])
xs,ys=[],[]
for i,n in fin.items():
    g=[sum(v)/len(v) for v in by[i].values()]
    if len(g)>=2 and rows[n]['n']>=8: xs.append(rows[n]['meta']); ys.append(sum(g)/len(g))
b=st.pstdev(ys)/st.pstdev(xs); a=st.mean(ys)-b*st.mean(xs)
print('calib n',len(xs),'a',round(a,2),'b',round(b,2),'corr',round(st.correlation(xs,ys),2))
conv=lambda m: round(a+b*m,1)
src['whiskyanalysis']={"name":"WhiskyAnalysis Meta-Critic (리뷰어 다수의 정규화 합의 점수)","lang":"EN","kind":"메타 평점","url":"https://whiskyanalysis.com/index.php/database/","rule":f"메타 점수 × {b:.2f} + {a:.1f} (공통 {len(xs)}병의 평균·표준편차를 맞춘 선형 변환). 리뷰어 3명 이상인 항목만","collected":"2026-11-11","group":"whiskyanalysis","group_name":"WhiskyAnalysis","in_score":True,"note":"표 최종 갱신 2023-01-20. 리뉴얼된 제품은 구판 평가일 수 있다."}
O=[o for o in O if o['source']!='whiskyanalysis']
def wa_obs(i,n):
    r=rows[n]; O.append({"bottle":i,"source":"whiskyanalysis","value":conv(r['meta']),"raw":f"메타 {r['meta']:.2f} (리뷰어 {r['n']}명) · {n}"})
for i,n in fin.items(): wa_obs(i,n)
# --- 신규 병
C2=load(S+'/ds2.json'); REJ2=set("benriach-curiositas cb-flaming-heart hp-10 laphroaig-triplewood grouse-smoky tullamore-dew green-spot connemara redbreast-12cs redbreast-21 redbreast-lustau tyrconnell yellow-spot nikka-coffey-grain nikka-coffey-malt yamazaki-dr hakushu-dr elmer-t-lee kc-sib george-dickel-12 pikesville balcones-sm westland-ao crown-royal-nhr lot-40 wisers-18 amrut-kadhambam pauljohn-edited".split())
have={x['id'] for x in B}
def mkimg(url,i):
    raw=subprocess.run(['curl','-sL','-m','40',url],capture_output=True).stdout
    im=Image.open(io.BytesIO(raw)).convert('RGBA'); bg=Image.new('RGBA',im.size,'white'); bg.alpha_composite(im); im=bg.convert('RGB'); im.thumbnail((340,340),Image.LANCZOS)
    im.save(f"{R}/img/{i}.webp",'WEBP',quality=80,method=6)
for i,ko,en,ty,rg,wn,at in new:
    if i in have: continue
    a_=at.split(); fl=set(a_[1:]); m=re.search(r'(\d+)년',ko); c=C2.get(i,{}).get('match') if i not in REJ2 else None
    img=None
    if c:
        try: mkimg(c[3],i); img=f"img/{i}.webp"
        except Exception as e: print('IMG ERR',i,e)
    B.append({"id":i,"ko":ko,"en":en,"type":ty,"region":rg,"age":int(m.group(1)) if m else None,"abv":float(a_[0]),
      "style":[k for k,x in (('peat','P'),('sherry','S'),('cs','C')) if x in fl],"cask":[k for k,x in (('bourbon','b'),('wine','w'),('rum','r'),('mizunara','m')) if x in fl],
      "spec":[x for x in ('SiB','SmB','BiB','BP','Wh') if x in fl],"beginner":False,
      "price":c[6] if c and c[6] else None,"price_product":c[7] if c and c[6] else None,"price_date":"2026-11-11" if c and c[6] else None,
      "img":img,"img_source":"데일리샷 상품 이미지" if img else None})
    wa_obs(i,wn)
# --- 데일리샷 이용자 평점(참고 정보)
C1=load(S+'/ds.json'); REJ1=set(load(S+'/tools/rej.json'))
for x in B:
    i=x['id']; c=(C1.get(i,{}).get('match') if i not in REJ1 else None) or (C2.get(i,{}).get('match') if i not in REJ2 else None)
    ok=c and c[4] and c[5] and c[5]>=5
    x['ds_rating']=round(c[4],2) if ok else None; x['ds_reviews']=c[5] if ok else None
B.sort(key=lambda x:x['id'])
dump(src,R+'/data/sources.json'); dump(B,R+'/data/bottles.json'); dump(O,R+'/data/observations.json')
print(len(B),'bottles',len(O),'obs','img',sum(1 for x in B if x['img']),'rating',sum(1 for x in B if x['ds_rating']))
