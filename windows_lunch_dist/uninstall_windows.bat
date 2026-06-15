@echo off
chcp 65001 >nul
rem ── 하태욱 프로그램 Windows 제거 (cmd 더블클릭용) ──
rem 실제 제거 로직은 uninstall_windows.ps1 에 있다.

setlocal
set "UNINSTALLER=%~dp0uninstall_windows.ps1"

if not exist "%UNINSTALLER%" (
    echo [오류] uninstall_windows.ps1 을 찾을 수 없습니다.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%UNINSTALLER%"
pause
