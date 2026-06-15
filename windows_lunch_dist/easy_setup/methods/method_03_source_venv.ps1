# method_03_source_venv.ps1
# PyInstaller 빌드가 실패하는 PC 용 백업.
# exe 를 만들지 않고, 가상 환경 + 소스(main.py)를 그대로 설치해 run.bat 으로 실행한다.
param([object]$Ctx, [switch]$FromMaster)
. (Join-Path $PSScriptRoot "..\common.ps1")
if (-not $Ctx) { $Ctx = Get-SetupContext }
Initialize-Logging -LogFile $Ctx.LogFile

function Invoke-Method03 {
    param([object]$Ctx)
    Write-Step "방법 3: 소스 + 가상 환경 실행 (빌드 없이)"

    $python = Find-Python
    if (-not $python) { Write-Warn "Python 을 찾지 못했습니다. 이 방법은 건너뜁니다."; return $false }
    if (-not (Test-Internet)) { Write-Warn "인터넷 연결이 없어 이 방법은 건너뜁니다."; return $false }
    Write-Info "Python: $python"

    $venvPython = New-Venv -PythonExe $python -VenvDir $Ctx.VenvDir
    if (-not $venvPython) { Write-Warn "가상 환경 생성 실패."; return $false }

    if (-not (Install-Packages -PythonExe $venvPython -RequirementsFile $Ctx.RequirementsFile)) {
        Write-Warn "패키지 설치 실패."; return $false
    }
    Write-Ok "패키지 설치 완료"

    if (-not (Install-SourceProgram -Ctx $Ctx -PythonExe $venvPython)) {
        Write-Warn "소스 설치 실패."; return $false
    }
    Write-Ok "소스 실행 방식으로 설치 완료"
    return $true
}

$ok = [bool](Invoke-Method03 -Ctx $Ctx)
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
