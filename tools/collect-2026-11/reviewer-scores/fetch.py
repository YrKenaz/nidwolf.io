import json,sys,subprocess,time,os,re,hashlib
D=sys.argv[1]+'/dl/'; host=sys.argv[2]
m=json.load(open(D+'matches.json'))
key={'wn':'whiskynotes','df':'dramface','ww':'thewhiskeywash','bb':'breakingbourbon'}[host]
us=sorted({u for v in m.values() for u in v[host]})
os.makedirs(D+'pg',exist_ok=True)
log=open(D+'fetch_'+host+'.log','a')
for u in us:
    f=D+'pg/'+host+'__'+re.sub(r'[^A-Za-z0-9._-]','_',u.split('//',1)[1])[:180]
    if os.path.exists(f) and os.path.getsize(f)>2000: continue
    r=subprocess.run(['curl','-sSL','-m','60','-A','Mozilla/5.0 (compatible; research-fetch)','-o',f,'-w','%{http_code}',u],capture_output=True,text=True)
    log.write(r.stdout+' '+u+'\n'); log.flush()
    if r.stdout.strip() in('403','429'): log.write('STOP blocked\n'); break
    time.sleep(2.5)
log.write('DONE\n')
