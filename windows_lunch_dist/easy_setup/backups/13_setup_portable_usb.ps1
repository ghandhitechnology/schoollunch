# 백업 13: USB 등 휴용 폴더에 설치

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$SourceRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Target = Read-Host "휴용 설치할 경로를 입력하세요 (예: D:\schoollunch)"
if ([string]::IsNullOrWhiteSpace($Target)) { $Target = "D:\schoollunch" }

if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }
Copy-Item -Recurse -Force $SourceRoot $Target
Set-Location $Target

python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean windows_build.spec

Write-Host "휴대용 설치 완료: $Target" -ForegroundColor Green
Write-Host "이 폴더를 다른 PC로 복사하면 바로 사용할 수 있습니다." -ForegroundColor Cyan
pause
