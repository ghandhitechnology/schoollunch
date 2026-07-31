@echo off
chcp 65001 >nul
title 하태욱 프로그램 설치
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo 설치에 실패했습니다. 위 오류 메시지를 확인하세요.
pause
exit /b %RESULT%
