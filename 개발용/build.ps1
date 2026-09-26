# 하태욱 프로그램.exe 빌드 (PowerShell)
# 사전 준비: python 3.10+ 설치 후  pip install -r requirements.txt
#
# 실행:  powershell -ExecutionPolicy Bypass -File build.ps1
#   또는  .\build.ps1   (실행 정책이 막히면 위 명령 사용)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 스크립트 위치를 기준으로 동작 (어느 폴꺼에서 실행핮어도 OK)
Set-Location -Path $PSScriptRoot

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-Command "python")) {
    Write-Host "[오류] python을 찾을 수 없습니다. Python 3.10 이상을 설치하세요." -ForegroundColor Red
    exit 1
}

if (-not (Test-Command "pyinstaller")) {
    Write-Host "[오류] pyinstaller를 찾을 수 없습니다. 'pip install -r requirements.txt'를 실행하세요." -ForegroundColor Red
    exit 1
}

Write-Host "[하태욱 프로그램] 빌드를 시작합니다..." -ForegroundColor Green

# version.py를 Windows 파일 메타데이터에도 반영한다.
python generate_version_info.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 한글 파일명/경로 문제를 피하고 버전·manifest 리소스를 포함하려면 .spec 빌드를 사용한다.
pyinstaller --noconfirm --clean windows_build.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host "빌드 실패 (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "빌드 완료: dist\하태욱 프로그램.exe" -ForegroundColor Green
