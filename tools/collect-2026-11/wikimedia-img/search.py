#!/usr/bin/env python3
"""위키미디어 공용에서 병별 사진 후보 검색. 직렬, 2초 간격. 결과는 search.json에 누적."""
import json,subprocess,time,urllib.parse,re,html,os,sys
H=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(os.path.dirname(os.path.dirname(H)))
UA='nidwolf-photo-collect/0.1 (https://nidwolf.com; bottle photos with licence and attribution)'
B=json.load(open(ROOT+'/data/bottles.json')); T=json.load(open(ROOT+'/data/trends.json'))
tb=T.get('bottles',{})
def tscore(i):
    v=tb.get(i)
    if isinstance(v,dict): return v.get('index') or v.get('score') or 0
    return v or 0
B.sort(key=lambda b:-(tscore(b['id']) or 0))
out=json.load(open(H+'/search.json')) if os.path.exists(H+'/search.json') else {}
def strip(x): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x or ''))).strip()
def query(q):
    p={'action':'query','format':'json','generator':'search','gsrnamespace':'6','gsrsearch':q,'gsrlimit':'20','prop':'imageinfo','iiprop':'url|extmetadata|mime|size|timestamp|user','iiurlwidth':'340','maxlag':'5'}
    r=subprocess.run(['curl','-sS','-m','40','-A',UA,'-w','\n%{http_code}','https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(p)],capture_output=True).stdout.decode('utf-8','replace')
    body,code=r.rsplit('\n',1)
    if code!='200': return None
    j=json.loads(body)
    if 'error' in j: return None
    rows=[]
    for pg in sorted(j.get('query',{}).get('pages',{}).values(),key=lambda x:x.get('index',99)):
        ii=pg['imageinfo'][0]; em=ii.get('extmetadata',{}); g=lambda k: strip(em.get(k,{}).get('value',''))
        rows.append({'title':pg['title'],'page':ii.get('descriptionurl'),'thumb':ii.get('thumburl'),'url':ii.get('url'),'mime':ii.get('mime'),'w':ii.get('width'),'h':ii.get('height'),'uploaded':ii.get('timestamp'),'uploader':ii.get('user'),'license':g('LicenseShortName'),'license_url':g('LicenseUrl'),'artist':g('Artist')[:150],'credit':g('Credit')[:150],'restrictions':g('Restrictions'),'desc':g('ImageDescription')[:250],'taken':g('DateTimeOriginal')[:40],'cats':g('Categories')[:300]})
    return rows
fail=0
for b in B:
    if b['id'] in out: continue
    rows=query(b['en'])
    if rows is None:
        fail+=1; time.sleep(10)
        if fail>=3: print('STOP'); break
        continue
    fail=0; out[b['id']]={'q':b['en'],'rows':rows}
    json.dump(out,open(H+'/search.json','w'),ensure_ascii=False); time.sleep(2)
print('DONE',len(out))
