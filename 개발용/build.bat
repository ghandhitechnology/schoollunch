@echo off
chcp 65001 >nul
rem ── 하태욱 프로그램.exe 빌드 (Windows에서 실행) ──
rem 사전 준비: python 3.10+ 설치 후  pip install -r requirements.txt

setlocal enabledelayedexpansion

python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] python을 찾을 수 없습니다. Python 3.10 이상을 설치하세요.
    pause
    exit /b 1
)

pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [오류] pyinstaller를 찾을 수 없습니다. 'pip install -r requirements.txt'를 실행하세요.
    pause
    exit /b 1
)

rem version.py를 Windows 파일 메타데이터에도 반영한다.
python generate_version_info.py
if errorlevel 1 exit /b 1

rem PyInstaller가 한글 경로/파일명을 다룰 때 안정적인 .spec 빌드를 사용한다.
pyinstaller --noconfirm --clean windows_build.spec
if errorlevel 1 (
    echo.
    echo 빌드에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo 빌드 완료: dist\하태욱 프로그램.exe
pause
