import json,re,sys,subprocess,time,os
D=sys.argv[1]+'/dl/'; h=sys.argv[2]
def fn(host,u): return D+'pg/'+host+'__'+re.sub(r'[^A-Za-z0-9._-]','_',u.split('//',1)[1])[:180]
log=open(D+'efetch_'+h+'.log','a'); err=0
for u in json.load(open(D+'e_jobs.json'))[h]:
    f=D+'wf/'+u.split('/')[-1] if h=='wf' else fn(h,u)
    if os.path.exists(f) and os.path.getsize(f)>3000: continue
    r=subprocess.run(['curl','-sSL','-m','90','-A','Mozilla/5.0 (compatible; research-fetch)','-o',f,'-w','%{http_code}',u],capture_output=True,text=True)
    log.write(r.stdout+' '+u+'\n'); log.flush()
    if r.stdout.strip()!='200':
        err+=1
        if err>=3: log.write('STOP\n'); break
    else: err=0
    time.sleep(3)
log.write('DONE\n')
