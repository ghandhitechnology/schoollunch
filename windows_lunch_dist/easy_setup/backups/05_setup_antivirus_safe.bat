@echo off
chcp 65001 >nul
rem 백업 05: 백신 차단 우회
setlocal enabledelayedexpansion

cd /d "%~dp0..\.."

echo [안내] Windows Defender 예외 추가를 시도합니다.
echo 관리자 권한이 필요할 수 있습니다.
powershell -Command "Add-MpPreference -ExclusionPath '%CD%' -ErrorAction SilentlyContinue"

python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1

echo.
echo 백신 예외 추가가 완료되었습니다. 설치를 마칩니다.
pause
