@echo off
chcp 65001 >nul
rem 백업 39: 원클릭 복구
setlocal enabledelayedexpansion

cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File easy_setup\backups\20_setup_emergency_repair.ps1
