# 하태욱 프로그램 Windows 제거 스크립트
# 설치된 파일, 설정/캐시, 바로가기, 자동 실행 등록을 모두 제거한다.
#
# 실행: powershell -ExecutionPolicy Bypass -File uninstall_windows.ps1

$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "easy_setup\common.ps1")

$Ctx = Get-SetupContext

Write-Host "[$($Ctx.AppName)] 제거를 시작합니다..." -ForegroundColor Yellow

# 실행 중인 프로세스 종료
Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessName -like "*하태욱*" -or ($_.Path -and $_.Path -like "*$($Ctx.AppDirName)*") } |
    Stop-Process -Force -ErrorAction SilentlyContinue

# 제거 대상 목록 (설치 폴더, 설정/캐시, 시작 메뉴/바탕화면 바로가기와 .cmd 대체본, 옛 하위 폴더)
$startMenuFolder = Join-Path (Split-Path -Parent $Ctx.StartMenuLnk) $Ctx.AppName
$targets = @(
    $Ctx.InstallDir,
    $Ctx.DataDir,
    $Ctx.StartMenuLnk,
    [System.IO.Path]::ChangeExtension($Ctx.StartMenuLnk, ".cmd"),
    $Ctx.DesktopLnk,
    [System.IO.Path]::ChangeExtension($Ctx.DesktopLnk, ".cmd"),
    $startMenuFolder
)

foreach ($t in $targets) {
    if (Test-Path $t) {
        Remove-Item -Recurse -Force $t -ErrorAction SilentlyContinue
        Write-Host "제거: $t" -ForegroundColor Gray
    }
}

# 자동 실행 레지스트리 (autostart.py 의 VALUE_NAME 과 동일)
try {
    Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
        -Name $Ctx.AppDirName -Force -ErrorAction Stop
    Write-Host "자동 실행 등록 제거" -ForegroundColor Gray
} catch { }

# 포터블/임베디드 방식이 남긴 작업 폴더 정리
foreach ($leftover in @((Join-Path $Ctx.ProjectRoot ".venv"), (Join-Path $Ctx.ProjectRoot ".embedpython"))) {
    if (Test-Path $leftover) { Remove-Item -Recurse -Force $leftover -ErrorAction SilentlyContinue }
}

Write-Host ""
Write-Host "제거가 완료되었습니다." -ForegroundColor Green
