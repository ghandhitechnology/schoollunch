# method_06_embedded_python.ps1
# PC 에 Python 이 전혀 없고 설치도 할 수 없을 때 쓰는 백업.
# python.org 의 임베디드(무설치) Python 을 내려받아 프로그램 안에서만 사용한다.
param([object]$Ctx, [switch]$FromMaster)
. (Join-Path $PSScriptRoot "..\common.ps1")
if (-not $Ctx) { $Ctx = Get-SetupContext }
Initialize-Logging -LogFile $Ctx.LogFile

function Invoke-Method06 {
    param([object]$Ctx)
    Write-Step "방법 6: 임베디드(무설치) Python 으로 소스 실행"

    if (-not (Test-Internet)) { Write-Warn "인터넷 연결이 없어 이 방법은 건너뜁니다."; return $false }

    $ver = $Ctx.PythonVersion
    $embedZip = Join-Path $env:TEMP "python-embed-$ver.zip"
    $embedDir = Join-Path $Ctx.ProjectRoot ".embedpython"
    $url = "https://www.python.org/ftp/python/$ver/python-$ver-embed-amd64.zip"

    Write-Info "임베디드 Python 다운로드 중..."
    if (-not (Get-DownloadedFile -Url $url -OutPath $embedZip)) { Write-Warn "임베디드 Python 다운로드 실패."; return $false }

    if (Test-Path $embedDir) { Remove-Item -Recurse -Force $embedDir -ErrorAction SilentlyContinue }
    Expand-Archive -Path $embedZip -DestinationPath $embedDir -Force
    $embedPython = Join-Path $embedDir "python.exe"
    if (-not (Test-Path $embedPython)) { Write-Warn "임베디드 Python 압축 해제 실패."; return $false }

    # 임베디드 Python 은 기본적으로 import site 가 꺼져 있어 pip 가 동작하지 않는다.
    # ._pth 파일에서 'import site' 주석을 풀어준다.
    $pth = Get-ChildItem -Path $embedDir -Filter "python*._pth" | Select-Object -First 1
    if ($pth) {
        (Get-Content $pth.FullName) -replace '^#\s*import site', 'import site' |
            Set-Content $pth.FullName -Encoding ASCII
    }

    # get-pip.py 로 pip 를 설치한다.
    $getPip = Join-Path $env:TEMP "get-pip.py"
    if (-not (Get-DownloadedFile -Url "https://bootstrap.pypa.io/get-pip.py" -OutPath $getPip)) {
        Write-Warn "get-pip.py 다운로드 실패."; return $false
    }
    & $embedPython $getPip --no-warn-script-location 2>&1 | Out-Null

    if (-not (Install-Packages -PythonExe $embedPython -RequirementsFile $Ctx.RequirementsFile)) {
        Write-Warn "패키지 설치 실패."; return $false
    }
    Write-Ok "패키지 설치 완료 (임베디드)"

    if (-not (Install-SourceProgram -Ctx $Ctx -PythonExe $embedPython)) { Write-Warn "소스 설치 실패."; return $false }
    Write-Ok "임베디드 Python 으로 설치 완료"
    return $true
}

$ok = [bool](Invoke-Method06 -Ctx $Ctx)
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
