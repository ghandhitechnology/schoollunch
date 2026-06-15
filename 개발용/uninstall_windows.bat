@echo off
chcp 65001 >nul
rem ── 하태욱 프로그램 Windows 제거 (cmd) ──

setlocal enabledelayedexpansion

set "APP_NAME=하태욱 프로그램"
set "APP_DIR_NAME=하태욱프로그램"
set "INSTALL_DIR=%LOCALAPPDATA%\%APP_DIR_NAME%"
set "DATA_DIR=%APPDATA%\%APP_DIR_NAME%"
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\%APP_NAME%"

echo [%APP_NAME%] 제거를 시작합니다...

rem 실행 중인 프로세스 종료
powershell -NoProfile -Command "Get-Process | Where-Object { $_.ProcessName -like '*하태욱*' -or $_.Path -like '*%APP_DIR_NAME%*' } | Stop-Process -Force -ErrorAction SilentlyContinue" 2>nul

rem 설치 폐기지
if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
    echo 설치 폐기지 제거: %INSTALL_DIR%
)

rem 설정/캐시
if exist "%DATA_DIR%" (
    rmdir /s /q "%DATA_DIR%"
    echo 설정/캐시 제거: %DATA_DIR%
)

rem 시작 메뉴 바로가기
if exist "%START_MENU%" (
    rmdir /s /q "%START_MENU%"
    echo 시작 메뉴 바로가기 제거
)

rem 바탕화면 바로가기
if exist "%USERPROFILE%\Desktop\%APP_NAME%.lnk" (
    del /q "%USERPROFILE%\Desktop\%APP_NAME%.lnk"
    echo 바탕화면 바로가기 제거
)

rem 자동 실행 레지스트리
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "하태욱프로그램" /f >nul 2>&1

echo.
echo 제거가 완료되었습니다.
pause
