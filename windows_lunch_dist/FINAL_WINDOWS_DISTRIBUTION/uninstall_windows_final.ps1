$ErrorActionPreference = "Continue"
$OutputEncoding = [System.Text.Encoding]::UTF8
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$appName = "하태욱 프로그램"
$appDirName = "하태욱프로그램"
$installDir = Join-Path $env:LOCALAPPDATA $appDirName
$dataDir = Join-Path $env:APPDATA $appDirName
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$desktop = [Environment]::GetFolderPath("Desktop")

Write-Host "[$appName] 제거를 시작합니다..." -ForegroundColor Yellow

Get-Process -ErrorAction SilentlyContinue |
    Where-Object {
        ($_.ProcessName -like "*하태욱*") -or
        ($_.Path -and $_.Path -like "*$appDirName*")
    } |
    Stop-Process -Force -ErrorAction SilentlyContinue

try {
    Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
        -Name $appDirName -Force -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $appDirName -Confirm:$false -ErrorAction SilentlyContinue
} catch { }

$targets = @(
    $installDir,
    $dataDir,
    (Join-Path $startMenu "$appName.lnk"),
    (Join-Path $startMenu "$appName.cmd"),
    (Join-Path $desktop "$appName.lnk"),
    (Join-Path $desktop "$appName.cmd")
)

foreach ($target in $targets) {
    if (Test-Path $target) {
        Remove-Item -Recurse -Force $target -ErrorAction SilentlyContinue
        Write-Host "제거: $target" -ForegroundColor Gray
    }
}

Write-Host "제거 완료" -ForegroundColor Green
