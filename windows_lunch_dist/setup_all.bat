@echo off
chcp 65001 >nul
rem ============================================================
rem  하태욱 프로그램 - Windows 자동 설치 (더블클릭용)
rem  이 파일을 더블클릭하면 설치가 시작됩니다.
rem  10가지 설치 방법을 자동으로 시도하므로 대부분 그냥 기다리면 됩니다.
rem ============================================================

setlocal
set "MASTER=%~dp0easy_setup\setup_master.ps1"

if not exist "%MASTER%" (
    echo [오류] 설치 스크립트를 찾을 수 없습니다:
    echo        %MASTER%
    echo.
    echo 압축이 제대로 풀렸는지, easy_setup 폴더가 있는지 확인하세요.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%MASTER%"
set "EXITCODE=%ERRORLEVEL%"

if "%EXITCODE%" neq "0" (
    echo.
    echo [안내] 자동 설치가 끝나지 못했습니다. (종료 코드: %EXITCODE%^)
    echo        위 메시지와 easy_setup 폴더 안의 개별 방법을 확인해 주세요.
    pause
)

exit /b %EXITCODE%
