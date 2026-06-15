# 백업 34: 자동 시작만 등록

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$AppDirName = "하태욱프로그램"
$AppDir = Join-Path $env:LOCALAPPDATA $AppDirName
$Exe = Join-Path $AppDir "하태욱 프로그램.exe"

if (-not (Test-Path $Exe)) {
    Write-Host "[오류] $Exe 파일이 없습니다." -ForegroundColor Red
    pause
    exit 1
}

Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name $AppDirName -Value "`"$Exe`"" -Force
Write-Host "자동 시작 등록 완료." -ForegroundColor Green
pause
