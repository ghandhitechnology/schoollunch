# 백업 33: 완전 제거만 수행

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$AppName = "하태욱 프로그램"
$AppDirName = "하태욱프로그램"

Write-Host "프로그램을 완전히 제거합니다..." -ForegroundColor Yellow
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\$AppDirName" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:APPDATA\$AppDirName" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\$AppName" -ErrorAction SilentlyContinue
Remove-Item -Force "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\$AppName.lnk" -ErrorAction SilentlyContinue
Remove-Item -Force "$env:USERPROFILE\Desktop\$AppName.lnk" -ErrorAction SilentlyContinue
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "$AppDirName" /f 2>nul | Out-Null
Unregister-ScheduledTask -TaskName $AppDirName -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "제거 완료." -ForegroundColor Green
pause
