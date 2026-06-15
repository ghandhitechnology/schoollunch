@echo off
chcp 65001 >nul
rem ── 하태욱 프로그램 Windows 설치 (cmd 더블클릭용) ──
rem 빌드된 dist\하태욱 프로그램.exe 를 설치하고 바로가기를 만든다.
rem 실제 설치 로직은 install_windows.ps1 (= easy_setup\common.ps1) 에 있다.

setlocal
set "INSTALLER=%~dp0install_windows.ps1"

if not exist "%INSTALLER%" (
    echo [오류] install_windows.ps1 을 찾을 수 없습니다.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALLER%"
pause
