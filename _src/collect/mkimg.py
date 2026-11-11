import json,sys,os,base64,io,glob
from PIL import Image
S=sys.argv[1]; R=json.load(open(S+'/result.json')); C=json.load(open(S+'/ds.json'))
REJ={'angels-envy','of-birthday','ogd-bib','pappy-15','toki','laphroaig-10'}
out={}; srcs={}
for w in R['whiskies']:
    i=w['id']; f=None; s=None
    ds=f"{S}/dsimg/{i}.webp"
    if i not in REJ and C.get(i,{}).get('match') and os.path.exists(ds): f=ds; s='데일리샷 상품 이미지'
    else:
        for pref,label in (('boozemakers','BoozeMakers'),('mom_','Man of Many'),('uproxx_bourbon','Uproxx')):
            c=[x for x in sorted(glob.glob(f"{S}/img/{i}__{pref}*")) if os.path.getsize(x)>0]
            if c: f=c[0]; s=label+' 기사 이미지'; break
    if not f: print('NOIMG',i); continue
    im=Image.open(f).convert('RGBA'); bg=Image.new('RGBA',im.size,'white'); bg.alpha_composite(im); im=bg.convert('RGB')
    im.thumbnail((340,340),Image.LANCZOS); b=io.BytesIO(); im.save(b,'WEBP',quality=80,method=6)
    out[i]='data:image/webp;base64,'+base64.b64encode(b.getvalue()).decode(); srcs[i]=s
json.dump({'img':out,'src':srcs},open(S+'/images.json','w'))
print(len(out),sum(len(v) for v in out.values())//1024,'KB')
