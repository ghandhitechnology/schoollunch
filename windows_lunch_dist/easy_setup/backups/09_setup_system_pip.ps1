# 백업 09: 가상 환경 생성이 안 될 때 시스템 Python에 직접 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

Write-Warning "가상 환경 없이 시스템 Python에 패키지를 설치합니다."
pip install --user -r requirements.txt
python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
