@echo off
chcp 65001 >nul
setlocal

set "SCRIPT=%~dp0uninstall_windows_final.ps1"
if not exist "%SCRIPT%" (
    echo [ERROR] uninstall_windows_final.ps1 not found.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
pause
