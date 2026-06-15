# 백업 25: 바로가기만 수리

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$AppDir = Join-Path $env:LOCALAPPDATA "하태욱프로그램"
$Exe = Join-Path $AppDir "하태욱 프로그램.exe"

if (-not (Test-Path $Exe)) {
    Write-Host "[오류] $Exe 파일이 없습니다." -ForegroundColor Red
    pause
    exit 1
}

$Wsh = New-Object -ComObject WScript.Shell
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$sc = $Wsh.CreateShortcut((Join-Path $startMenu "하태욱 프로그램.lnk"))
$sc.TargetPath = $Exe
$sc.WorkingDirectory = $AppDir
$sc.IconLocation = "$Exe,0"
$sc.Save()

$desktop = [Environment]::GetFolderPath("Desktop")
$sc2 = $Wsh.CreateShortcut((Join-Path $desktop "하태욱 프로그램.lnk"))
$sc2.TargetPath = $Exe
$sc2.WorkingDirectory = $AppDir
$sc2.IconLocation = "$Exe,0"
$sc2.Save()

Write-Host "바로가기 수리 완료." -ForegroundColor Green
pause
