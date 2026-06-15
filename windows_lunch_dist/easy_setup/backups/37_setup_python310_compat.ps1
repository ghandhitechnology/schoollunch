# 백업 37: Python 3.10 호환 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$ver = python --version 2>&1
if ($ver -notmatch "Python 3\.10") {
    Write-Warning "이 스크립트는 Python 3.10을 권장합니다. 현재: $ver"
}

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
