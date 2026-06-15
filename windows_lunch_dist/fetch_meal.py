# -*- coding: utf-8 -*-
"""NEIS 급식식단정보 API에서 인천과학고 급식을 가져온다 (API 키 없이 소량 호출).

반환 형식: {"조식": [메뉴, ...], "중식": [...], "석식": [...], "_cached": bool}
실패 시 주간 조회 → 캐시 순으로 fallback 한다.
"""
import datetime
import re

import requests

import config

NEIS = "https://open.neis.go.kr/hub"
SCHOOL_NAME = "인천과학고등학교"
TIMEOUT = 10

_ALLERGY = re.compile(r"\s*\([0-9. ]+\)\s*")   # "(5.6.13)" 알레르기 표기
_TAG = re.compile(r"<[^>]+>")


def _clean_dish(raw: str) -> list:
    """'찹쌀밥 <br/>소불고기 (5.6)' → ['찹쌀밥', '소불고기']"""
    items = []
    for part in _TAG.sub("\n", raw).split("\n"):
        name = _ALLERGY.sub("", part).strip().strip(".").strip()
        if name:
            items.append(name)
    return items


def get_school_code(cfg: dict) -> tuple:
    """(시도교육청코드, 행정표준코드). 최초 1회 조회 후 config에 캐시."""
    neis = cfg.get("neis") or {}
    if neis.get("atpt") and neis.get("code"):
        return neis["atpt"], neis["code"]
    r = requests.get(
        f"{NEIS}/schoolInfo",
        params={"Type": "json", "SCHUL_NM": SCHOOL_NAME},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    rows = r.json()["schoolInfo"][1]["row"]
    row = next(x for x in rows if x["SCHUL_NM"] == SCHOOL_NAME)
    cfg["neis"] = {"atpt": row["ATPT_OFCDC_SC_CODE"], "code": row["SD_SCHUL_CODE"]}
    config.save_config(cfg)
    return cfg["neis"]["atpt"], cfg["neis"]["code"]


def _query(atpt: str, code: str, **date_params) -> dict:
    r = requests.get(
        f"{NEIS}/mealServiceDietInfo",
        params={
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": atpt,
            "SD_SCHUL_CODE": code,
            **date_params,
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    if "mealServiceDietInfo" not in data:   # INFO-200 = 해당 날짜 데이터 없음
        return {}
    meals = {}
    for row in data["mealServiceDietInfo"][1]["row"]:
        meals.setdefault(row["MLSV_YMD"], {})[row["MMEAL_SC_NM"]] = _clean_dish(
            row["DDISH_NM"]
        )
    return meals  # {YYYYMMDD: {조식: [...], 중식: [...], 석식: [...]}}


def fetch_meals(cfg: dict, date: datetime.date = None) -> dict:
    date = date or datetime.date.today()
    ymd = date.strftime("%Y%m%d")
    try:
        atpt, code = get_school_code(cfg)
    except Exception as e:
        config.log(f"급식: 학교코드 조회 실패 ({e})")
        return _from_cache(ymd)

    # 1차: 당일 조회
    try:
        meals = _query(atpt, code, MLSV_YMD=ymd)
        result = meals.get(ymd, {})
        result["_cached"] = False
        config.save_cache_entry("meal", {"date": ymd, "data": result})
        return result
    except Exception as e:
        config.log(f"급식: 당일 조회 실패 ({e}), 주간 조회 시도")

    # 2차: 주간 범위 조회
    try:
        frm = (date - datetime.timedelta(days=3)).strftime("%Y%m%d")
        to = (date + datetime.timedelta(days=3)).strftime("%Y%m%d")
        meals = _query(atpt, code, MLSV_FROM_YMD=frm, MLSV_TO_YMD=to)
        result = meals.get(ymd, {})
        result["_cached"] = False
        config.save_cache_entry("meal", {"date": ymd, "data": result})
        return result
    except Exception as e:
        config.log(f"급식: 주간 조회도 실패 ({e}), 캐시 사용")

    return _from_cache(ymd)


def _from_cache(ymd: str) -> dict:
    cached = config.load_cache().get("meal")
    if cached and cached.get("date") == ymd:
        data = dict(cached["data"])
        data["_cached"] = True
        return data
    return {"_cached": True}


if __name__ == "__main__":
    cfg = config.load_config()
    meals = fetch_meals(cfg)
    print(f"캐시 사용: {meals.pop('_cached', False)}")
    for name in ("조식", "중식", "석식"):
        print(f"\n[{name}]")
        for item in meals.get(name, ["(없음)"]):
            print(" -", item)
