import sys,json,collections
D=sys.argv[1]+'/dl/'
res=json.load(open(D+'final2.json'))
TY={'SM':'싱글몰트 스카치','BL':'블렌디드 스카치','BB':'버번','RY':'라이·아메리칸','IR':'아이리시','JP':'재패니즈','WD':'월드'}
ORD=['JP','IR','WD','RY','BB','BL','SM']
ind=lambda r:[s for s in ('wf','wn','df') if s in r['obs']]
for r in res:
    r['tier']='A' if len(ind(r))>=2 else ('B' if len(ind(r))==1 else 'C')
# inbox json
inbox={'created':'2026-11-11','status':'후보 (데이터 파일 미반영)','sources':{'whiskyfun':'https://www.whiskyfun.com/','whiskynotes':'https://www.whiskynotes.be/','dramface':'https://www.dramface.com/','breakingbourbon':'https://www.breakingbourbon.com/ (보류: 약관 해석 결정 필요, 원문 스냅샷 없음)'},'candidates':[]}
SN={'wf':'whiskyfun','wn':'whiskynotes','df':'dramface','bb':'breakingbourbon'}
for r in res:
    c={'id':r['id'],'ko':r['ko'],'en':r['en'],'type':r['type'],'tier':r['tier'],'master_match':r['match'],'note':r['note'],'observations':[]}
    for s,o in r['obs'].items():
        c['observations'].append({'source':SN[s],'raw':o['raw'],'name_in_source':o['name'],'url':o['url'],'date':o.get('date'),'reviewer':o.get('author'),'snapshot':o.get('snapshot'),'line_name':o.get('line_name'),'line_score':o.get('line_score'),'pending':s=='bb'})
    inbox['candidates'].append(c)
json.dump(inbox,open('/mnt/h/Dev/Tier/Whiskey/data/inbox/candidates-20261111.json','w'),indent=1,ensure_ascii=False)
def cell(r,s):
    o=r['obs'].get(s)
    if not o: return '—'
    y=str(o.get('date') or '')[:4]
    if s=='bb': return f"{o['raw'].split(' ')[0]}/5 ({y})"
    a=' Angus' if s=='wf' and o.get('author','').startswith('Angus') else ''
    return f"`{o['raw']}` ({y}{a}) L{o['line_name']}·{o['line_score']}"
out=[]
def table(rows,cols):
    out.append('| 제안 id | 한글 이름 | 영문 이름 | '+' | '.join(c[0] for c in cols)+' | 대조 | 비고 |')
    out.append('|---|---|---|'+'---|'*len(cols)+'---|---|')
    for r in rows:
        out.append(f"| `{r['id']}` | {r['ko']} | {r['en']} | "+' | '.join(cell(r,c[1]) for c in cols)+f" | {r['match']} | {r['note']} |")
    out.append('')
for tier,title,cols in [('A','2.1 A군 — 독립 출처 2곳 이상에서 점수 확인',[('Whiskyfun','wf'),('WhiskyNotes','wn'),('Dramface','df'),('BB(보류)','bb')]),('B','2.2 B군 — 독립 출처 1곳에서 점수 확인',[('Whiskyfun','wf'),('WhiskyNotes','wn'),('Dramface','df'),('BB(보류)','bb')]),('C','2.3 C군 — Breaking Bourbon에서만 확인 (출처 사용 결정 전까지 보류)',[('BB(보류)','bb')])]:
    rows=[r for r in res if r['tier']==tier]
    out.append(f'### {title} ({len(rows)}병)\n')
    for ty in ORD:
        rr=[r for r in rows if r['type']==ty]
        if not rr: continue
        out.append(f'**{TY[ty]} ({len(rr)}병)**\n'); table(rr,cols)
open(D+'tables.md','w').write('\n'.join(out))
cnt=collections.Counter((r['tier'],r['type']) for r in res)
print({t:sum(v for (a,b),v in cnt.items() if a==t) for t in 'ABC'})
for t in 'ABC': print(t,{ty:cnt[(t,ty)] for ty in ORD})
print(sum(1 for r in res if r['match']=='애매함'),'애매함')
print(collections.Counter(s for r in res for s in r['obs']))
