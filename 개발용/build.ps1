# 하태욱 프로그램 Windows 빌드
# Python 3.10+만 있으면 전용 가상환경과 의존성을 자동 준비한다.

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 스크립트 위치를 기준으로 동작한다.
Set-Location -Path $PSScriptRoot

function Resolve-Python {
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        return @{ Exe = "py"; Args = @("-3") }
    }
    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        return @{ Exe = "python"; Args = @() }
    }
    throw "Python 3.10 이상을 찾을 수 없습니다. https://www.python.org/downloads/windows/ 에서 설치하세요."
}

$Python = Resolve-Python
$PythonExe = $Python.Exe
$PythonArgs = $Python.Args
$VersionText = & $PythonExe @PythonArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or [version]$VersionText -lt [version]"3.10") {
    throw "Python 3.10 이상이 필요합니다. 감지된 버전: $VersionText"
}

$VenvDir = Join-Path $PSScriptRoot ".venv-build"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "[1/3] 빌드 전용 가상환경 생성..." -ForegroundColor Cyan
    & $PythonExe @PythonArgs -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "가상환경 생성에 실패했습니다." }
}

Write-Host "[2/3] 빌드 의존성 확인..." -ForegroundColor Cyan
& $VenvPython -m pip install --disable-pip-version-check --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "의존성 설치에 실패했습니다." }

Write-Host "[3/3] 빠른 시작용 Windows 앱 빌드..." -ForegroundColor Cyan
& $VenvPython -m PyInstaller --noconfirm --clean windows_build.spec

if ($LASTEXITCODE -ne 0) {
    throw "빌드 실패 (exit code $LASTEXITCODE)"
}

Write-Host ""
Write-Host "빌드 완료: dist\하태욱 프로그램\하태욱 프로그램.exe" -ForegroundColor Green
