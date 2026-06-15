# 백업 36: 이미 빌드된 dist 파일을 설치만

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$Exe = Join-Path $ProjectRoot "dist\하태욱 프로그램.exe"
if (-not (Test-Path $Exe)) {
    Write-Host "[오류] dist\하태욱 프로그램.exe 파일이 없습니다. 먼저 빌드하세요." -ForegroundColor Red
    pause
    exit 1
}

powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
