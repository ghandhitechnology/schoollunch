# 백업 11: 실행 파일 빌드 없이 소스 코드로 직접 실행

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

$InstallDir = Join-Path $env:LOCALAPPDATA "하태욱프로그램"
if (-not (Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null }

# 소스 복사
Copy-Item -Path "$ProjectRoot\*.py" -Destination $InstallDir -Force
if (Test-Path "$ProjectRoot\assets") { Copy-Item -Recurse -Force "$ProjectRoot\assets" "$InstallDir\assets" }
Copy-Item -Recurse -Force "$ProjectRoot\.venv" "$InstallDir\.venv"

# 실행 배치
$Launcher = Join-Path $InstallDir "run.bat"
"@echo off`nchcp 65001 >nul`ncd /d `"%~dp0`"`n`".venv\Scripts\python.exe`" main.py --ui" | Out-File -FilePath $Launcher -Encoding UTF8

# 바로가기
$Wsh = New-Object -ComObject WScript.Shell
$sc = $Wsh.CreateShortcut((Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\하태욱 프로그램.lnk"))
$sc.TargetPath = $Launcher
$sc.WorkingDirectory = $InstallDir
$sc.Save()

Write-Host "소스 실행 설치 완료. 시작 메뉴에서 실행하세요." -ForegroundColor Green
pause
