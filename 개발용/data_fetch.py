# -*- coding: utf-8 -*-
"""급식과 시간표를 안전하게 병렬 조회한다."""
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import fetch_meal
import fetch_timetable


def _codes_are_cached(cfg: dict) -> bool:
    neis = cfg.get("neis") or {}
    return bool(neis.get("atpt") and neis.get("code") and cfg.get("comcigan_code"))


def fetch_all(
    cfg: dict,
    meal_fetch: Callable[[dict], dict] | None = None,
    timetable_fetch: Callable[[dict], dict] | None = None,
) -> tuple[dict, dict]:
    """두 독립 API를 조회한다.

    학교 코드가 아직 없는 최초 실행은 각 fetch가 설정 파일을 갱신하므로 순차 실행한다.
    이후 실행은 네트워크 대기 시간을 줄이기 위해 최대 두 스레드로 병렬 조회한다.
    """
    meal_fetch = meal_fetch or fetch_meal.fetch_meals
    timetable_fetch = timetable_fetch or fetch_timetable.fetch_today

    if not _codes_are_cached(cfg):
        return meal_fetch(cfg), timetable_fetch(cfg)

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="school-data") as pool:
        meal_future = pool.submit(meal_fetch, cfg)
        timetable_future = pool.submit(timetable_fetch, cfg)
        return meal_future.result(), timetable_future.result()
