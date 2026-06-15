# method_02_user_pip_build.ps1
# 가상 환경(venv)을 만들 수 없는 PC 용 백업.
# 사용자 영역(pip --user)에 패키지를 직접 설치한 뒤 빌드/설치한다.
param([object]$Ctx, [switch]$FromMaster)
. (Join-Path $PSScriptRoot "..\common.ps1")
if (-not $Ctx) { $Ctx = Get-SetupContext }
Initialize-Logging -LogFile $Ctx.LogFile

function Invoke-Method02 {
    param([object]$Ctx)
    Write-Step "방법 2: 사용자 영역 pip 설치 + 빌드 (venv 없이)"

    $python = Find-Python
    if (-not $python) { Write-Warn "Python 을 찾지 못했습니다. 이 방법은 건너뜁니다."; return $false }
    if (-not (Test-Internet)) { Write-Warn "인터넷 연결이 없어 이 방법은 건너뜁니다."; return $false }
    Write-Info "Python: $python"

    if (-not (Install-Packages -PythonExe $python -RequirementsFile $Ctx.RequirementsFile -User)) {
        Write-Warn "사용자 영역 패키지 설치 실패."; return $false
    }
    Write-Ok "패키지 설치 완료 (사용자 영역)"

    $exe = Build-Exe -PythonExe $python -Ctx $Ctx
    if (-not $exe) { Write-Warn "빌드 실패."; return $false }
    Write-Ok "빌드 완료: $exe"

    if (-not (Install-ExeProgram -Ctx $Ctx -ExePath $exe)) { Write-Warn "설치 복사 실패."; return $false }
    Write-Ok "설치 완료"
    return $true
}

$ok = [bool](Invoke-Method02 -Ctx $Ctx)
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
