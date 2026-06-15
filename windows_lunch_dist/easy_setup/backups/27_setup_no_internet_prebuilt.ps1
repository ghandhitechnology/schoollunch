# 백업 27: 인터넷 없이 미리 빌드된 exe만 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$Exe = Join-Path $ProjectRoot "dist\하태욱 프로그램.exe"
if (-not (Test-Path $Exe)) {
    Write-Host "[오류] dist\하태욱 프로그램.exe 파일이 없습니다." -ForegroundColor Red
    Write-Host "인터넷이 연결된 PC에서 미리 빌드하여 이 폴더에 복사해 주세요." -ForegroundColor Yellow
    pause
    exit 1
}

$AppDir = Join-Path $env:LOCALAPPDATA "하태욱프로그램"
if (-not (Test-Path $AppDir)) { New-Item -ItemType Directory -Path $AppDir -Force | Out-Null }
Copy-Item -Path $Exe -Destination $AppDir -Force

$Wsh = New-Object -ComObject WScript.Shell
$sc = $Wsh.CreateShortcut((Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\하태욱 프로그램.lnk"))
$sc.TargetPath = Join-Path $AppDir "하태욱 프로그램.exe"
$sc.WorkingDirectory = $AppDir
$sc.IconLocation = (Join-Path $AppDir "하태욱 프로그램.exe") + ",0"
$sc.Save()

Write-Host "오프라인 설치 완료." -ForegroundColor Green
pause
