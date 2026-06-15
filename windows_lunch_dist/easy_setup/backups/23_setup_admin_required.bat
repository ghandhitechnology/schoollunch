@echo off
chcp 65001 >nul
rem 백업 23: 관리자 권한으로 실행해야 할 때
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [오류] 관리자 권한이 필요합니다. 이 파일을 마우스 오른쪽 버튼으로 클릭하고 '관리자 권한으로 실행'을 선택하세요.
    pause
    exit /b 1
)

cd /d "%~dp0..\.."
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
