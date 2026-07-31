param(
    [switch]$NoDesktopShortcut,
    [switch]$NoLaunch,
    [switch]$Unattended
)

# 사용자 권한으로 설치한다. 관리자 권한은 필요하지 않다.

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location -Path $PSScriptRoot

$AppName = "하태욱 프로그램"
$AppDirName = "하태욱프로그램"
$ExeName = "하태욱 프로그램.exe"
$SourceDir = Join-Path $PSScriptRoot "dist\$AppName"
$SourceExe = Join-Path $SourceDir $ExeName
$LegacySourceExe = Join-Path $PSScriptRoot "dist\$ExeName"
$InstallDir = Join-Path $env:LOCALAPPDATA $AppDirName
$TargetExe = Join-Path $InstallDir $ExeName
$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs" $AppName

if (-not (Test-Path $SourceExe)) {
    if (Test-Path $LegacySourceExe) {
        $SourceExe = $LegacySourceExe
        $SourceDir = $null
    } else {
        throw "빌드 결과가 없습니다. setup_windows.bat 또는 build.bat를 먼저 실행하세요."
    }
}

Write-Host "[$AppName] 설치를 시작합니다..." -ForegroundColor Green

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
if ($SourceDir) {
    # onedir 패키지는 매 실행 압축 해제가 없어 저사양 PC에서 더 빨리 시작한다.
    Copy-Item -Path (Join-Path $SourceDir "*") -Destination $InstallDir -Recurse -Force
} else {
    Copy-Item -Path $SourceExe -Destination $TargetExe -Force
}
Write-Host "앱 파일 복사 완료: $InstallDir" -ForegroundColor Gray

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

$createDesktop = -not $NoDesktopShortcut
if (-not $Unattended -and -not $NoDesktopShortcut) {
    $answer = Read-Host "바탕화면 바로가기를 만드시겠습니까? (Y/n)"
    $createDesktop = ($answer -eq "" -or $answer -match "^(y|Y|yes|YES|예)$")
}
if ($createDesktop) {
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

$runNow = -not $NoLaunch
if (-not $Unattended -and -not $NoLaunch) {
    $answer = Read-Host "지금 $AppName을 실행할까요? (Y/n)"
    $runNow = ($answer -eq "" -or $answer -match "^(y|Y|yes|YES|예)$")
}
if ($runNow) {
    Start-Process -FilePath $TargetExe -ArgumentList "--ui"
}
