@echo off
chcp 65001 >nul
rem 백업 06: PowerShell 없이 cmd만 사용
setlocal enabledelayedexpansion

cd /d "%~dp0..\.."

python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 필요합니다.
    pause
    exit /b 1
)

if exist ".venv" rmdir /s /q ".venv"
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec

set "APP_DIR=%LOCALAPPDATA%\하태욱프로그램"
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\하태욱 프로그램"
if not exist "%APP_DIR%" mkdir "%APP_DIR%"
del /q "%APP_DIR%\*.exe" 2>nul
copy /y "dist\하태욱 프로그램.exe" "%APP_DIR%\" >nul
if not exist "%START_MENU%" mkdir "%START_MENU%"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%START_MENU%\하태욱 프로그램.lnk'); $s.TargetPath='%APP_DIR%\하태욱 프로그램.exe'; $s.WorkingDirectory='%APP_DIR%'; $s.IconLocation='%APP_DIR%\하태욱 프로그램.exe,0'; $s.Save()" >nul 2>&1

echo 설치 완료.
pause
