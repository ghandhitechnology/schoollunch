# 백업 15: 오래된 Windows 10용 호환 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$build = [System.Environment]::OSVersion.Version.Build
if ($build -lt 18362) {
    Write-Warning "Windows 10 1903 이상을 권장합니다. 계속하려면 아무 키나 누르세요."
    pause
}

python -m venv .venv
.\.venv\Scripts\pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
