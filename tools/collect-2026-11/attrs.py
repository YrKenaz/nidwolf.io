import json,sys,os,re,subprocess,time,urllib.parse
S=sys.argv[1]; R=json.load(open(S+'/result.json')); C=json.load(open(S+'/ds.json'))
# id: "abv flags"  P=피트 S=셰리 C=CS/배럴프루프 | 캐스크 b=버번 w=포트·와인 r=럼 m=미즈나라 | 버번 스펙 SiB SmB BiB BP Wh
A={l.split(':')[0].strip():l.split(':')[1].split() for l in '''
ardbeg-uigeadail:54.2 P S
lagavulin-16:43 P
aberlour-abunadh:60 S C
gts:65 C BP
ecbp:60 C BP
jw-green:43
glendronach-15:46 S
glenmorangie-nectar:46 b w
michters-10:47.2 SiB
kavalan-oloroso:46 S
redbreast-15:46 S b
wlw:64 C BP Wh
balvenie-12sb:47.8 b
hp-valknut:46.8 P S
russells-sib:55 SiB
nikka-ftb:51.4
of-birthday:48
glenmorangie-18:43 S b
russells-10:45 SmB
pappy-15:53.5 Wh
talisker-10:45.8 P b
glenallachie-15:46 S
glendronach-cs:58 S C
tamdhu-12:43 S
bowmore-18:43 P S
bushmills-16:40 S b w
bunnahabhain-12:46.3 S
talisker-storm:45.8 P
hakushu-12:43 P
of-1920:57.5
quinta-ruban:46 b w
cadboll:43 b w
glendronach-18:46 S
balvenie-14:43 b r
jw-18:40
laphroaig-10:40 P b
jw-blue:40
oldpulteney-15:46 S b
oban-14:43
caolila-12:43 P b
rare-breed:58.4 C BP
chivas-18:40
monkey-shoulder:40 b
ardbeg-10:46 P b
benriach-12:46 S b w
cb-orchard:46 b
mortlach-12:43.4 S b
makers-cellar:57 C BP Wh
fuji-grain:46 b
springbank-15:46 P S
hp-cs:63 P S C
woodford-do:43.2
bookers:62 C BP SmB
green-spot-lb:46 b w
cb-peat-monster:46 P
glendronach-12:43 S
wt-101:50.5
fr-sb:45 SmB
larceny-bp:61 C BP Wh
kavalan-vinho:57 C w
natterjack-cs:63 C
hibiki-harmony:43 S m
kc-9:50 SmB
yoichi:45 P
redbreast-12:40 S b
aberlour-12:40 S b
glenfiddich-18:40 S b
westward-sm:45
fourroses-sib:50 SiB
bowmore-15:43 P S
macallan-12sherry:40 S
glenfarclas-12:43 S
makers-46:47 Wh
ogd-bib:50 BiB
angels-envy:43.3 w
springbank-10:46 P S b
blantons:46.5 SiB
ec-sb:47 SmB
ew-bib:50 BiB
buffalo-trace:45
clynelish-14:46
glenmorangie-10:40 b
balvenie-12dw:40 S b
yamazaki-12:43 S b m
glenlivet-18:40 S b
amrut-fusion:50 P
1792-fp:62.5
longrow:46 P
rittenhouse:50 BiB
kc-rye:50 SmB
michters-rye:42.4 SiB
highwest-dr:46
glenfiddich-15:40 S b
miyagikyo:45 S
makers-cs:55 C BP Wh
port-charlotte-10:50 P b w
woodford:43.2
dalwhinnie-15:43
macallan-12dc:40 S
teeling-blackpitts:46 P b w
kavalan-exbourbon:46 b
bushmills-12:40 S b
laphroaig-qc:48 P b
ardbeg-anoa:46.6 P S b
1792-sb:46.85 SmB
eht-sb:50 SmB BiB
ardbeg-corry:57.1 P
dewars-18:40
dalmore-12:40 S b
hp-12:40 P S
kilchoman-machir:46 P S b
teeling-sb:46 r
starward-solera:43 w
laddie-classic:50 b
chivas-mizunara:40 m
bowmore-12:40 P S b
jameson-bb:40 S b
toki:43
tobermory-12:46.3 b
glenlivet-12:40 b
glenfiddich-12:40 S b
black-bush:40 S
suntory-ao:43
royalsalute-21:40
naked-malt:40 S
oldpulteney-12:40 b
chita:43
ballantines-21:40
glenrothes-wmc:48.8 S
jw-gold:40
aberfeldy-12:40 b
glenallachie-12:46 S
famous-grouse:40
makers:45 Wh
jw-doubleblack:40 P
cb-artist:43
taketsuru:43
jw-black:40
chivas-12:40
singleton-12:40 S b
dewars-12:40
ballantines-17:40
jameson:40
oldparr-12:40
black-bottle:40 P
cc-12:40
jw-red:40
kakubin:40
redbreast-27:54.6 S b w C
midleton-vr:40 b
hibiki-21:43 S m
yoichi-10:45 P
talisker-de:45.8 P S
red-spot:46 S b w
eht-bp:65 C BP
woodford-bp:60 C BP
writers-tears-rh:46 S
cragganmore-de:40 w
dalmore-14:43.8 S b
sassenach:46
jameson-18:40 S b
ogd-114:57
bunna-toiteach:46.3 P S
eht-sib:50 SiB BiB
kc-12:50 SmB
of-1910:46.5
eagle-rare-17:50.5
pc-islay-barley:50 P b w
raasay:46.4 P b w
glenmoray-18:47.2 b
craigellachie-13:46 b
jd-14:63 C BP
glenscotia-victoriana:54.2 C
mc-candid:49 S
glenmorangie-12:40 b
laphroaig-cairdeas:52 P C
glenmoray-elgin:40
ledaig-sinclair:46.3 P w
glenkinchie-de:43 S
dalmore-cigar:44 S b w
lagavulin-12cs:57 P C b
abunadh-alba:58 C b
glengoyne-15:43 S b
tamdhu-15:46 S
westward-cs:62.5 C
kilkerran-12:46 P S b
aberlour-16:40 S b
springbank-12cs:55 P S C b
benromach-15:43 P S b
jd-10:48.5
of-100:50
irishman-sm:40 S b
buchanans-18:40
wilderness-sib:50 SiB BiB
oldparr-18:40
wt-8-101:50.5
jura-18:44 b w
jura-12:40 S b
pauljohn-px:48 S
craigellachie-17:46 b
glenmorangie-infinita:43 S b
glenfiddich-12sherry:43 S
kilchoman-sanaig:46 P S
kilchoman-lochgorm:46 P S
tamdhu-bs:57 S C
mc-overaged:43 S
campbeltown-loch:46 P S b
amrut-cs:61.8 C b
glenmorangie-tokyo:46 S b m
inchmurrin-12:46 b
lochlomond-14:46 b
henry-mckenna:50 SiB BiB
stagg:65 C BP
bardstown-bib:50 BiB
green-river:45
vob-100:50
ec-bp-rye:54 C BP
lochlomond-glengarry:46 b
singleton-18g:40 S b
chichibu-505:50.5
benromach-cs:59 P S C b
cb-hedonism:43 b
glendronach-port:46 S w
ledaig-10:46.3 P b
hp-15:44 P S
glengrant-12:43 b
glengarioch-12:48 S b
glencadam-15:46 b
arran-sherry:55.8 S C
auchentoshan-18:43 b
aultmore-12:46 b
aultmore-18:46 b
irishman-12:43 b
aberfeldy-16:40 S b
bigpeat-12:46 P
glengoyne-cs:59 S C
lagavulin-8:48 P b
chivas-25:40
bennevis-10:46 S b
edradour-cal12:46 S
lochlomond-12:46 b
pauljohn-oloroso:48 S
glengrant-18:43 b
glenfiddich-ipa:43 b
glenfarclas-105:60 S C
benromach-10:43 P S b
balvenie-14peat:48.3 P b
cragganmore-12:40 b
lochlomond-18:46 b
jd-12:53.5
speyburn-15:46 S b
akashi:40
glenturret-triple:44 S b
powers-jl:46 S b
laphroaig-px:48 P S b
teeling-sm:46 S w
glengoyne-12:43 S b
tomatin-14:46 b w
dewars-21dd:46 S
glenfiddich-xx:47 S b w
ancnoc-rascan:46 P b
auchentoshan-3w:43 S b
lagavulin-offerman:46 P
scapa-skiren:40 b
glencadam-andalucia:46 S b
glenturret-12:46 S b
oban-de:43 S
dalmore-12sherry:43 S
balvenie-12ao:43 b
glenfarclas-15:46 S
benriach-16:43 S b
glengrant-15bs:50 b
glenmoray-12:40 b
oldperth-12:46 S
roseisle-12:56.5 C b
linkwood-12:43 b
dalmore-15:40 S b
lochlomond-original:40 b
mars-iwai:40
of-86:43
glenallachie-cs:58 S C
lochlea:46 S b
smokehead:43 P
arran-barrel:43 b
tomatin-12:43 S b
auchentoshan-12:40 S b
machrie-moor:46 P b
singleton-d18:40 S b
glenglassaugh-12:45 S b w
ancnoc-12:40 S b
blairathol-12:43 S
royalbrackla-12:46 S
tomatin-15:46 b
rock-island:46.8 P
strathmill-12:43 b
glenmorangie-x:40 b
ew-sib:43.3 SiB
kingsbarns-doocot:46 b w
laphroaig-select:40 P S b
jura-sevenwood:42 b w
glengoyne-10:40 S b
dewars-15:40
tomatin-cs:57.5 S C b
tomintoul-cigar:43 P S
balblair-12:46 S b
lochnagar-12:40 S b
edradour-10:40 S b
cardhu-12:40 b
tomintoul-16:40 b
dailuaine-16:43 S
cb-glasgow:43 P S
chivas-13:40 b
old-tub:50 BiB
speyburn-arranta:46 b
cuttysark-pro:50
glenelgin-12:43 S b
jw-highrye:45
buchanans-12:40
ballantines-12:40
glenkinchie-12:43 b
speyburn-10:40 S b
timorous:46.8
deanston-12:46.3 b
copper-dog:40
clansman:40
fettercairn-12:40 b
tomatin-legacy:43 b
gauldrons:46.2
epicurean:46.2
cuttysark:40
mannochmore-12:43 b
tomintoul-14:46 b
glenrothes-12:40 S
tomintoul-10:40 b
ileach:40 P
johnbarr:40
weller-sr:45 Wh
grants:40
black-white:40
glengrant-arb:40 S b
windsor-12:40
nikka-black:37
'''.strip().split('\n')}
AGE={'jw-green':15,'jw-black':12,'lagavulin-offerman':11}
BEG={'wt-101','ec-sb','ew-bib','kc-9','makers-46','woodford','1792-sb','buffalo-trace','makers','monkey-shoulder','glenmorangie-10','ardbeg-10','hp-12','talisker-10','glenfiddich-12','cb-artist','bunnahabhain-12','aberfeldy-12','laphroaig-10'}
REJ=set(json.load(open(S+'/tools/rej.json')))
pc=S+'/price.json'; P=json.load(open(pc)) if os.path.exists(pc) else {}
for w in R['whiskies']:
    i=w['id']; m=C.get(i,{}).get('match')
    if i in P or i in REJ or not m: continue
    u='https://dailyshot.co/m/search/result?q='+urllib.parse.quote(C[i]['q'])
    t=subprocess.run(['curl','-sL','-m','30','-A','Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36',u],capture_output=True).stdout.decode('utf-8','replace')
    mm=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',t,re.S); pr=None; nm=None
    if mm:
        try:
            j=json.loads(mm.group(1))
            for qq in j['props']['pageProps']['dehydratedState']['queries']:
                dd=qq['state'].get('data')
                if isinstance(dd,dict) and 'pages' in dd:
                    for p in dd['pages']:
                        for x in p.get('results',[]):
                            if x.get('thumbnail_image')==m[3] and x.get('price') and not re.search(r'세트|전용잔|패키지|기획|&',x['name']):
                                if pr is None or x['price']<pr: pr=x['price']; nm=x['name']
        except Exception as e: print('ERR',i,e)
    P[i]={'price':pr,'name':nm}; json.dump(P,open(pc,'w'),ensure_ascii=False); time.sleep(0.3)
miss=[]
for w in R['whiskies']:
    i=w['id']; a=A.get(i)
    if not a: miss.append(i); a=['40']
    fl=set(a[1:])
    m=re.search(r'(\d+)년',w['ko']); w['age']=AGE.get(i,int(m.group(1)) if m else None)
    w['abv']=float(a[0]); w['style']=[k for k,c in (('peat','P'),('sherry','S'),('cs','C')) if c in fl]
    w['cask']=[k for k,c in (('bourbon','b'),('wine','w'),('rum','r'),('mizunara','m')) if c in fl]
    w['spec']=[c for c in ('SiB','SmB','BiB','BP','Wh') if c in fl]
    w['beg']=bool(i in BEG or 'dcintro' in w['scores'] or 'minnick10' in w['scores'])
    w['price']=(P.get(i) or {}).get('price'); w['pname']=(P.get(i) or {}).get('name')
json.dump(R,open(S+'/result.json','w'),ensure_ascii=False,indent=1)
print('missing attrs:',miss); print('extra attrs:',[k for k in A if k not in {w['id'] for w in R['whiskies']}])
print('priced',sum(1 for w in R['whiskies'] if w['price']),'/',len(R['whiskies']))
for w in R['whiskies']:
    if w['price']: print(w['ko'],'|',w['pname'],w['price'])
