# -*- coding: utf-8 -*-
"""네트워크 준비 상태 확인 및 fetch 재시도."""
import sys
import time
from typing import Callable, TypeVar

import requests

import config

NEIS_URL = "https://open.neis.go.kr"
COMCI_URL = "http://comci.net:4082/st"
PROBE_TIMEOUT = 5

DEFAULT_MAX_WAIT_SEC = 300
DEFAULT_RETRY_SEC = 10
DEFAULT_FETCH_RETRIES = 3
DEFAULT_FETCH_BACKOFF = (5, 10, 20)

T = TypeVar("T")


def _windows_adapter_up() -> bool:
    """Windows: wininet으로 어댑터 연결 여부를 빠르게 확인한다."""
    if sys.platform != "win32":
        return True
    import ctypes
    flags = ctypes.c_ulong()
    connected = ctypes.windll.wininet.InternetGetConnectedState(ctypes.byref(flags), 0)
    return bool(connected)


def _probe(url: str, method: str = "head") -> bool:
    try:
        if method == "head":
            requests.head(url, timeout=PROBE_TIMEOUT)
        else:
            requests.get(url, timeout=PROBE_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        return True
    except requests.RequestException:
        return False


def is_network_ready() -> bool:
    """급식(NEIS)과 시간표(comci) 엔드포인트가 모두 응답할 때만 True."""
    if not _windows_adapter_up():
        return False
    if not _probe(NEIS_URL, "head"):
        return False
    if not _probe(COMCI_URL, "get"):
        return False
    return True


def wait_for_network(max_wait_sec: int = DEFAULT_MAX_WAIT_SEC,
                     retry_sec: int = DEFAULT_RETRY_SEC) -> bool:
    deadline = time.monotonic() + max_wait_sec
    while time.monotonic() < deadline:
        if is_network_ready():
            return True
        config.log("인터넷 연결 대기 중... (NEIS + comci)")
        time.sleep(retry_sec)
    return False


def fetch_with_retries(fn: Callable[[], T],
                       retries: int = DEFAULT_FETCH_RETRIES,
                       backoff: tuple[int, ...] = DEFAULT_FETCH_BACKOFF) -> T:
    """RequestException 발생 시 지수적 대기 후 재시도한다."""
    last_exc = None
    attempts = max(1, retries)
    for attempt in range(attempts):
        try:
            return fn()
        except requests.RequestException as e:
            last_exc = e
            if attempt >= attempts - 1:
                raise
            delay = backoff[attempt] if attempt < len(backoff) else backoff[-1]
            config.log(f"네트워크 요청 실패 ({e!r}) — {delay}초 후 재시도")
            time.sleep(delay)
    raise last_exc  # pragma: no cover
