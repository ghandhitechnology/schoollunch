# 하태욱 프로그램 Windows 설치 스크립트 (수동용)
# 이미 빌드된 dist\하태욱 프로그램.exe 를 설치 위치로 복사하고 바로가기를 만든다.
# 설치 로직은 easy_setup\common.ps1 한 곳에 모아 두고 여기서는 그것을 호출한다.
#
# 실행: powershell -ExecutionPolicy Bypass -File install_windows.ps1

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "easy_setup\common.ps1")

$Ctx = Get-SetupContext
Initialize-Logging -LogFile $Ctx.LogFile

if (-not (Test-Path $Ctx.DistExe)) {
    Write-Fail "$($Ctx.DistExe) 파일이 없습니다. 먼저 build.bat 또는 build.ps1 로 빌드하세요."
    Pause-ForUser
    exit 1
}

Write-Step "$($Ctx.AppName) 설치"
$desktop = Read-YesNo "바탕화면 바로가기도 만들까요?"
if (-not (Install-ExeProgram -Ctx $Ctx -ExePath $Ctx.DistExe -Desktop $desktop)) {
    Write-Fail "설치에 실패했습니다."
    Pause-ForUser
    exit 1
}

Write-Ok "설치가 완료되었습니다."
Write-Info "처음 실행하면 설정 창이 열립니다. 자동 시작 등록은 설정 창에서 처리됩니다."
if (Read-YesNo "지금 $($Ctx.AppName) 을 실행할까요?") { Start-InstalledApp -Ctx $Ctx }
