# 백업 31: 이미 설치된 exe가 있을 때 바로가기만 만듦

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
$sc = $Wsh.CreateShortcut((Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\하태욱 프로그램.lnk"))
$sc.TargetPath = $Exe
$sc.WorkingDirectory = $AppDir
$sc.IconLocation = "$Exe,0"
$sc.Save()

Write-Host "바로가기 생성 완료." -ForegroundColor Green
pause
