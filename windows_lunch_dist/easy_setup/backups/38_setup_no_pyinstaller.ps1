# 백업 38: PyInstaller 없이 소스 코드로 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

$InstallDir = Join-Path $env:LOCALAPPDATA "하태욱프로그램"
if (-not (Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null }
Copy-Item -Path "$ProjectRoot\*.py" -Destination $InstallDir -Force
if (Test-Path "$ProjectRoot\assets") { Copy-Item -Recurse -Force "$ProjectRoot\assets" "$InstallDir\assets" }
Copy-Item -Recurse -Force "$ProjectRoot\.venv" "$InstallDir\.venv"

$Launcher = Join-Path $InstallDir "run.bat"
"@echo off`nchcp 65001 >nul`ncd /d `"%~dp0`"`n`".venv\Scripts\python.exe`" main.py --ui" | Out-File -FilePath $Launcher -Encoding UTF8

$Wsh = New-Object -ComObject WScript.Shell
$sc = $Wsh.CreateShortcut((Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\하태욱 프로그램.lnk"))
$sc.TargetPath = $Launcher
$sc.WorkingDirectory = $InstallDir
$sc.Save()

Write-Host "PyInstaller 없이 설치 완료." -ForegroundColor Green
pause
