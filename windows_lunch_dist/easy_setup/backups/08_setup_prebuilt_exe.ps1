# 백업 08: 미리 빌드된 exe가 있는 경우 설치만 진행

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$Exe = Join-Path $ProjectRoot "dist\하태욱 프로그램.exe"
if (-not (Test-Path $Exe)) {
    Write-Host "[오류] dist\하태욱 프로그램.exe 파일이 없습니다." -ForegroundColor Red
    Write-Host "빌드된 실행 파일을 dist 폴더에 넣고 다시 실행하세요." -ForegroundColor Yellow
    pause
    exit 1
}

powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
