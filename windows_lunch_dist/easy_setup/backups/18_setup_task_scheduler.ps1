# 백업 18: 작업 예약으로 자동 시작 설정

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$AppName = "하태욱프로그램"
$AppDir = Join-Path $env:LOCALAPPDATA "하태욱프로그램"
$Exe = Join-Path $AppDir "하태욱 프로그램.exe"

if (-not (Test-Path $Exe)) {
    Write-Host "[오류] $Exe 파일이 없습니다. 먼저 프로그램을 설치하세요." -ForegroundColor Red
    pause
    exit 1
}

$action = New-ScheduledTaskAction -Execute "$Exe" -Argument "--once"
$trigger = New-ScheduledTaskTrigger -AtLogon
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $AppName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "작업 예약 등록 완료." -ForegroundColor Green
pause
