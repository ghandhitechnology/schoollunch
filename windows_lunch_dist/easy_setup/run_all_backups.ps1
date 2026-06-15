# run_all_backups.ps1
# 모든 설치 방법(10가지 methods + 40가지 backups)을 순차적으로 시도합니다.
# 하나가 성공하면 즉시 종료합니다.

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$Ctx = Get-SetupContext
Initialize-Logging -LogFile (Join-Path $Ctx.DataDir "run_all_backups.log")

Show-Banner "모든 설치 방법 순차 시도"

# 1단계: 통합 methods
$methods = @(
    "methods\method_01_venv_build.ps1",
    "methods\method_02_user_pip_build.ps1",
    "methods\method_03_source_venv.ps1",
    "methods\method_04_prebuilt_exe.ps1",
    "methods\method_05_offline_wheels.ps1",
    "methods\method_06_embedded_python.ps1",
    "methods\method_07_pip_mirror.ps1",
    "methods\method_08_antivirus_safe.ps1",
    "methods\method_09_admin_systemwide.ps1",
    "methods\method_10_portable.ps1"
)

foreach ($method in $methods) {
    $path = Join-Path $PSScriptRoot $method
    $name = Split-Path -Leaf $method
    Write-Step "시도: $name"
    try {
        $ok = & $path -Ctx $Ctx -FromMaster
        if ($ok -and (Test-Installation -Ctx $Ctx)) {
            Write-Ok "성공: $name"
            Pause-ForUser
            exit 0
        }
    } catch {
        Write-Fail "$name 예외: $_"
    }
}

# 2단계: 개별 백업 scripts (핵심 10개)
$backups = @(
    "backups\07_setup_safe_path.ps1",
    "backups\03_setup_download_python.ps1",
    "backups\12_setup_windows_store_python.ps1",
    "backups\11_setup_run_from_source.ps1",
    "backups\08_setup_prebuilt_exe.ps1",
    "backups\16_setup_clean_reinstall.ps1",
    "backups\20_setup_emergency_repair.ps1"
)

foreach ($backup in $backups) {
    $path = Join-Path $PSScriptRoot $backup
    $name = Split-Path -Leaf $backup
    Write-Step "시도: $name"
    try {
        $ext = [System.IO.Path]::GetExtension($path).ToLower()
        if ($ext -eq ".bat") {
            $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$path`"" -Wait -PassThru -NoNewWindow
            $code = $proc.ExitCode
        } else {
            $proc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$path`"" -Wait -PassThru -NoNewWindow
            $code = $proc.ExitCode
        }
        if ((Test-Installation -Ctx $Ctx) -and $code -eq 0) {
            Write-Ok "성공: $name"
            Pause-ForUser
            exit 0
        }
    } catch {
        Write-Fail "$name 예외: $_"
    }
}

Write-Fail "모든 방법이 실패했습니다."
Write-Info "로그: $($Ctx.LogFile)"
Pause-ForUser
exit 1
