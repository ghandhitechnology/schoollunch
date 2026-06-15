# 백업 03: Python이 없을 때 자동 다운로드 및 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

function Test-Python {
    try { $ver = python --version 2>&1; return $ver -match "Python 3\.(1[0-9]|[2-9][0-9])" } catch { return $false }
}

if (-not (Test-Python)) {
    Write-Host "Python이 없어 자동 설치를 시도합니다..." -ForegroundColor Yellow
    $url = "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
    $installer = "$env:TEMP\python-3.12.4-amd64.exe"
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    Start-Process -FilePath $installer -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "User")
}

if (-not (Test-Python)) {
    Write-Host "[오류] Python 설치 실패" -ForegroundColor Red
    pause
    exit 1
}

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
