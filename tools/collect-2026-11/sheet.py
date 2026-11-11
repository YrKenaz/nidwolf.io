import sys,glob,os
from PIL import Image,ImageDraw
files=sorted(sys.argv[3:]); out=sys.argv[1]; cols=int(sys.argv[2]); T=150
per=cols*6
for s in range(0,len(files),per):
    fs=files[s:s+per]; rows=(len(fs)+cols-1)//cols
    sh=Image.new('RGB',(cols*T,rows*(T+14)),'white'); d=ImageDraw.Draw(sh)
    for k,f in enumerate(fs):
        try:
            im=Image.open(f).convert('RGBA'); bg=Image.new('RGBA',im.size,'white'); bg.alpha_composite(im); im=bg.convert('RGB'); im.thumbnail((T-4,T-4))
            x=(k%cols)*T; y=(k//cols)*(T+14); sh.paste(im,(x+(T-im.width)//2,y))
        except Exception as e: pass
        d.text(((k%cols)*T+2,(k//cols)*(T+14)+T),os.path.basename(f)[:24],fill='black')
    sh.save(f"{out}_{s//per}.jpg",quality=85)
print((len(files)+per-1)//per)
