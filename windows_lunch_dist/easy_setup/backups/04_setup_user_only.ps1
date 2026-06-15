# 백업 04: 관리자 권한 없이 사용자 전용 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$python = (Get-Command python -ErrorAction Stop).Source
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec

# install_windows.ps1은 이미 사용자 폴더만 사용하므로 추가 변경 불필요
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
