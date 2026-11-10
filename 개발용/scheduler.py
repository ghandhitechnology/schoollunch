# -*- coding: utf-8 -*-
"""백그라운드 자동 갱신 스케줄러.

트레이 프로세스에서 도는 데몬 스레드다. 설정 창은 별도 프로세스로 열리므로
(main.run_tray 의 on_settings 참고) 설정 변경은 config.json 을 거쳐야만 전달된다.
그래서 매 tick 마다 설정을 다시 읽는다 — 트레이를 재시작하지 않아도 주기 변경이 먹는다.

판단 로직(decide)은 시계를 직접 읽지 않는 순수 함수라 가짜 시계로 테스트할 수 있다.
"""
import datetime
import threading
import time

import config

TICK_SEC = 20
# tick 간격보다 이만큼 더 벌어지면 절전/최대절전에서 깨어난 것으로 본다.
# monotonic 시계의 절전 중 동작이 OS 마다 달라(macOS/Linux 는 멈추고 Windows 는 흐른다)
# 어디서나 같게 동작하는 벽시계 간격만 본다.
WAKE_GAP_SEC = 120
# 실패 후 재시도 간격. 깨어났는데 Wi-Fi 가 아직 안 붙은 경우를 덮는다.
BACKOFF_STEPS_SEC = (60, 120, 240, 480, 900)


def backoff_delay(fail_count: int) -> int:
    """연속 실패 횟수에 대응하는 재시도 대기 시간(초)."""
    if fail_count <= 0:
        return 0
    return BACKOFF_STEPS_SEC[min(fail_count, len(BACKOFF_STEPS_SEC)) - 1]


def decide(*, today, last_success_date, seconds_since_success,
           seconds_since_failure, wall_gap, interval_min, fail_count):
    """갱신할지 말지 결정한다. 시계를 읽지 않는 순수 함수.

    반환: (갱신할까, 이유). 이유는 로그에만 쓰인다.
    우선순위: 최초 → 재시도(backoff) → 날짜 변경 → 절전 해제 → 주기.
    """
    if last_success_date is None and fail_count == 0:
        return True, "최초 갱신"

    # 실패 중에는 backoff 가 다른 트리거보다 우선한다.
    # 그렇지 않으면 네트워크가 끊긴 동안 날짜 변경/절전 해제가 매 tick 재시도를 유발한다.
    if fail_count > 0:
        delay = backoff_delay(fail_count)
        if seconds_since_failure is None or seconds_since_failure >= delay:
            return True, f"재시도 (연속 {fail_count}회 실패, {delay // 60}분 대기 후)"
        return False, ""

    # 바탕화면은 '오늘' 급식·시간표를 보여준다. 자정을 넘겼으면 주기 설정과 무관하게 갱신한다.
    if last_success_date != today:
        return True, "날짜 변경"

    if wall_gap > WAKE_GAP_SEC:
        return True, f"절전 해제 감지 ({int(wall_gap)}초 공백)"

    if interval_min > 0 and seconds_since_success is not None \
            and seconds_since_success >= interval_min * 60:
        return True, f"주기 갱신 ({interval_min}분)"

    return False, ""


def _elapsed(now, then):
    """벽시계는 NTP 보정 등으로 뒤로 갈 수 있으므로 음수는 0으로 막는다."""
    if then is None:
        return None
    return max(0.0, now - then)


def _date_of(wall_time):
    return datetime.date.fromtimestamp(wall_time)


class RefreshScheduler:
    """run_refresh 를 알맞은 시점에 호출하는 데몬 스레드.

    run_refresh 반환값 규약:
      True  — 갱신 성공
      False — 갱신 실패 (backoff 시작)
      None  — 이미 갱신 중이라 건너뜀 (성공도 실패도 아님, 상태를 바꾸지 않는다)
    """

    def __init__(self, run_refresh, load_config=None, log=None,
                 tick_sec=TICK_SEC, clock=None):
        self._run_refresh = run_refresh
        self._load_config = load_config or config.load_config
        self._log = log or config.log
        self._tick_sec = tick_sec
        self._clock = clock or time.time

        self._stop_event = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

        self._last_success_wall = None
        self._last_success_date = None
        self._last_failure_wall = None
        self._fail_count = 0
        self._prev_tick_wall = None

    # ── 상태 ──
    def seed(self, success: bool) -> None:
        """부팅 직후 main() 이 이미 한 번 갱신했음을 알려 즉시 재갱신을 막는다."""
        now = self._clock()
        with self._lock:
            if success:
                self._last_success_wall = now
                self._last_success_date = _date_of(now)
                self._fail_count = 0
                self._last_failure_wall = None
            else:
                self._fail_count = 1
                self._last_failure_wall = now

    def status(self) -> dict:
        with self._lock:
            return {
                "last_success_wall": self._last_success_wall,
                "last_success_date": self._last_success_date,
                "fail_count": self._fail_count,
            }

    def last_success_label(self) -> str:
        """트레이 메뉴에 띄울 '마지막 갱신 HH:MM' 문구."""
        state = self.status()
        when = state["last_success_wall"]
        if when is None:
            if state["fail_count"]:
                return "마지막 갱신: 실패"
            return "마지막 갱신: 없음"
        stamp = datetime.datetime.fromtimestamp(when)
        if stamp.date() == datetime.date.today():
            return f"마지막 갱신: {stamp:%H:%M}"
        return f"마지막 갱신: {stamp:%m/%d %H:%M}"

    # ── 스레드 ──
    def start(self) -> None:
        if self._thread is not None:
            return
        self._prev_tick_wall = self._clock()
        self._thread = threading.Thread(target=self._loop, name="refresh-scheduler",
                                        daemon=True)
        self._thread.start()
        self._log(f"자동 갱신 스케줄러 시작 (tick {self._tick_sec}초)")

    def stop(self) -> None:
        self._stop_event.set()

    def _loop(self) -> None:
        while not self._stop_event.wait(self._tick_sec):
            try:
                self.tick()
            except Exception as e:  # 스케줄러 스레드는 어떤 경우에도 죽으면 안 된다
                self._log(f"자동 갱신 스케줄러 오류: {e!r}")

    def tick(self) -> bool:
        """한 번의 판단 주기. 테스트에서 직접 호출할 수 있게 공개해 둔다."""
        now = self._clock()
        prev = self._prev_tick_wall
        self._prev_tick_wall = now
        wall_gap = max(0.0, now - prev) if prev is not None else 0.0

        interval_min = self.current_interval()

        with self._lock:
            last_date = self._last_success_date
            last_ok = self._last_success_wall
            last_fail = self._last_failure_wall
            fails = self._fail_count

        should, reason = decide(
            today=_date_of(now),
            last_success_date=last_date,
            seconds_since_success=_elapsed(now, last_ok),
            seconds_since_failure=_elapsed(now, last_fail),
            wall_gap=wall_gap,
            interval_min=interval_min,
            fail_count=fails,
        )
        if should:
            self.refresh(reason)
        return should

    def current_interval(self) -> int:
        """매 tick 설정을 다시 읽는다 — 설정 창(별도 프로세스) 변경을 반영하기 위해."""
        try:
            cfg = self._load_config()
        except Exception as e:
            self._log(f"자동 갱신 설정 읽기 실패, 기본값 사용: {e!r}")
            return config.DEFAULTS["refresh_interval_min"]
        return config.safe_refresh_interval(cfg.get("refresh_interval_min"))

    def refresh(self, reason: str = "수동") -> None:
        self._log(f"자동 갱신 — {reason}")
        result = False
        try:
            result = self._run_refresh()
        except Exception as e:
            self._log(f"자동 갱신 실패: {e!r}")
            result = False

        if result is None:  # 이미 갱신 중 — 상태를 건드리지 않는다
            self._log("자동 갱신 건너뜀 (이미 갱신 중)")
            return

        now = self._clock()
        with self._lock:
            if result:
                self._last_success_wall = now
                self._last_success_date = _date_of(now)
                self._fail_count = 0
                self._last_failure_wall = None
                fails = 0
            else:
                self._fail_count += 1
                self._last_failure_wall = now
                fails = self._fail_count
        if not result:
            self._log(f"자동 갱신 실패 — {backoff_delay(fails) // 60}분 후 재시도")
