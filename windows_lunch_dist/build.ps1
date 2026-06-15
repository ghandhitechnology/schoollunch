# 하태욱 프로그램.exe 빌드 (PowerShell)
# 사전 준비: Python 3.10+ 설치 후  pip install -r requirements.txt
#
# 실행:  powershell -ExecutionPolicy Bypass -File build.ps1

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

# 스크립트 위치를 기준으로 동작하므로 어느 폴더에서 실행해도 된다.
Set-Location -Path $PSScriptRoot

function Test-Command { param([string]$Name) return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

if (-not (Test-Command "python")) {
    Write-Host "[오류] python 을 찾을 수 없습니다. Python 3.10 이상을 설치하세요." -ForegroundColor Red
    exit 1
}

# pyinstaller 가 PATH 에 없어도 python -m PyInstaller 로 동작하도록 보장한다.
python -m pip install pyinstaller --disable-pip-version-check 2>&1 | Out-Null

Write-Host "[하태욱 프로그램] 빌드를 시작합니다..." -ForegroundColor Green

# 한글 파일명/경로와 버전·manifest 리소스를 포함하기 위해 .spec 빌드를 사용한다.
python -m PyInstaller --noconfirm --clean windows_build.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "빌드 실패 (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "빌드 완료: dist\하태욱 프로그램.exe" -ForegroundColor Green
