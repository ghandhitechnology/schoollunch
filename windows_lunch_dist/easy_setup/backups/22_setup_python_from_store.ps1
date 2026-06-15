# 백업 22: Microsoft Store Python 사용 (App Installer)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

Write-Host "Microsoft Store에서 Python 3.12를 설치합니다..." -ForegroundColor Cyan
Start-Process "ms-windows-store://pdp/?ProductId=9NCVDN91XZQP"
Read-Host "Store에서 Python 설치가 완료되면 Enter 키를 누르세요"

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
