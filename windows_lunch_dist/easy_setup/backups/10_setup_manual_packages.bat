@echo off
chcp 65001 >nul
rem 백업 10: 수동으로 패키지 다운로드 후 오프라인 설치
setlocal enabledelayedexpansion

cd /d "%~dp0..\.."

python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 필요합니다.
    pause
    exit /b 1
)

if not exist "easy_setup\wheelhouse" mkdir "easy_setup\wheelhouse"
echo 필요한 패키지를 다운로드합니다. 인터넷 연결이 필요합니다.
pip download -r requirements.txt -d "easy_setup\wheelhouse"

python -m venv .venv
.venv\Scripts\pip install --no-index --find-links "easy_setup\wheelhouse" -r requirements.txt
.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
