# 백업 20: 최종 응급 복구 - 모든 방법을 순차 시도

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

function Try-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "시도: $Name" -ForegroundColor Cyan
    try {
        & $Action
        $installDir = Join-Path $env:LOCALAPPDATA "하태욱프로그램"
        if (Test-Path $installDir) {
            Write-Host "성공: $Name" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "실패: $Name - $_" -ForegroundColor Yellow
    }
    return $false
}

# 1. 일반 설치
if (Try-Step "일반 설치" { & powershell -ExecutionPolicy Bypass -File setup_all.ps1 }) { pause; exit 0 }

# 2. 안전 경로
if (Try-Step "안전 경로" { & powershell -ExecutionPolicy Bypass -File easy_setup\backups\07_setup_safe_path.ps1 }) { pause; exit 0 }

# 3. 소스 실행
if (Try-Step "소스 실행" { & powershell -ExecutionPolicy Bypass -File easy_setup\backups\11_setup_run_from_source.ps1 }) { pause; exit 0 }

# 4. 미리 빌드된 exe
if (Try-Step "미리 빌드된 exe" { & powershell -ExecutionPolicy Bypass -File easy_setup\backups\08_setup_prebuilt_exe.ps1 }) { pause; exit 0 }

Write-Host "[오류] 모든 복구 방법이 실패했습니다." -ForegroundColor Red
pause
exit 1
