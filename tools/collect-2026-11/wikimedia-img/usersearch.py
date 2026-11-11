#!/usr/bin/env python3
"""병 사진을 많이 올린 저작자의 업로드 목록을 훑는다(브랜드 범주 탐색 대신). 결과는 userfiles.json."""
import json,subprocess,time,urllib.parse,re,html,os,sys
H=os.path.dirname(os.path.abspath(__file__))
UA='nidwolf-photo-collect/0.1 (https://nidwolf.com; bottle photos with licence and attribution)'
def strip(x): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x or ''))).strip()
out=json.load(open(H+'/userfiles.json')) if os.path.exists(H+'/userfiles.json') else {}
for user in sys.argv[1:]:
    if user in out: continue
    rows=[]; cont={}
    while True:
        p={'action':'query','format':'json','generator':'allimages','gaiuser':user,'gaisort':'timestamp','gaidir':'older','gailimit':'50','prop':'imageinfo','iiprop':'url|extmetadata|mime|size|timestamp|user','iiurlwidth':'340','maxlag':'5'}; p.update(cont)
        r=subprocess.run(['curl','-sS','-m','60','-A',UA,'https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(p)],capture_output=True).stdout.decode('utf-8','replace')
        j=json.loads(r)
        for pg in j.get('query',{}).get('pages',{}).values():
            if 'imageinfo' not in pg: continue
            ii=pg['imageinfo'][0]; em=ii.get('extmetadata',{}); g=lambda k: strip(em.get(k,{}).get('value',''))
            rows.append({'title':pg['title'],'page':ii.get('descriptionurl'),'thumb':ii.get('thumburl'),'url':ii.get('url'),'mime':ii.get('mime'),'w':ii.get('width'),'h':ii.get('height'),'uploaded':ii.get('timestamp'),'uploader':ii.get('user'),'license':g('LicenseShortName'),'license_url':g('LicenseUrl'),'artist':g('Artist')[:150],'credit':g('Credit')[:150],'restrictions':g('Restrictions'),'desc':g('ImageDescription')[:250],'taken':g('DateTimeOriginal')[:40],'cats':g('Categories')[:300]})
        time.sleep(2)
        if 'continue' in j and len(rows)<3000: cont=j['continue']
        else: break
    out[user]=rows; json.dump(out,open(H+'/userfiles.json','w'),ensure_ascii=False); print(user,len(rows))
