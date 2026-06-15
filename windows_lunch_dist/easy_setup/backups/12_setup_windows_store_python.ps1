# 백업 12: Windows Store Python 문제 해결

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

# Windows Store 실행 별명 끄기
$aliasPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\Python.exe"
if (Test-Path $aliasPath) { Remove-Item -Path $aliasPath -Recurse -Force -ErrorAction SilentlyContinue }

# python.org Python 설치
$url = "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
$installer = "$env:TEMP\python-3.12.4-amd64.exe"
Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
Start-Process -FilePath $installer -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User")

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
