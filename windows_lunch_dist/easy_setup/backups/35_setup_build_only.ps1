# 백업 35: 빌드만 수행

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec

$Exe = Join-Path $ProjectRoot "dist\하태욱 프로그램.exe"
if (Test-Path $Exe) {
    Write-Host "빌드 완료: $Exe" -ForegroundColor Green
} else {
    Write-Host "[오류] 빌드 실패" -ForegroundColor Red
}
pause
