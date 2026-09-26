@echo off
chcp 65001 >nul
rem ── 하태욱 프로그램.exe 빌드 (Windows cmd) ──
rem 사전 준비: Python 3.10+ 설치 후  pip install -r requirements.txt

setlocal
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] python 을 찾을 수 없습니다. Python 3.10 이상을 설치하세요.
    pause
    exit /b 1
)

rem pyinstaller 가 PATH 에 없어도 python -m PyInstaller 로 동작하도록 보장한다.
python -m pip install pyinstaller --disable-pip-version-check >nul 2>&1

rem 한글 경로/파일명에 안정적인 .spec 빌드를 사용한다.
rem version.py를 Windows 파일 메타데이터에도 반영한다.
python generate_version_info.py
if errorlevel 1 exit /b 1

python -m PyInstaller --noconfirm --clean windows_build.spec
if errorlevel 1 (
    echo.
    echo 빌드에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo 빌드 완료: dist\하태욱 프로그램.exe
pause
