@echo off
chcp 65001 >nul
rem 백업 01: 이미 Python이 PATH에 있는 경우 사용
setlocal enabledelayedexpansion

cd /d "%~dp0..\.."

python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python을 찾을 수 없습니다. 다른 백업 방법을 시도하세요.
    pause
    exit /b 1
)

if exist ".venv" rmdir /s /q ".venv"
python -m venv .venv
if errorlevel 1 (
    echo [오류] 가상 환경 생성 실패
    pause
    exit /b 1
)

.venv\Scripts\pip install -r requirements.txt
if errorlevel 1 (
    echo [오류] 패키지 설치 실패
    pause
    exit /b 1
)

.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
if errorlevel 1 (
    echo [오류] 빌드 실패
    pause
    exit /b 1
)

powershell -ExecutionPolicy Bypass -File install_windows.ps1
echo.
echo 완료. 종료하려면 아무 키나 누르세요.
pause
