# 백업 17: 바탕화면 바로가기만 생성

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec

$AppDir = Join-Path $env:LOCALAPPDATA "하태욱프로그램"
$Exe = Join-Path $ProjectRoot "dist\하태욱 프로그램.exe"
if (-not (Test-Path $AppDir)) { New-Item -ItemType Directory -Path $AppDir -Force | Out-Null }
Copy-Item -Path $Exe -Destination $AppDir -Force

$Wsh = New-Object -ComObject WScript.Shell
$sc = $Wsh.CreateShortcut((Join-Path $env:USERPROFILE "Desktop\하태욱 프로그램.lnk"))
$sc.TargetPath = Join-Path $AppDir "하태욱 프로그램.exe"
$sc.WorkingDirectory = $AppDir
$sc.Save()

Write-Host "바탕화면 바로가기 생성 완료." -ForegroundColor Green
pause
