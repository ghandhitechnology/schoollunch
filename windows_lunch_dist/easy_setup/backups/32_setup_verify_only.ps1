# 백업 32: 설치 상태만 검증

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$AppDir = Join-Path $env:LOCALAPPDATA "하태욱프로그램"
$Exe = Join-Path $AppDir "하태욱 프로그램.exe"
$Shortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\하태욱 프로그램.lnk"

$ok = $true
if (-not (Test-Path $Exe)) { Write-Host "[X] 실행 파일 없음: $Exe" -ForegroundColor Red; $ok = $false }
else { Write-Host "[OK] 실행 파일 존재" -ForegroundColor Green }

if (-not (Test-Path $Shortcut)) { Write-Host "[X] 시작 메뉴 바로가기 없음" -ForegroundColor Red; $ok = $false }
else { Write-Host "[OK] 시작 메뉴 바로가기 존재" -ForegroundColor Green }

if ($ok) {
    Write-Host "설치가 정상입니다." -ForegroundColor Green
} else {
    Write-Host "설치에 문제가 있습니다. run_all_backups.ps1을 실행해 보세요." -ForegroundColor Yellow
}
pause
