param(
    [switch]$Rebuild,
    [switch]$NoDesktopShortcut,
    [switch]$NoLaunch,
    [switch]$Unattended
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location -Path $PSScriptRoot

$AppName = "하태욱 프로그램"
$BuiltExe = Join-Path $PSScriptRoot "dist\$AppName\$AppName.exe"
$LegacyExe = Join-Path $PSScriptRoot "dist\$AppName.exe"

try {
    if ($Rebuild -or (-not (Test-Path $BuiltExe) -and -not (Test-Path $LegacyExe))) {
        Write-Host "빌드 결과가 없어 먼저 앱을 빌드합니다." -ForegroundColor Cyan
        & (Join-Path $PSScriptRoot "build.ps1")
    } else {
        Write-Host "기존 빌드 결과를 사용합니다. 새로 빌드하려면 -Rebuild를 사용하세요." -ForegroundColor Gray
    }

    $InstallArgs = @{}
    if ($NoDesktopShortcut) { $InstallArgs.NoDesktopShortcut = $true }
    if ($NoLaunch) { $InstallArgs.NoLaunch = $true }
    if ($Unattended) { $InstallArgs.Unattended = $true }
    & (Join-Path $PSScriptRoot "install_windows.ps1") @InstallArgs
} catch {
    Write-Host ""
    Write-Host "[오류] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
