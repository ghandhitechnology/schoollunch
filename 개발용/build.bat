@echo off
chcp 65001 >nul
rem PowerShell 빌드 스크립트가 가상환경과 의존성을 자동 준비한다.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" echo 빌드에 실패했습니다.
pause
exit /b %RESULT%
