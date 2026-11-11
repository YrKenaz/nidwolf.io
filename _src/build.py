"""index.html 생성기.  사용법: python3 _src/build.py   (저장소 루트에서 실행)
_src/data/whiskies.json(점수·속성)과 _src/data/images.json(병 이미지)을 _src/template.html에 넣어 index.html을 만든다."""
import json,os
H=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(H)
R=json.load(open(H+'/data/whiskies.json',encoding='utf-8')); I=json.load(open(H+'/data/images.json'))
KEYS=('id','ko','en','type','region','score','tier','n','scores','raw','age','abv','style','cask','spec','beg','price','pname')
ws=[{k:w[k] for k in KEYS} for w in R['whiskies']]
data=json.dumps({'whiskies':ws,'meta':R['meta']},ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
t=open(H+'/template.html',encoding='utf-8').read().replace('__DATA__',data).replace('__IMAGES__',json.dumps(I,separators=(',',':')))
DESC='한국·영어권 위스키 티어표와 순위·평점 리스트 13개를 100점 척도로 합산한 위스키 티어표. 종류·숙성년수·피트·셰리·CS·가격대별로 골라 볼 수 있습니다.'
HEAD=('<!doctype html>\n<html lang="ko"><head><meta charset="utf-8">'
 '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
 f'<meta name="description" content="{DESC}">'
 '<link rel="canonical" href="https://nidwolf.com/"><link rel="icon" href="/Nidwolf-ico.ico">'
 f'<meta property="og:title" content="위스키 종합 티어표"><meta property="og:description" content="{DESC}">'
 '<meta property="og:type" content="website"><meta property="og:url" content="https://nidwolf.com/">'
 '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n')
t=t.replace('<meta name="claude:viewport-fit-sides" content="cover">\n','')
full=HEAD+t.replace('<div class="wrap">','</head><body>\n<div class="wrap">',1)+'\n</body></html>\n'
open(ROOT+'/index.html','w',encoding='utf-8').write(full)
print('index.html',len(full)//1024,'KB,',len(ws),'병')
