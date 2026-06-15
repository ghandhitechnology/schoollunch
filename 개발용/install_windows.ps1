# 하태욱 프로그램 Windows 설치 스크립트
# 빌드된 dist\하태욱 프로그램.exe를 사용자 폐기지로 복사하고 바로가기를 만든다.
#
# 실행: powershell -ExecutionPolicy Bypass -File install_windows.ps1

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location -Path $PSScriptRoot

$AppName = "하태욱 프로그램"
$AppDirName = "하태욱프로그램"
$ExeName = "하태욱 프로그램.exe"
$SourceExe = Join-Path $PSScriptRoot "dist" $ExeName
$InstallDir = Join-Path $env:LOCALAPPDATA $AppDirName
$TargetExe = Join-Path $InstallDir $ExeName
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs" $AppName

function Test-Admin {
    $current = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($current)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Path $SourceExe)) {
    Write-Host "[오류] $SourceExe 파일이 없습니다. 먼저 build.bat 또는 build.ps1로 빌드하세요." -ForegroundColor Red
    exit 1
}

Write-Host "[$AppName] 설치를 시작합니다..." -ForegroundColor Green

# 설치 폐기지 준비
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# 기존 파일 정리
Get-ChildItem -Path $InstallDir -Filter "*.exe" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Copy-Item -Path $SourceExe -Destination $TargetExe -Force
Write-Host "실행 파일 복사 완료: $TargetExe" -ForegroundColor Gray

# 시작 메뉴 바로가기
if (-not (Test-Path $StartMenuDir)) {
    New-Item -ItemType Directory -Path $StartMenuDir -Force | Out-Null
}

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut((Join-Path $StartMenuDir "$AppName.lnk"))
$Shortcut.TargetPath = $TargetExe
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = "$TargetExe,0"
$Shortcut.Save()
Write-Host "시작 메뉴 바로가기 생성 완료" -ForegroundColor Gray

# 바탕화면 바로가기 선택
$createDesktop = Read-Host "바탕화면 바로가기를 만드시겠습니까? (Y/n)"
if ($createDesktop -eq "" -or $createDesktop -match "^(y|Y|yes|YES|예)$") {
    $DesktopDir = [Environment]::GetFolderPath("Desktop")
    $DesktopShortcut = $WshShell.CreateShortcut((Join-Path $DesktopDir "$AppName.lnk"))
    $DesktopShortcut.TargetPath = $TargetExe
    $DesktopShortcut.WorkingDirectory = $InstallDir
    $DesktopShortcut.IconLocation = "$TargetExe,0"
    $DesktopShortcut.Save()
    Write-Host "바탕화면 바로가기 생성 완료" -ForegroundColor Gray
}

Write-Host ""
Write-Host "설치가 완료되었습니다." -ForegroundColor Green
Write-Host "처음 실행 시 설정창이 열리며, 시작 프로그램 등록은 설정에서 처리됩니다." -ForegroundColor Gray

$runNow = Read-Host "지금 $AppName을 실행할까요? (Y/n)"
if ($runNow -eq "" -or $runNow -match "^(y|Y|yes|YES|예)$") {
    Start-Process -FilePath $TargetExe -ArgumentList "--ui"
}
