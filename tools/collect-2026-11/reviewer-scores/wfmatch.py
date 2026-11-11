import re,sys,json,glob,html as H
sys.path.insert(0,sys.argv[1]+'/bin')
from targets import T
D=sys.argv[1]+'/dl/'
wf={}
for f in glob.glob(D+'www.whiskyfun.com_*.html'):
    if 'FTC' in f: continue
    h=open(f,'rb').read().decode('latin-1')
    for li in re.findall(r'(?is)<li[^>]*>(.*?)</li>',h):
        m=re.findall(r'href="([^"]*archive[^"]*)"',li)
        name=re.sub(r'\s+',' ',H.unescape(re.sub(r'<[^>]+>',' ',li))).strip()
        if m and len(name)<300: wf[name]=m[-1]
def yr(u):
    m=re.search(r'#(\d{6})',u); return int(m.group(1)[4:6]) if m else 0
out={}
for id,en,ty,slug,wfre in T:
    w=[(n,u) for n,u in wf.items() if re.search(wfre,n) and yr(u)>=15 and yr(u)<=26]
    w.sort(key=lambda x:-yr(x[1])); out[id]=w[:3]
    if w: print(id,'||',' ## '.join(n[:95]+' @'+u.split('#')[-1] for n,u in w[:3]))
json.dump(out,open(D+'wf_matches.json','w'),indent=1)
