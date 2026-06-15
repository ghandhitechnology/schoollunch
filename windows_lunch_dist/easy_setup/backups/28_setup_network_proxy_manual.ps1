# 백업 28: 수동 프록시 입력

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$proxy = Read-Host "프록시 주소를 입력하세요 (예: http://proxy.company.com:8080)"
$env:HTTP_PROXY = $proxy
$env:HTTPS_PROXY = $proxy

python -m venv .venv
.\.venv\Scripts\pip install --proxy $proxy -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
