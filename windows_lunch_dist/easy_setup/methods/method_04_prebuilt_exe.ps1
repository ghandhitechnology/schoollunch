# method_04_prebuilt_exe.ps1
# 이미 빌드된 exe 가 있을 때 쓰는 가장 빠른 방법.
# dist\ 또는 prebuilt\ 폴더의 exe 를 그대로 설치한다. Python 이 없어도 동작한다.
param([object]$Ctx, [switch]$FromMaster)
. (Join-Path $PSScriptRoot "..\common.ps1")
if (-not $Ctx) { $Ctx = Get-SetupContext }
Initialize-Logging -LogFile $Ctx.LogFile

function Invoke-Method04 {
    param([object]$Ctx)
    Write-Step "방법 4: 미리 빌드된 exe 설치 (Python 불필요)"

    $exe = $null
    if (Test-Path $Ctx.DistExe)     { $exe = $Ctx.DistExe }
    elseif (Test-Path $Ctx.PrebuiltExe) { $exe = $Ctx.PrebuiltExe }

    if (-not $exe) {
        Write-Warn "미리 빌드된 exe 가 없습니다 (dist\ 또는 prebuilt\). 이 방법은 건너뜁니다."
        return $false
    }
    Write-Info "사용할 exe: $exe"

    if (-not (Install-ExeProgram -Ctx $Ctx -ExePath $exe)) { Write-Warn "설치 복사 실패."; return $false }
    Write-Ok "설치 완료"
    return $true
}

$ok = [bool](Invoke-Method04 -Ctx $Ctx)
if (-not $FromMaster) {
    if ($ok -and (Test-Installation -Ctx $Ctx)) {
        Write-Ok "설치에 성공했습니다."
        if (Read-YesNo "지금 실행할까요?") { Start-InstalledApp -Ctx $Ctx }
    } else {
        Write-Fail "이 방법으로는 설치하지 못했습니다. setup_all.bat 을 실행해 자동 복구를 시도하세요."
    }
    Pause-ForUser
}
$ok
