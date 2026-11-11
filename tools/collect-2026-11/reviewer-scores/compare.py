#!/usr/bin/env python3
"""반영 전(backup-20261111)과 후(data)의 티어·확신도 비교. build.py를 읽기 전용으로 불러 compute()만 쓴다."""
import sys,os,json,collections
H=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(os.path.dirname(os.path.dirname(H)))
sys.path.insert(0,ROOT+'/tools'); sys.dont_write_bytecode=True
import build
def run(d):
    build.load=lambda name: json.load(open(os.path.join(d,name),encoding='utf-8'))
    ws,meta,bottles,errs,stats=build.compute(); assert not errs,errs[:3]
    return {w['id']:w for w in ws},stats
a,sa=run(ROOT+'/tools/collect-2026-11/backup-20261111'); b,sb=run(ROOT+'/data')
T='SABCDEN'
for name,x,s in (('전',a,sa),('후',b,sb)):
    c=collections.Counter(w['tier'] for w in x.values()); f=collections.Counter(w['flag'] for w in x.values())
    print(name,len(x),'병',' '.join(t+str(c[t]) for t in T),'| 잠정',f['prov'],'경계',f['border'],'확정',f['firm'],'미평가',f['none'],'| 경계',s['tiers'],'sd',s['sd'],'사전',s['prior'])
ch=[(i,a[i]['tier'],b[i]['tier'],a[i]['score'],b[i]['score'],a[i]['n'],b[i]['n']) for i in a if a[i]['tier']!=b[i]['tier']]
print('티어 바뀐 기존 병',len(ch),'(올라감',sum(1 for c in ch if T.index(c[2])<T.index(c[1])),'내려감',sum(1 for c in ch if T.index(c[2])>T.index(c[1])),')')
print('그중 새 관측값이 붙지 않았는데 바뀐 병',sum(1 for c in ch if c[5]==c[6]))
big=[c for c in ch if 'N' not in (c[1],c[2]) and abs(T.index(c[1])-T.index(c[2]))>=2]
print('두 칸 이상',len(big))
for c in sorted(big,key=lambda c:c[0]): print('  ',c[0],b[c[0]]['ko'],c[1],'→',c[2],c[3],'→',c[4],'출처',c[5],'→',c[6])
print('미평가→평가',[(c[0],c[2]) for c in ch if c[1]=='N'])
print('독립 출처 1→2곳 이상',sum(1 for i in a if a[i]['n']==1 and b[i]['n']>=2),'| 0→1 이상',sum(1 for i in a if a[i]['n']==0 and b[i]['n']>=1),'| 2곳 이상인 병 전',sum(1 for w in a.values() if w['n']>=2),'후',sum(1 for w in b.values() if w['n']>=2))
new=[w for i,w in b.items() if i not in a]
print('새 병',len(new),collections.Counter(w['tier'] for w in new),collections.Counter(w['flag'] for w in new))
