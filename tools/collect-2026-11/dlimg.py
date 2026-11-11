import json,sys,os,subprocess,hashlib,urllib.parse
S=sys.argv[1]; d=json.load(open(S+'/result.json'))['whiskies']; os.makedirs(S+'/img',exist_ok=True)
jobs=[]
for w in d:
    for n,(k,u) in enumerate(w['imgs']):
        if u.startswith('/_next/image'):
            u=urllib.parse.parse_qs(urllib.parse.urlparse(u).query)['url'][0]
        ext=os.path.splitext(urllib.parse.urlparse(u).path)[1].lower() or '.jpg'
        fn=f"{S}/img/{w['id']}__{k}_{n}{ext}"
        if not os.path.exists(fn): jobs.append((u,fn))
print(len(jobs))
import concurrent.futures as cf
def go(j):
    u,fn=j
    subprocess.run(['curl','-sL','-m','40','-A','Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36','-o',fn,u])
with cf.ThreadPoolExecutor(12) as ex: list(ex.map(go,jobs))
