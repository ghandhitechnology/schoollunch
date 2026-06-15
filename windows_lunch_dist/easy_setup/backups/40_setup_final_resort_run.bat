@echo off
chcp 65001 >nul
rem 백업 40: 최후의 수단 - 소스 코드 직접 실행
setlocal enabledelayedexpansion

cd /d "%~dp0..\.."
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 필요합니다. https://www.python.org/downloads/ 에서 설치하세요.
    pause
    exit /b 1
)

if not exist ".venv" python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py --ui
