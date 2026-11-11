#!/usr/bin/env python3
"""미등록 병 가운데 데일리샷 리뷰(용량·구형 합산) 100건 이상인 병을 bottles.json 형식으로 준비한다.

bottles.json은 고치지 않는다. 결과는 tools/trend-data/에 둔다.
  new_bottles.json        bottles.json에 그대로 붙일 수 있는 줄(한 줄에 한 병)
  new_bottles_notes.json  병마다 근거: 합친 상품, 이미지 주소, region을 어디서 가져왔는지
  new_bottles_held.json   넣지 않고 보류한 병과 이유
먼저 `trend_collect.py ds score`로 unregistered.json이 만들어져 있어야 한다.

PLAN은 사람이 정한다: id, 한글·영문 이름, 종류, 같은 브랜드의 등록 병(region을 거기서 가져온다).
age·style·spec은 상품명에 적힌 것만 채운다(12년 → age, CS → cs, 셰리 → sherry, 싱글배럴 → SiB).
abv·cask는 상품명에 없으므로 비운다. 이미지는 내려받지 않고 주소만 notes에 남긴다.
"""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trend_collect as t

MIN_REVIEWS = 100
# 데일리샷 묶음 이름(unregistered.json의 name): (id, ko, en, type, region을 가져올 등록 병 id 또는 None)
PLAN = {
 "탐나불린 셰리 캐스크": ("tamnavulin-sherry", "탐나불린 셰리 캐스크", "Tamnavulin Sherry Cask", "SM", None),
 "더 글렌리": ("glenlee", "더 글렌리", "The Glenlee", "BL", None),
 "발렌타인 싱글몰트 글렌버기 12년": ("ballantines-glenburgie-12", "발렌타인 싱글몰트 글렌버기 12년", "Ballantine's Single Malt Glenburgie 12", "SM", None),
 "산토리 올드 위스키": ("suntory-old", "산토리 올드", "Suntory Old", "JP", "kakubin"),
 "조니워커 블랙 셰리 에디션": ("jw-black-sherry", "조니워커 블랙 셰리 에디션", "Johnnie Walker Black Label Sherry Edition", "BL", "jw-black"),
 "아드벡 위 비스티 5년": ("ardbeg-wee-beastie", "아드벡 위 비스티 5년", "Ardbeg Wee Beastie 5", "SM", "ardbeg-10"),
 "일리악 CS": ("ileach-cs", "일리악 CS", "The Ileach Cask Strength", "SM", "ileach"),
 "조니워커 블랙 루비": ("jw-black-ruby", "조니워커 블랙 루비", "Johnnie Walker Black Ruby", "BL", "jw-black"),
 "글렌피딕 12년 트리플 오크": ("glenfiddich-12to", "글렌피딕 12년 트리플 오크", "Glenfiddich 12 Triple Oak", "SM", "glenfiddich-12"),
 "더 글렌그란트 아보랄리스 CS": ("glengrant-arb-cs", "글렌그란트 아보랄리스 CS", "Glen Grant Arboralis Cask Strength", "SM", "glengrant-arb"),
 "카발란 디스틸러리 셀렉트 No.1": ("kavalan-ds1", "카발란 디스틸러리 셀렉트 No.1", "Kavalan Distillery Select No.1", "WD", "kavalan-classic"),
 "에드라두어 12년 CS": ("edradour-12cs", "에드라두어 12년 CS", "Edradour 12 Cask Strength", "SM", "edradour-10"),
 "잭 다니엘스 싱글배럴 배럴 스트렝스": ("jd-sib-bs", "잭 다니엘 싱글배럴 배럴 스트렝스", "Jack Daniel's Single Barrel Barrel Strength", "RY", "jd-sib"),
 "더 글렌드로낙 오드 투 더 다크": ("glendronach-ode-dark", "글렌드로낙 오드 투 더 다크", "GlenDronach Ode to the Dark", "SM", "glendronach-12"),
 "아란 쿼터 캐스크": ("arran-quarter", "아란 쿼터 캐스크", "Arran Quarter Cask", "SM", "arran-10"),
 "라프로익 10년 셰리 오크 피니시": ("laphroaig-10sherry", "라프로익 10년 셰리 오크 피니시", "Laphroaig 10 Sherry Oak Finish", "SM", "laphroaig-10"),
 "러셀 리저브 싱글배럴 라이": ("russells-sib-rye", "러셀 리저브 싱글배럴 라이", "Russell's Reserve Single Barrel Rye", "RY", "russells-sib"),
 "더 글렌그란트 12년 셰리 캐스크": ("glengrant-12sherry", "글렌그란트 12년 셰리 캐스크", "Glen Grant 12 Sherry Cask", "SM", "glengrant-12"),
 "산토리 로얄 위스키": ("suntory-royal", "산토리 로얄", "Suntory Royal", "JP", "kakubin"),
 "더 페이머스 그라우스 셰리 캐스크 피니시": ("grouse-sherry", "페이머스 그라우스 셰리 캐스크 피니시", "The Famous Grouse Sherry Cask Finish", "BL", "famous-grouse"),
 "스모키 스캇": ("smoky-scot", "스모키 스캇", "Smoky Scot", "SM", None),
 "잭 다니엘스 싱글배럴 100 프루프": ("jd-sib-100", "잭 다니엘 싱글배럴 100 프루프", "Jack Daniel's Single Barrel 100 Proof", "RY", "jd-sib"),
 "몰트락 16년": ("mortlach-16", "모틀락 16년", "Mortlach 16", "SM", "mortlach-12"),
}
# 100건 이상이지만 넣지 않는 것
HELD = {
 "메이커스 마크 바틀 점퍼 에디션": "메이커스 마크의 포장 한정판으로 보임. 내용물이 같은 병인지 확인되지 않음",
 "잭 다니엘스 잔": "잔 세트 상품(잭 다니엘스 잔 세트). 병이 아님",
 "빅 피트 CS 데일리샷 추석 에디션 #1": "판매처 한정 배치. 일반 판매 병으로 볼지 애매함",
 "조니워커 블랙 오징어 게임 코스튬 에디션": "조니워커 블랙의 포장 한정판으로 보임",
 "디 오리지널 골드바 위스키": "선물 세트 상품만 있음. 단품 병 확인 안 됨",
 "더 글렌리벳 12년 200주년 에디션": "글렌리벳 12년의 기념 포장판인지 별도 원액인지 확인되지 않음",
}


def main():
    un = t.load(os.path.join(t.WORK, "unregistered.json"))
    bottles = {b["id"]: b for b in t.load(os.path.join(t.ROOT, "data", "bottles.json"))}
    over = [g for g in un if g["reviews"] >= MIN_REVIEWS]
    missing = [g["name"] for g in over if g["name"] not in PLAN and g["name"] not in HELD]
    if missing:
        print("PLAN에도 HELD에도 없는 100건 이상 병(사람이 분류해야 함):", missing)
    out, notes, held = [], {}, []
    for g in over:
        if g["name"] in HELD:
            held.append({"name": g["name"], "en": g["en"], "reviews": g["reviews"], "why": HELD[g["name"]], "products": g["products"]})
            continue
        if g["name"] not in PLAN:
            held.append({"name": g["name"], "en": g["en"], "reviews": g["reviews"], "why": "미분류", "products": g["products"]})
            continue
        bid, ko, en, typ, sib = PLAN[g["name"]]
        if bid in bottles:
            print("이미 등록된 id:", bid); continue
        page = t.ds_search(g["name"])
        key = t.norm(g["name"])
        cands = []
        for r in (page or {}).get("results", []):
            name = r["top_product_name"]
            if r.get("category") != "위스키" or t.RE_BUNDLE.search(name) or t.norm(name) != key:
                continue
            plain = not t.RE_PACK.search(t.RE_PAREN.sub(" ", name))
            vol = re.search(r"(\d+(?:\.\d+)?)\s*(ml|L)", name)
            is700 = (vol is None) or (vol.group(1) == "700" and vol.group(2) == "ml")
            cands.append((plain and is700, plain, r.get("review_count") or 0, r))
        cands.sort(key=lambda c: (c[0], c[1], c[2]), reverse=True)
        if not cands:
            held.append({"name": g["name"], "en": g["en"], "reviews": g["reviews"], "why": "다시 검색했을 때 상품을 찾지 못함", "products": g["products"]})
            continue
        ok700, _, _, r = cands[0]
        if "배치" in r["top_product_name"]:
            ok700 = False      # 배치별 상품은 가격이 배치마다 달라 대표 가격으로 쓰지 않는다
        age = re.search(r"(\d+)년", ko)
        style = [s for s, pat in (("sherry", "셰리"), ("cs", r"CS|캐스크 스트렝스|배럴 스트렝스")) if re.search(pat, ko)]
        spec = ["SiB"] if "싱글배럴" in ko else []
        row = {"id": bid, "ko": ko, "en": en, "type": typ,
               "region": bottles[sib]["region"] if sib else None,
               "age": int(age.group(1)) if age else None, "abv": None,
               "style": style, "cask": [], "spec": spec, "beginner": False,
               "price": r.get("price") if ok700 else None,
               "price_product": r["top_product_name"] if ok700 else None,
               "price_date": time.strftime("%Y-%m-%d") if ok700 else None,
               "img": None, "img_source": None,
               "ds_rating": r.get("review_rate"), "ds_reviews": g["reviews"]}
        out.append(row)
        notes[bid] = {"ds_group": g["name"], "ds_en_name": g["en"], "ds_subcategory": g["type"],
                      "merged_products": g["products"], "picked_product": r["top_product_name"],
                      "picked_is_700ml": ok700, "img_url": r.get("thumbnail_image"),
                      "region_from": sib, "ds_rating_from": r["top_product_name"],
                      "unverified": ["abv", "cask"] + ([] if sib else ["region"])}
        print(bid, "|", r["top_product_name"], r.get("price"), r.get("review_rate"), g["reviews"], flush=True)
    with open(os.path.join(t.WORK, "new_bottles.json"), "w", encoding="utf-8") as f:
        f.write("[\n" + ",\n".join(json.dumps(b, ensure_ascii=False) for b in out) + "\n]\n")
    t.save(os.path.join(t.WORK, "new_bottles_notes.json"), notes, indent=1)
    t.save(os.path.join(t.WORK, "new_bottles_held.json"), held, indent=1)
    print("준비한 병", len(out), "/ 보류", len(held))


if __name__ == "__main__":
    main()
