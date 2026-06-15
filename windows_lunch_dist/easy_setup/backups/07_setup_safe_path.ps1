# 백업 07: 경로에 공백/한글이 있으면 안전한 임시 경로로 복사 후 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$SafePath = "C:\schoollunch_setup"

if ($ProjectRoot -notmatch '[\s]') {
    Write-Host "현재 경로가 안전합니다. 일반 설치를 진행합니다." -ForegroundColor Green
} else {
    Write-Host "경로에 공백이 있어 임시 위치로 복사합니다." -ForegroundColor Yellow
    if (Test-Path $SafePath) { Remove-Item -Recurse -Force $SafePath }
    Copy-Item -Recurse -Force $ProjectRoot $SafePath
    $ProjectRoot = $SafePath
}

Set-Location $ProjectRoot
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1

pause
