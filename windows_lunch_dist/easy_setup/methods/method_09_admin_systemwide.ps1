# method_09_admin_systemwide.ps1
# 일반 사용자 권한으로는 Python 설치/빌드가 막히는 PC 용 백업.
# 관리자 권한으로 승격해 Python 을 시스템 전체(All Users)에 설치한 뒤 빌드/설치한다.
param([object]$Ctx, [switch]$FromMaster)
. (Join-Path $PSScriptRoot "..\common.ps1")
if (-not $Ctx) { $Ctx = Get-SetupContext }
Initialize-Logging -LogFile $Ctx.LogFile

function Invoke-Method09 {
    param([object]$Ctx)
    Write-Step "방법 9: 관리자 권한으로 시스템 전체 설치"

    if (-not (Test-IsAdmin)) {
        Write-Info "관리자 권한이 필요합니다. 권한 상승 창에서 '예'를 눌러 주세요..."
        try {
            Start-Process -FilePath "powershell" -Verb RunAs -Wait `
                -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`"", "-FromMaster")
        } catch {
            Write-Warn "관리자 권한 승격이 취소되었습니다. 이 방법은 건너뜁니다."
            return $false
        }
        # 승격된 인스턴스가 설치를 끝냈는지 확인한다.
        return (Test-Installation -Ctx $Ctx)
    }

    # ── 여기부터는 관리자 권한으로 동작 ──
    $python = Find-Python
    if (-not $python) {
        if (-not (Test-Internet)) { Write-Warn "Python 도 없고 인터넷도 없어 건너뜁니다."; return $false }
        Write-Info "Python 을 시스템 전체에 설치합니다..."
        $ver = $Ctx.PythonVersion
        $installer = Join-Path $env:TEMP "python-$ver-amd64.exe"
        $url = "https://www.python.org/ftp/python/$ver/python-$ver-amd64.exe"
        if (-not (Get-DownloadedFile -Url $url -OutPath $installer)) { Write-Warn "Python 다운로드 실패."; return $false }
        Start-Process -FilePath $installer -Wait `
            -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1 Include_test=0"
        $python = Find-Python
        if (-not $python) { Write-Warn "Python 설치 후에도 찾지 못했습니다."; return $false }
    }
    Write-Info "Python: $python"

    $venvPython = New-Venv -PythonExe $python -VenvDir $Ctx.VenvDir
    $targetPython = if ($venvPython) { $venvPython } else { $python }
    if (-not (Install-Packages -PythonExe $targetPython -RequirementsFile $Ctx.RequirementsFile)) {
        Write-Warn "패키지 설치 실패."; return $false
    }
    $exe = Build-Exe -PythonExe $targetPython -Ctx $Ctx
    if (-not $exe) { Write-Warn "빌드 실패."; return $false }
    if (-not (Install-ExeProgram -Ctx $Ctx -ExePath $exe)) { Write-Warn "설치 복사 실패."; return $false }
    Write-Ok "설치 완료"
    return $true
}

$ok = [bool](Invoke-Method09 -Ctx $Ctx)
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
