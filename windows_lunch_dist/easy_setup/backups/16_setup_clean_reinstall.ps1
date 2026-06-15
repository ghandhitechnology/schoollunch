# 백업 16: 기존 설치를 완전히 제거하고 새로 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$AppName = "하태욱 프로그램"
$AppDirName = "하태욱프로그램"

Write-Host "기존 설치를 제거합니다..." -ForegroundColor Yellow
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\$AppDirName" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:APPDATA\$AppDirName" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\$AppName" -ErrorAction SilentlyContinue
Remove-Item -Force "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\$AppName.lnk" -ErrorAction SilentlyContinue
Remove-Item -Force "$env:USERPROFILE\Desktop\$AppName.lnk" -ErrorAction SilentlyContinue
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "$AppDirName" /f 2>nul | Out-Null

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot
if (Test-Path ".venv") { Remove-Item -Recurse -Force ".venv" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
