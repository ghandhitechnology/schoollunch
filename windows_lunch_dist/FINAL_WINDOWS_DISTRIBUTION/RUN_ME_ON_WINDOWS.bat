@echo off
chcp 65001 >nul
setlocal

set "SCRIPT=%~dp0setup_windows_final.ps1"
if not exist "%SCRIPT%" (
    echo [ERROR] setup_windows_final.ps1 not found.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
exit /b %ERRORLEVEL%
