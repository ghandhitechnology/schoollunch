# method_05_offline_wheels.ps1
# 인터넷이 막힌 PC 용 백업.
# 함께 동봉된 wheels\ 폴더의 미리 받은 패키지로 오프라인 설치한다.
# (wheels 폴더가 없으면 건너뛴다. 미리 'pip download -r requirements.txt -d wheels' 로 준비)
param([object]$Ctx, [switch]$FromMaster)
. (Join-Path $PSScriptRoot "..\common.ps1")
if (-not $Ctx) { $Ctx = Get-SetupContext }
Initialize-Logging -LogFile $Ctx.LogFile

function Invoke-Method05 {
    param([object]$Ctx)
    Write-Step "방법 5: 오프라인 wheel 설치 (인터넷 불필요)"

    if (-not (Test-Path $Ctx.WheelsDir) -or
        -not (Get-ChildItem -Path $Ctx.WheelsDir -Filter *.whl -ErrorAction SilentlyContinue)) {
        Write-Warn "wheels\ 폴더에 패키지가 없어 이 방법은 건너뜁니다."
        return $false
    }

    $python = Find-Python
    if (-not $python) { Write-Warn "Python 을 찾지 못했습니다. 이 방법은 건너뜁니다."; return $false }
    Write-Info "Python: $python"

    # 가능하면 가상 환경, 안 되면 사용자 영역으로 설치한다.
    $venvPython = New-Venv -PythonExe $python -VenvDir $Ctx.VenvDir
    $targetPython = if ($venvPython) { $venvPython } else { $python }
    $userFlag = -not $venvPython

    $installed = Install-Packages -PythonExe $targetPython -RequirementsFile $Ctx.RequirementsFile `
        -Offline -FindLinks $Ctx.WheelsDir -User:$userFlag
    if (-not $installed) { Write-Warn "오프라인 패키지 설치 실패."; return $false }
    Write-Ok "오프라인 패키지 설치 완료"

    # PyInstaller 도 오프라인이면 못 받을 수 있으니, 빌드 시도 후 안 되면 소스 실행으로 전환.
    $exe = Build-Exe -PythonExe $targetPython -Ctx $Ctx
    if ($exe) {
        if (Install-ExeProgram -Ctx $Ctx -ExePath $exe) { Write-Ok "설치 완료 (빌드)"; return $true }
    }
    Write-Warn "빌드를 못 해 소스 실행 방식으로 전환합니다."
    if (Install-SourceProgram -Ctx $Ctx -PythonExe $targetPython) { Write-Ok "설치 완료 (소스)"; return $true }
    return $false
}

$ok = [bool](Invoke-Method05 -Ctx $Ctx)
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
