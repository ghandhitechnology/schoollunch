# 백업 26: 설정은 유지하면서 프로그램만 재설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$AppDir = Join-Path $env:LOCALAPPDATA "하태욱프로그램"
$DataDir = Join-Path $env:APPDATA "하태욱프로그램"

# 설정 백업
$tempBackup = "$env:TEMP\hataewook_backup"
if (Test-Path $DataDir) {
    if (Test-Path $tempBackup) { Remove-Item -Recurse -Force $tempBackup }
    Copy-Item -Recurse -Force $DataDir $tempBackup
}

# 프로그램 재설치
if (Test-Path $AppDir) { Remove-Item -Recurse -Force $AppDir }
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1

# 설정 복원
if (Test-Path $tempBackup) {
    if (Test-Path $DataDir) { Remove-Item -Recurse -Force $DataDir }
    Copy-Item -Recurse -Force $tempBackup $DataDir
}

Write-Host "프로그램 재설치 및 설정 복원 완료." -ForegroundColor Green
pause
