# method_08_antivirus_safe.ps1
# 백신(Windows Defender 등)이 빌드 결과물이나 설치 파일을 지울 때 쓰는 백업.
# 소스/설치 폴더를 Defender 예외로 등록한 뒤 표준 빌드 설치를 진행한다.
# (예외 등록에는 관리자 권한이 필요하다. 권한이 없으면 안내만 하고 빌드는 그대로 시도한다.)
param([object]$Ctx, [switch]$FromMaster)
. (Join-Path $PSScriptRoot "..\common.ps1")
if (-not $Ctx) { $Ctx = Get-SetupContext }
Initialize-Logging -LogFile $Ctx.LogFile

function Invoke-Method08 {
    param([object]$Ctx)
    Write-Step "방법 8: 백신 예외 등록 후 설치"

    if (Test-IsAdmin) {
        Add-DefenderExclusion -Path $Ctx.ProjectRoot | Out-Null
        Add-DefenderExclusion -Path $Ctx.InstallDir  | Out-Null
    } else {
        Write-Warn "관리자 권한이 아니어서 백신 예외를 자동 등록하지 못합니다."
        Write-Info "차단이 계속되면 이 파일을 '관리자 권한으로 실행' 하거나,"
        Write-Info "Windows 보안 > 바이러스 위협 방지 > 제외 항목에 아래 폴더를 직접 추가하세요:"
        Write-Info "  $($Ctx.ProjectRoot)"
        Write-Info "  $($Ctx.InstallDir)"
    }

    $python = Find-Python
    if (-not $python) { Write-Warn "Python 을 찾지 못했습니다. 이 방법은 건너뜁니다."; return $false }
    if (-not (Test-Internet)) { Write-Warn "인터넷 연결이 없어 이 방법은 건너뜁니다."; return $false }

    $venvPython = New-Venv -PythonExe $python -VenvDir $Ctx.VenvDir
    $targetPython = if ($venvPython) { $venvPython } else { $python }
    $userFlag = -not $venvPython
    if (-not (Install-Packages -PythonExe $targetPython -RequirementsFile $Ctx.RequirementsFile -User:$userFlag)) {
        Write-Warn "패키지 설치 실패."; return $false
    }
    $exe = Build-Exe -PythonExe $targetPython -Ctx $Ctx
    if (-not $exe) { Write-Warn "빌드 실패."; return $false }
    if (-not (Install-ExeProgram -Ctx $Ctx -ExePath $exe)) { Write-Warn "설치 복사 실패."; return $false }
    Write-Ok "설치 완료"
    return $true
}

$ok = [bool](Invoke-Method08 -Ctx $Ctx)
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
