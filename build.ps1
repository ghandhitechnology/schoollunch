# 하태욱 프로그램.exe 빌드 (PowerShell)
# 사전 준비: python 3.10+ 설치 후  pip install -r requirements.txt
#
# 실행:  powershell -ExecutionPolicy Bypass -File build.ps1
#   또는  .\build.ps1   (실행 정책이 막히면 위 명령 사용)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

# 스크립트 위치를 기준으로 동작 (어느 폴더에서 실행해도 OK)
Set-Location -Path $PSScriptRoot

Write-Host "[하태욱 프로그램] 빌드를 시작합니다..." -ForegroundColor Green

pyinstaller --onefile --noconsole `
  --name "하태욱 프로그램" `
  --icon "assets\icons\app_icon.ico" `
  --add-data "assets;assets" `
  main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "빌드 실패 (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "빌드 완료: dist\하태욱 프로그램.exe" -ForegroundColor Green
