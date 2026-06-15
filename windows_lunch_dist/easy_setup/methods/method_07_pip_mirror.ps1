# method_07_pip_mirror.ps1
# PyPI 가 느리거나 차단된 망(학교/사내망)에서 쓰는 백업.
# 국내·대체 미러를 차례로 시도해 패키지를 설치한 뒤 빌드/설치한다.
param([object]$Ctx, [switch]$FromMaster)
. (Join-Path $PSScriptRoot "..\common.ps1")
if (-not $Ctx) { $Ctx = Get-SetupContext }
Initialize-Logging -LogFile $Ctx.LogFile

function Invoke-Method07 {
    param([object]$Ctx)
    Write-Step "방법 7: 대체 미러로 패키지 설치 + 빌드"

    $python = Find-Python
    if (-not $python) { Write-Warn "Python 을 찾지 못했습니다. 이 방법은 건너뜁니다."; return $false }
    Write-Info "Python: $python"

    $venvPython = New-Venv -PythonExe $python -VenvDir $Ctx.VenvDir
    $targetPython = if ($venvPython) { $venvPython } else { $python }
    $userFlag = -not $venvPython

    $mirrors = @(
        "https://pypi.org/simple",
        "https://files.pythonhosted.org/simple",
        "https://mirror.kakao.com/pypi/simple",
        "https://pypi.tuna.tsinghua.edu.cn/simple"
    )
    $installed = $false
    foreach ($mirror in $mirrors) {
        Write-Info "미러 시도: $mirror"
        if (Install-Packages -PythonExe $targetPython -RequirementsFile $Ctx.RequirementsFile `
                -IndexUrl $mirror -User:$userFlag -MaxRetries 1) {
            $installed = $true; break
        }
    }
    if (-not $installed) { Write-Warn "모든 미러에서 패키지 설치 실패."; return $false }
    Write-Ok "패키지 설치 완료 (미러)"

    $exe = Build-Exe -PythonExe $targetPython -Ctx $Ctx
    if ($exe) {
        if (Install-ExeProgram -Ctx $Ctx -ExePath $exe) { Write-Ok "설치 완료 (빌드)"; return $true }
    }
    Write-Warn "빌드를 못 해 소스 실행 방식으로 전환합니다."
    if (Install-SourceProgram -Ctx $Ctx -PythonExe $targetPython) { Write-Ok "설치 완료 (소스)"; return $true }
    return $false
}

$ok = [bool](Invoke-Method07 -Ctx $Ctx)
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
