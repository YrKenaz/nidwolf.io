#!/usr/bin/env python3
"""세 리뷰어 출처(Whiskyfun, WhiskyNotes, Dramface)의 환산 계수 시험 계산.
사용: python3 calibrate.py <기존 병 관측값 e_obs.json> [data 폴더]
기준값 = 그 출처를 넣기 전 기존 관측값(in_score 출처)의 매체 그룹별 평균을 다시 평균한 값.
환산 = 기준 평균 + (x - 출처 평균) * 기준 표준편차 / 출처 표준편차 (공통 병 기준, 모표준편차)."""
import json,sys,collections,math
obs_new=json.load(open(sys.argv[1])); DATA=sys.argv[2] if len(sys.argv)>2 else '../../../data'
src=json.load(open(DATA+'/sources.json')); obs=json.load(open(DATA+'/observations.json'))
g=collections.defaultdict(lambda: collections.defaultdict(list))
for o in obs:
    s=src[o['source']]
    if s['in_score'] and o['value'] is not None and o['source'] not in ('whiskyfun','whiskynotes','dramface'): g[o['bottle']][s['group']].append(o['value'])
ref={b:sum(sum(v)/len(v) for v in gs.values())/len(gs) for b,gs in g.items()}
def stats(key):
    pairs=[(v[key]['x'],ref[b]) for b,v in obs_new.items() if key in v and b in ref]
    n=len(pairs); xs=[p[0] for p in pairs]; ys=[p[1] for p in pairs]
    mx=sum(xs)/n; my=sum(ys)/n; sx=math.sqrt(sum((x-mx)**2 for x in xs)/n); sy=math.sqrt(sum((y-my)**2 for y in ys)/n)
    r=sum((x-mx)*(y-my) for x,y in pairs)/(n*sx*sy)
    return dict(n=n,mean_x=round(mx,3),sd_x=round(sx,3),mean_ref=round(my,3),sd_ref=round(sy,3),r=round(r,3),slope=round(sy/sx,4),intercept=round(my-mx*sy/sx,3))
if __name__=='__main__':
    out={k:stats(k) for k in ('wf','wn','df')}
    for k,v in out.items(): print(k,v, '※ 공통 병 30 미만' if v['n']<30 else '', '※ 상관 0.3 미만' if v['r']<0.3 else '')
    json.dump(out,open('calibration.json','w'),indent=1)
