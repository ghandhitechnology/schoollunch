# setup_master.ps1
# 하태욱 프로그램 - Windows 절대 실패하지 않는 마스터 설치
# 10가지 설치 방법을 순차적으로 시도하여 하나가 성공하면 멈춥니다.

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$Ctx = Get-SetupContext
Initialize-Logging -LogFile $Ctx.LogFile

Show-Banner "하태욱 프로그램 Windows 설치"
Write-Info "설치 로그: $($Ctx.LogFile)"
Write-Info "Windows 버전: $([System.Environment]::OSVersion.Version)"

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
    Write-Step "방법 시도: $name"
    try {
        $ok = & $path -Ctx $Ctx -FromMaster
        if ($ok -and (Test-Installation -Ctx $Ctx)) {
            Write-Ok "설치 성공!"
            if (Read-YesNo "지금 프로그램을 실행할까요?") {
                Start-InstalledApp -Ctx $Ctx
            }
            Pause-ForUser
            exit 0
        }
    } catch {
        Write-Fail "방법 $name 처리 중 예외: $_"
    }
}

Write-Fail "모든 자동 설치 방법이 실패했습니다."
Write-Info "개별 백업 방법은 easy_setup\backups\ 폴더에 있습니다."
Write-Info "가장 강력한 최종 복구: easy_setup\backups\20_setup_emergency_repair.ps1"
Pause-ForUser
exit 1
