# method_01_venv_build.ps1
# 표준 설치: 가상 환경(.venv) → 패키지 설치 → exe 빌드 → 설치.
# 가장 깔끔한 정석 방법이며, 대부분의 PC 에서 이 방법으로 끝난다.
param([object]$Ctx, [switch]$FromMaster)
. (Join-Path $PSScriptRoot "..\common.ps1")
if (-not $Ctx) { $Ctx = Get-SetupContext }
Initialize-Logging -LogFile $Ctx.LogFile

function Invoke-Method01 {
    param([object]$Ctx)
    Write-Step "방법 1: 가상 환경 + 빌드 (표준)"

    $python = Find-Python
    if (-not $python) { Write-Warn "Python 을 찾지 못했습니다. 이 방법은 건너뜁니다."; return $false }
    if (-not (Test-Internet)) { Write-Warn "인터넷 연결이 없어 이 방법은 건너뜁니다."; return $false }
    Write-Info "Python: $python"

    $venvPython = New-Venv -PythonExe $python -VenvDir $Ctx.VenvDir
    if (-not $venvPython) { Write-Warn "가상 환경 생성 실패."; return $false }
    Write-Ok "가상 환경 준비 완료"

    if (-not (Install-Packages -PythonExe $venvPython -RequirementsFile $Ctx.RequirementsFile)) {
        Write-Warn "패키지 설치 실패."; return $false
    }
    Write-Ok "패키지 설치 완료"

    $exe = Build-Exe -PythonExe $venvPython -Ctx $Ctx
    if (-not $exe) { Write-Warn "빌드 실패."; return $false }
    Write-Ok "빌드 완료: $exe"

    if (-not (Install-ExeProgram -Ctx $Ctx -ExePath $exe)) { Write-Warn "설치 복사 실패."; return $false }
    Write-Ok "설치 완료"
    return $true
}

$ok = [bool](Invoke-Method01 -Ctx $Ctx)
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
