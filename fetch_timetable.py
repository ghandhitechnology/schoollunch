# -*- coding: utf-8 -*-
"""컴시간알리미(comci.net) 비공식 API에서 시간표를 가져온다.

서버 스크립트의 경로·접두사·자료 키 번호가 주기적으로 바뀌므로,
매 실행마다 /st 페이지를 받아 정규식으로 현재 값을 추출한다.

반환 형식 (fetch_today):
{
  "date": datetime.date,         # 표시 대상 날짜 (주말이면 다가오는 월요일)
  "weekday_label": "금",
  "periods": [{"period": 1, "time": "08:50", "subject": "공수1", "teacher": "김완*"}, ...],
  "_cached": bool,
}
"""
import base64
import copy
import datetime
import json
import re

import requests

import config

BASE = "http://comci.net:4082"
SCHOOL_NAME = "인천과학고등학교"
TIMEOUT = 10
_HEADERS = {"User-Agent": "Mozilla/5.0"}

_RE_ROUTE = re.compile(r"\./(\d+)\?(\d+)l")
_RE_PREFIX = re.compile(r"sc_data\('(\d+)_'")
_RE_DAY = re.compile(r"일일자료=Q자료\(자료\.자료(\d+)")
_RE_TEACHER = re.compile(r"성명=Q성명\(자료\.자료(\d+)\[th\]")
_RE_SUBJECT = re.compile(r"자료\.자료(\d+)\[sb\]")

WEEKDAYS = "월화수목금토일"


def _bootstrap() -> dict:
    """메인 스크립트에서 현재 라우트/접두사/자료 키를 추출."""
    r = requests.get(f"{BASE}/st", headers=_HEADERS, timeout=TIMEOUT)
    r.encoding = "EUC-KR"
    script = r.text
    route, search_q = _RE_ROUTE.search(script).groups()
    return {
        "route": route,
        "search_q": search_q,
        "prefix": _RE_PREFIX.search(script).group(1),
        "day_key": _RE_DAY.search(script).group(1),
        "teacher_key": _RE_TEACHER.search(script).group(1),
        "subject_key": _RE_SUBJECT.search(script).group(1),
    }


def _search_school(boot: dict, name: str) -> int:
    q = "".join(f"%{b:02X}" for b in name.encode("euc-kr"))
    url = f"{BASE}/{boot['route']}?{boot['search_q']}l{q}"
    r = requests.get(url, headers=_HEADERS, timeout=TIMEOUT)
    r.encoding = "UTF-8"
    rows = json.loads(r.text.replace("\x00", ""))["학교검색"]
    if not rows:
        raise LookupError(f"컴시간알리미에서 '{name}' 검색 결과 없음")
    # [지역코드, 지역명, 학교명, 학교코드] — 정확히 일치하는 학교 우선
    for row in rows:
        if row[2] == name:
            return row[3]
    return rows[0][3]


def get_school_code(cfg: dict, boot: dict) -> int:
    code = cfg.get("comcigan_code")
    if code:
        return code
    code = _search_school(boot, SCHOOL_NAME)
    cfg["comcigan_code"] = code
    config.save_config(cfg)
    return code


def _fetch_raw(boot: dict, school_code: int) -> dict:
    token = base64.b64encode(
        f"{boot['prefix']}_{school_code}_0_1".encode()
    ).decode()
    r = requests.get(f"{BASE}/{boot['route']}?{token}", headers=_HEADERS, timeout=TIMEOUT)
    r.encoding = "UTF-8"
    return json.loads(r.text.replace("\x00", ""))


def _decode_week(raw: dict, boot: dict, grade: int, cls: int) -> dict:
    subjects = raw[f"자료{boot['subject_key']}"]
    teachers = raw[f"자료{boot['teacher_key']}"]
    table = raw[f"자료{boot['day_key']}"]   # [grade][class][day(1=월..5=금)][0]=교시수, [1..]=과목코드
    period_times = raw.get("일과시간", [])  # ["1(08:50)", ...]

    times = []
    for t in period_times:
        m = re.search(r"\((\d{2}:\d{2})\)", str(t))
        times.append(m.group(1) if m else "")

    days = []
    for day in range(1, 6):
        row = table[grade][cls][day]
        count = row[0] if row and isinstance(row[0], int) else 0
        periods = []
        for i, x in enumerate(row[1 : count + 1], start=1):
            if not isinstance(x, int) or x == 0:
                periods.append({"period": i, "time": times[i - 1] if i <= len(times) else "", "subject": "", "teacher": ""})
                continue
            s, th = divmod(x, 1000)
            periods.append({
                "period": i,
                "time": times[i - 1] if i <= len(times) else "",
                "subject": str(subjects[s]) if s < len(subjects) else "?",
                "teacher": str(teachers[th]) if th < len(teachers) else "",
            })
        # 끝쪽 빈 교시 제거
        while periods and not periods[-1]["subject"]:
            periods.pop()
        days.append(periods)
    return {"days": days}


def _resolve_teachers(timetable: dict, roster: list) -> dict:
    """컴시간 서버는 교사명을 '김완*'처럼 가려서 보낸다. 설정에 입력한 전체 이름
    명단에서 접두사가 정확히 한 명과 일치하면 전체 이름으로 바꿔 보여 준다."""
    if not roster:
        return timetable
    for period in timetable.get("periods", []):
        name = period.get("teacher") or ""
        if not name.endswith("*"):
            continue
        prefix = name.rstrip("*")
        if not prefix:
            continue
        matches = [full for full in roster
                   if isinstance(full, str) and full.startswith(prefix) and len(full) > len(prefix)]
        if len(matches) == 1:
            period["teacher"] = matches[0]
    return timetable


def _target_date(today: datetime.date = None) -> datetime.date:
    """주말이면 다가오는 월요일을 표시 대상으로."""
    d = today or datetime.date.today()
    if d.weekday() >= 5:  # 토(5), 일(6)
        d += datetime.timedelta(days=7 - d.weekday())
    return d


def fetch_today(cfg: dict, today: datetime.date = None) -> dict:
    grade = int(cfg.get("grade", 1))
    cls = int(cfg.get("class_num", 1))
    target = _target_date(today)

    try:
        boot = _bootstrap()
        code = get_school_code(cfg, boot)
        raw = _fetch_raw(boot, code)
        week = _decode_week(raw, boot, grade, cls)
        result = {
            "date": target.isoformat(),
            "weekday_label": WEEKDAYS[target.weekday()],
            "periods": week["days"][target.weekday()],
            "_cached": False,
        }
        # 캐시에는 원본(마스킹된) 이름을 저장해 명단을 나중에 고쳐도 다시 매칭되게 한다
        config.save_cache_entry("timetable", result)
        return _resolve_teachers(copy.deepcopy(result), cfg.get("teacher_names") or [])
    except Exception as e:
        config.log(f"시간표: 조회 실패 ({e}), 캐시 사용")
        cached = config.load_cache().get("timetable")
        if cached:
            cached = copy.deepcopy(cached)
            cached["_cached"] = True
            return _resolve_teachers(cached, cfg.get("teacher_names") or [])
        return {
            "date": target.isoformat(),
            "weekday_label": WEEKDAYS[target.weekday()],
            "periods": [],
            "_cached": True,
        }


if __name__ == "__main__":
    cfg = config.load_config()
    print(f"=== {cfg.get('grade', 1)}-{cfg.get('class_num', 1)} 시간표 ===")
    tt = fetch_today(cfg)
    print(f"{tt['date']} ({tt['weekday_label']})  캐시: {tt['_cached']}")
    for p in tt["periods"]:
        print(f"  {p['period']}교시 {p['time']:>5}  {p['subject']:<8} {p['teacher']}")
