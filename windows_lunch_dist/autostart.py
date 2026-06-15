# -*- coding: utf-8 -*-
"""OS 시작 시 자동 실행 등록."""
import os
import plistlib
import subprocess
import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "하태욱프로그램"
MACOS_LAUNCH_AGENT_LABEL = "com.hataewook.program"


def _exe_path() -> str:
    if getattr(sys, "frozen", False):   # PyInstaller exe
        return f'"{sys.executable}" --background'
    # 스크립트 위치를 기준으로 절대 경로를 생성 (작업 디렉터리와 무관)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "main.py")
    return f'"{sys.executable}" "{main_py}" --background'


def _program_arguments() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--background"]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "main.py")
    return [sys.executable, main_py, "--background"]


def _macos_plist_path() -> str:
    launch_agents = os.path.expanduser("~/Library/LaunchAgents")
    os.makedirs(launch_agents, exist_ok=True)
    return os.path.join(launch_agents, f"{MACOS_LAUNCH_AGENT_LABEL}.plist")


def _macos_launchctl(*args: str) -> None:
    try:
        subprocess.run(["launchctl", *args], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _macos_enable() -> None:
    plist_path = _macos_plist_path()
    payload = {
        "Label": MACOS_LAUNCH_AGENT_LABEL,
        "ProgramArguments": _program_arguments(),
        "RunAtLoad": True,
        "KeepAlive": False,
        "WorkingDirectory": os.path.dirname(os.path.abspath(__file__)),
        "StandardOutPath": os.path.join(os.path.expanduser("~"), "Library", "Logs", "hataewook-program.log"),
        "StandardErrorPath": os.path.join(os.path.expanduser("~"), "Library", "Logs", "hataewook-program.err.log"),
    }
    with open(plist_path, "wb") as f:
        plistlib.dump(payload, f)
    uid = os.getuid()
    _macos_launchctl("bootout", f"gui/{uid}", plist_path)
    _macos_launchctl("bootstrap", f"gui/{uid}", plist_path)


def _macos_disable() -> None:
    plist_path = _macos_plist_path()
    uid = os.getuid()
    _macos_launchctl("bootout", f"gui/{uid}", plist_path)
    try:
        os.remove(plist_path)
    except FileNotFoundError:
        pass


def enable() -> None:
    if sys.platform == "darwin":
        _macos_enable()
        return
    if sys.platform != "win32":
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        # _exe_path()는 이미 따옴표를 포함하므로 다시 감싸면 안 된다
        winreg.SetValueEx(k, VALUE_NAME, 0, winreg.REG_SZ, _exe_path())


def disable() -> None:
    if sys.platform == "darwin":
        _macos_disable()
        return
    if sys.platform != "win32":
        return
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, VALUE_NAME)
    except FileNotFoundError:
        pass


def apply(enabled: bool) -> None:
    enable() if enabled else disable()
