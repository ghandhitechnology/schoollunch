# 백업 30: 설치 위치를 다른 드라이브로 이동

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec

$target = Read-Host "설치할 드라이브나 경로를 입력하세요 (예: D:\Apps)"
if ([string]::IsNullOrWhiteSpace($target)) { $target = "D:\Apps" }

$AppDir = Join-Path $target "하태욱프로그램"
if (-not (Test-Path $AppDir)) { New-Item -ItemType Directory -Path $AppDir -Force | Out-Null }
Copy-Item -Path "$ProjectRoot\dist\하태욱 프로그램.exe" -Destination $AppDir -Force

$Wsh = New-Object -ComObject WScript.Shell
$sc = $Wsh.CreateShortcut((Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\하태욱 프로그램.lnk"))
$sc.TargetPath = Join-Path $AppDir "하태욱 프로그램.exe"
$sc.WorkingDirectory = $AppDir
$sc.Save()

Write-Host "설치 위치 이동 완료: $AppDir" -ForegroundColor Green
pause
