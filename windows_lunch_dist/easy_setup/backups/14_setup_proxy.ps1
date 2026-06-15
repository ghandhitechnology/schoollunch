# 백업 14: 프록시 환경에서 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$proxy = (Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name ProxyServer -ErrorAction SilentlyContinue).ProxyServer
if (-not $proxy) {
    $proxy = Read-Host "프록시 주소를 입력하세요 (예: 127.0.0.1:8080)"
}

$env:HTTP_PROXY = "http://$proxy"
$env:HTTPS_PROXY = "http://$proxy"

python -m venv .venv
.\.venv\Scripts\pip install --proxy "http://$proxy" -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
