# method_10_portable.ps1
# 마지막 보루(최후의 백업). 아무것도 복사하지 않고 현재 폴더에서 그대로 실행한다.
# 소스가 있는 폴더 위치에 의존성만 갖춰 두고, 그 자리를 가리키는 런처와 바로가기만 만든다.
# Python 만 있으면 거의 항상 성공한다.
param([object]$Ctx, [switch]$FromMaster)
. (Join-Path $PSScriptRoot "..\common.ps1")
if (-not $Ctx) { $Ctx = Get-SetupContext }
Initialize-Logging -LogFile $Ctx.LogFile

function Invoke-Method10 {
    param([object]$Ctx)
    Write-Step "방법 10: 현재 폴더에서 바로 실행 (포터블)"

    $python = Find-Python
    if (-not $python) { Write-Warn "Python 을 찾지 못했습니다. 이 방법은 건너뜁니다."; return $false }
    Write-Info "Python: $python"

    # 의존성: 가능하면 현재 폴더의 venv, 안 되면 사용자 영역(--user).
    $venvPython = $null
    if (Test-Path (Join-Path $Ctx.VenvDir "Scripts\python.exe")) {
        $venvPython = Join-Path $Ctx.VenvDir "Scripts\python.exe"   # 이전 단계에서 만든 venv 재사용
    } elseif (Test-Internet) {
        $venvPython = New-Venv -PythonExe $python -VenvDir $Ctx.VenvDir
    }
    $runPython = if ($venvPython) { $venvPython } else { $python }

    if (Test-Internet) {
        $userFlag = -not $venvPython
        Install-Packages -PythonExe $runPython -RequirementsFile $Ctx.RequirementsFile -User:$userFlag | Out-Null
    } else {
        Write-Warn "인터넷이 없어 패키지 설치는 건너뜁니다. 이미 설치돼 있길 기대합니다."
    }

    # 콘솔 없는 실행기(pythonw) 우선.
    $runDir = Split-Path -Parent $runPython
    $pyw = Join-Path $runDir "pythonw.exe"
    if (-not (Test-Path $pyw)) { $pyw = $runPython }

    # 설치 폴더에 '현재 위치의 소스'를 가리키는 런처만 만든다 (복사 없음 = 포터블).
    if (-not (Test-Path $Ctx.InstallDir)) { New-Item -ItemType Directory -Path $Ctx.InstallDir -Force | Out-Null }
    $runBat = @"
@echo off
chcp 65001 >nul
cd /d "$($Ctx.ProjectRoot)"
start "" "$pyw" "$($Ctx.MainPy)" %*
"@
    Write-PlainText -Path $Ctx.InstalledRunBat -Content $runBat

    New-AppShortcuts -Ctx $Ctx -TargetPath $Ctx.InstalledRunBat
    Write-Ok "포터블 설치 완료 (소스 폴더: $($Ctx.ProjectRoot))"
    Write-Warn "이 방법은 현재 폴더를 그대로 사용합니다. 폴더를 옮기거나 지우면 실행되지 않습니다."
    return $true
}

$ok = [bool](Invoke-Method10 -Ctx $Ctx)
if (-not $FromMaster) {
    if ($ok -and (Test-Installation -Ctx $Ctx)) {
        Write-Ok "설치에 성공했습니다."
        if (Read-YesNo "지금 실행할까요?") { Start-InstalledApp -Ctx $Ctx }
    } else {
        Write-Fail "이 방법으로도 설치하지 못했습니다. Python 이 설치돼 있는지 확인하세요."
    }
    Pause-ForUser
}
$ok
