# 백업 19: Visual C++ 런타임 확인 후 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$vcInstalled = Get-ChildItem "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" -ErrorAction SilentlyContinue
if (-not $vcInstalled) {
    Write-Warning "Visual C++ 런타임이 없을 수 있습니다. 다운로드 페이지를 엽니다."
    Start-Process "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    Read-Host "설치 후 Enter 키를 누르세요"
}

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec
powershell -ExecutionPolicy Bypass -File install_windows.ps1
pause
