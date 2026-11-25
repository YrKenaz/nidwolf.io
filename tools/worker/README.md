# 자동 갱신 일꾼 (tools/worker)

NAS가 주 1회 바깥 자료를 받아 원자료만 남기고, PC에서 그 원자료를 저장소 자료에 합친다.
NAS는 git·빌드를 하지 않고 저장소 키도 갖지 않는다. 커밋·배포는 사람이 확인한 뒤에 한다.

| 파일 | 어디서 | 하는 일 |
|---|---|---|
| `make_input.py` | PC | 저장소 자료에서 수집기 입력 `in/bottles_min.json`을 만든다 |
| `collect.py` | NAS | 입력대로 받아 `out/<날짜>/`에 원자료를 적는다. Python 3.8, 표준 라이브러리만 |
| `merge.py` | PC | 원자료 폴더를 `data/`에 합친다. `--dry-run`으로 미리 본다 |
| `backfill.py` | PC | git 이력으로 가격 이력·변경 기록의 초판을 만든다(한 번만) |
| `wlib.py` | PC | 문턱값과 두 파일의 형식(merge·backfill 공용) |

## 실행 순서

```
# 1) PC: 입력 만들기 (병을 더하거나 별칭·브랜드 표를 고친 뒤에는 다시 만든다)
python3 -B tools/worker/make_input.py
scp tools/worker/collect.py nas:nidwolf-worker/
scp tools/worker/in/bottles_min.json nas:nidwolf-worker/in/

# 2) NAS: 수집 (예약 작업). 파이썬은 /var/packages/py3k/target/usr/local/bin/python3
python3 collect.py                      # 위키만(기본)
python3 collect.py --stages ds,wiki     # 데일리샷 포함. 사용자 승인 뒤에만
python3 collect.py --resume             # 끝나지 않은 가장 최근 실행을 이어서
python3 collect.py --plan               # 요청 없이 계획만 출력
python3 collect.py --limit 3            # 단계마다 3건만(설치 시험용)

# 3) PC: 결과 가져와 합치기
scp -r nas:nidwolf-worker/out/2026-11-25 tools/worker/out/
python3 -B tools/worker/merge.py tools/worker/out/2026-11-25 --dry-run   # 바뀔 내용 확인
python3 -B tools/worker/merge.py tools/worker/out/2026-11-25             # 반영
python3 -B tools/build.py --check
```

소요 시간(587병, 위키 문서 169개 기준): 위키 약 17분(6초 간격), 데일리샷 약 26분(2초 간격).
시범 실행(PC, 위키 문서 7개)의 최대 메모리는 약 23MB였다.

## 수집기가 지키는 것

- 요청 간격: 데일리샷 2초, 위키미디어 6초. 한 번에 한 요청.
- 401·403·429 또는 예상과 다른 응답이면 그 자리에서 멈춘다(종료 코드 2). 다시 시도하지 않고, 뒤 단계도 돌리지 않는다.
- 그 밖의 오류는 그 항목만 `failed.jsonl`에 적고 넘어간다. 연달아 5번이면 멈춘다(종료 코드 3).
- 받은 것은 항목마다 한 줄로 바로 적는다. 중간에 끊겨도 `--resume`이나 같은 `--date`로 이어서 받는다(이미 받은 항목은 건너뜀).
- User-Agent는 `trend_collect.py`와 같은 값이다. 위키미디어용에만 사이트 주소가 들어가고, 개인 정보는 없다.
- `ds` 단계는 기본으로 꺼져 있다. 데일리샷 약관 확인이 끝나기 전에는 NAS에서 켜지 않는다.

## 파일 형식

### 입력 `in/bottles_min.json` (format 1)
```
{"format": 1, "made": "2026-11-25",
 "bottles": [{"id", "pid": ds_url의 상품 번호|null, "queries": [검색어 최대 3개],
              "accept": [같은 상품으로 인정할 이름], "sig": "…", "prefixes": […], "exclude_pids": […]}],
 "wiki": [{"title": 브랜드 표의 문서 제목, "resolved": 확인된 본 문서 제목|null}]}
```
`accept`·`sig`·`prefixes`·`exclude_pids`는 "검색어를 더 보낼지" 정하는 데만 쓴다. 어느 상품을 합칠지는 PC의 병합 때 다시 정한다.

### 출력 `out/<날짜>/`
- `wiki.jsonl`: `{"title","resolved","missing","views","window":[시작,끝],"at"}` (조회 기록이 없으면 `"no_data": true`)
- `ds.jsonl`: `{"id","queries","rows":[{"pid","name","en","sub","reviews","rating","sales","price","vol","service"}],"truncated","at"}`
- `failed.jsonl`: `{"stage","key","error","at"}`
- `run.log`, `summary.json`(`status`: done | partial | blocked | stopped | running, 단계별 `total`·`already`·`ok`·`failed`)

### `data/price_history.json`
```
{"<id>": [["2026-11-11", 74800], ["2026-11-25", 72000]], …}
```
- 병마다 [측정일, 가격(원)]의 목록, 날짜 오름차순. 값이 같아도 측정일마다 한 점. 병당 최근 104점까지.
- 가격이 있는 병만 들어 있다. 가격은 `bottles.json`의 `price_product` 상품 기준이다.
- "확인 필요"로 빠진 측정은 점으로 넣지 않는다.

### `data/changes.json`
```
[{"date": "2026-11-25", "type": "price", "id": "…", "from": 74800, "to": 72000}, …]
```
- 최근 날짜가 위. 같은 날짜 안에서는 new → tier → price → trend → removed, 그다음 id 순. 최근 12주(84일)만 보관.
- `type`별 `from`/`to`: `tier`는 티어 글자(S·A·B·C·D·E, 미평가는 N), `price`는 원, `trend`는 트렌드지수(0~100 정수), `new`와 `removed`는 둘 다 `null`.
- `removed`에만 `ko`(병 이름)가 붙는다. 빠진 병은 `bottles.json`에 없기 때문이다.
- 적는 문턱값(`wlib.py` 상수): 가격 ±5% 이상 또는 ±3,000원 이상, 트렌드지수 ±5점 이상. 티어·새 병·빠진 병은 모두 적는다.

## 병합 규칙

- 변경 기록은 **직전 병합 때의 상태**(`state/last.json`)와 지금을 비교해 만든다. 그 사이에 손으로 더한 병·평가도 다음 병합 때 new·tier로 잡힌다. 티어는 `build.py`의 `compute()` 결과를 쓴다.
- 트렌드지수는 전 병을 다시 계산한다. 상한은 그대로 둔다(`--rescale ds,wiki,src`로 지정한 재료만 다시 잡음).
- 끝까지 돌지 못한 단계의 자료는 쓰지 않는다(`--allow-partial`로 풀 수 있음).
- 가격을 자동으로 반영하지 않고 "확인 필요"로 빼는 경우
  - 직전보다 40% 넘게 바뀜
  - 가격 상품이 검색 결과에서 사라짐, 또는 같은 병으로 보던 상품이 하나도 없음(이때는 리뷰 수도 기존 값 유지)
  - 가격이 비어 있음, 상품명·용량이 달라짐, 기존 가격이 없던 병
- `ds_reviews`는 같은 병으로 합친 상품의 리뷰 합(트렌드지수와 같은 값), `ds_rating`은 가격 상품의 평점. 합이 5건 미만이면 둘 다 `null`.
- 목록 전체는 원자료 폴더의 `merge_preview.json`(미리 보기) 또는 `merge_result.json`(반영)에 남는다.

## 되돌리는 법

- 반영할 때마다 바꾸기 전 파일을 `tools/worker/backup/<시각>/`에 복사해 둔다. 파일 이름은 경로의 `/`를 `__`로 바꾼 것이다(예: `data__bottles.json`). 되돌리려면 그 파일들을 원래 자리로 복사한다.
- `state/last.json`도 함께 되돌려야 다음 병합의 비교 기준이 맞는다.
- 커밋 전이라면 `git diff data/`로 바뀐 내용을 볼 수 있다. `git checkout`/`restore`로 되돌리는 것은 다른 사람의 작업을 지울 수 있으니 쓰지 않는다.

## 알아 둘 것

- 위키미디어 조회수는 같은 기간을 다시 받아도 1~3% 줄어 있을 수 있다(2026-11-25 시범: 7개 문서 모두 소폭 감소). 트렌드지수에는 대개 영향이 없다(20병 중 1병이 1점).
- 수집기와 `trend_collect.py`는 상품명 정규화 규칙을 따로 갖고 있다. `make_input.py`가 실행할 때마다 두 규칙의 결과를 대조하고, 다르면 멈춘다. 규칙을 고칠 때는 두 곳을 같이 고친다.
- `out/`, `backup/`, 시범 입력은 `tools/worker/.gitignore`로 저장소에서 뺐다. `in/bottles_min.json`과 `state/last.json`은 저장소에 둔다.
- 티어·트렌드지수 변동의 과거분은 소급하지 않았다. `backfill.py`가 채운 것은 새 병·빠진 병·가격이다.
