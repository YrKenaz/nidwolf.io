import sys,re,os,json,html as H
sys.path.insert(0,sys.argv[1]+'/bin')
from t import txt
D=sys.argv[1]+'/dl/'
res={}
for f in sorted(os.listdir(D+'pg')):
    src=f[:2]; h=open(D+'pg/'+f,'rb').read().decode('utf-8','replace'); t=txt(D+'pg/'+f)
    title=re.search(r'(?is)<title>(.*?)</title>',h); title=H.unescape(title.group(1)).strip() if title else ''
    d={'title':title}
    date=re.search(r'"datePublished":"([^"]+)"',h) or re.search(r'article:published_time" content="([^"]+)"',h)
    d['date']=date.group(1)[:10] if date else None
    if src=='bb':
        m=re.search(r'text-block-214">([^<]*)<',h); d['score']=m.group(1) if m else None
        a=re.search(r'Written By: ([^<]+)<',h); d['author']=a.group(1) if a else None
        dt=re.search(r'class="text-block-5">([^<]+)<',h); d['date']=dt.group(1) if dt else None
        for k in ['Proof','Age','Classification','Released','Distillery']:
            m=re.search(k+r':\s*([^\n]+)',t); d[k]=m.group(1).strip() if m else None
    elif src=='df':
        d['scores']=re.findall(r'Score:\s*([\d.]+/10)',t)
        m=re.search(r'Written by ([^\n|]+)',t); d['author']=m.group(1).strip() if m else None
        d['abv']=re.findall(r'[\d.]+% ABV',t)[:3]
    elif src=='wn':
        d['scores']=re.findall(r'class="entry-score">([^<]*)<',h)
        d['heads']=re.findall(r'\n ?([^\n]{5,90}\([\d.,]+ ?%, [^\n)]{2,80}\))',t)[:4]
    elif src=='ww':
        m=re.search(r'OVERALL RATING\s*\n\s*([\d.]+)',t); d['score']=m.group(1) if m else None
        d['alt']=re.findall(r'(?i)(?:score|rating)[^\n]{0,15}?(\d{1,3}(?:\.\d)?\s*/\s*(?:10|100|5))',t)[:3]
        a=re.search(r'"author":\{[^}]*"name":"([^"]+)"',h); d['author']=a.group(1) if a else None
    res[f]=d
json.dump(res,open(D+'px.json','w'),indent=1,ensure_ascii=False)
import collections
for s in ['bb','df','wn','ww']:
    c=collections.Counter(str(v.get('score') or v.get('scores')) for k,v in res.items() if k.startswith(s))
    print(s,c.most_common(14))
