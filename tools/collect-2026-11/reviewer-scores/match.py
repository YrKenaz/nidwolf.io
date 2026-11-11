import re,sys,json
sys.path.insert(0,sys.argv[1]+'/bin')
from targets import T
from t import txt
D=sys.argv[1]+'/dl/'
urls={k:[u.strip() for u in open(D+k+'_urls.txt')] for k in ['wn','df','ww','bb']}
urls['ww']=[u for u in urls['ww'] if 'review' in u or '/whiskey-reviews/' in u]
urls['wn']=[u for u in urls['wn'] if '/whisky-news/' not in u and int(u.split('/')[3])>=2015]
wf={}
for f in ['American-whisky','Irish-whisky','Japanese-whisky','world-whisky','blended-whisky','vatted-or-undisclosed']:
    h=open(D+'www.whiskyfun.com_'+f+'.html','rb').read().decode('latin-1')
    for li in re.findall(r'(?is)<li[^>]*>(.*?)</li>',h):
        m=re.findall(r'href="([^"]*archive[^"]*)"',li)
        import html as H
        name=re.sub(r'\s+',' ',H.unescape(re.sub(r'<[^>]+>',' ',li))).strip()
        if m: wf[name]=m[-1]
json.dump(wf,open(D+'wf_index.json','w'))
out={}
for id,en,ty,slug,wfre in T:
    r={}
    for k,us in urls.items():
        ms=[u for u in us if re.search(slug,u.rstrip('/').split('/',3)[-1] if k!='wn' else u,re.I)]
        ms.sort(key=lambda u:(len(u.rstrip('/').split('/')[-1]),u))
        if k in('wn','df'): ms.sort(key=lambda u:-int((re.search(r'/(20\d\d)/',u) or re.search('(0)','0')).group(1)))
        r[k]=ms[:2]
    w=[(n,u) for n,u in wf.items() if re.search(wfre,n)]
    def yr(u):
        m=re.search(r'#(\d{6})',u); 
        return int(m.group(1)[4:6]) if m else 0
    w=[x for x in w if yr(x[1])>=15]; w.sort(key=lambda x:-yr(x[1]))
    r['wf']=w[:2]
    out[id]=r
    print(id,'|',' '.join(k+':'+str(len(v)) for k,v in r.items()))
json.dump(out,open(D+'matches.json','w'),indent=1)
