# 백업 02: 오프라인 설치
# 사전에 easy_setup\wheelhouse 에 .whl 파일을 다운로드해야 합니다.

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$Wheelhouse = Join-Path $PSScriptRoot "..\wheelhouse"
if (-not (Test-Path $Wheelhouse)) {
    Write-Host "[오류] wheelhouse 폴더가 없습니다." -ForegroundColor Red
    Write-Host "먼저 인터넷 연결된 환경에서 아래 명령을 실행하여 패키지를 다운로드하세요:" -ForegroundColor Yellow
    Write-Host "  pip download -r requirements.txt -d wheelhouse" -ForegroundColor Cyan
    pause
    exit 1
}

python -m venv .venv
.\.venv\Scripts\pip install --no-index --find-links "$Wheelhouse" -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
