# 하태욱 프로그램 Windows 제거 스크립트
# 설치된 파일, 설정/캐시, 시작 프로그램 등록을 모두 제거한다.
#
# 실행: powershell -ExecutionPolicy Bypass -File uninstall_windows.ps1

$ErrorActionPreference = "Stop"

$AppName = "하태욱 프로그램"
$AppDirName = "하태욱프로그램"
$RegValueName = "하태욱프로그램"

$InstallDir = Join-Path $env:LOCALAPPDATA $AppDirName
$DataDir = Join-Path $env:APPDATA $AppDirName
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs" $AppName
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "$AppName.lnk"

Write-Host "[$AppName] 제거를 시작합니다..." -ForegroundColor Yellow

# 실행 중인 프로세스 종료
Get-Process | Where-Object { $_.ProcessName -like "*하태욱*" -or $_.Path -like "*$InstallDir*" } | Stop-Process -Force -ErrorAction SilentlyContinue

# 설치 폐기지
if (Test-Path $InstallDir) {
    Remove-Item -Recurse -Force $InstallDir
    Write-Host "설치 폐기지 제거: $InstallDir" -ForegroundColor Gray
}

# 설정/캐시
if (Test-Path $DataDir) {
    Remove-Item -Recurse -Force $DataDir
    Write-Host "설정/캐시 제거: $DataDir" -ForegroundColor Gray
}

# 시작 메뉴 바로가기
if (Test-Path $StartMenuDir) {
    Remove-Item -Recurse -Force $StartMenuDir
    Write-Host "시작 메뉴 바로가기 제거" -ForegroundColor Gray
}

# 바탕화면 바로가기
if (Test-Path $DesktopShortcut) {
    Remove-Item -Force $DesktopShortcut
    Write-Host "바탕화면 바로가기 제거" -ForegroundColor Gray
}

# 자동 실행 레지스트리
$RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
try {
    Remove-ItemProperty -Path $RegPath -Name $RegValueName -Force -ErrorAction Stop
    Write-Host "시작 프로그램 등록 제거" -ForegroundColor Gray
} catch {
    # 등록되어 있지 않으면 무시
}

Write-Host ""
Write-Host "제거가 완료되었습니다." -ForegroundColor Green
