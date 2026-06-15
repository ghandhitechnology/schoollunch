# easy_setup - 절대 실패하지 않는 설치 도구 모음

이 폴더는 **하태욱 프로그램**을 Windows에 설치할 때 발생할 수 있는 거의 모든 문제를 해결하기 위한 설치 도구 모음입니다.

## 주요 파일

| 파일 | 설명 |
|------|------|
| `setup_master.ps1` | 가장 강력한 통합 설치 스크립트. 10가지 방법을 자동으로 시도합니다. |
| `run_all_backups.ps1` | 통합 방법과 핵심 백업 방법을 순차적으로 실행합니다. |
| `common.ps1` | 설치 스크립트들이 공유하는 라이브러리입니다. |
| `methods/` | 10가지 통합 설치 방법이 들어 있습니다. |
| `backups/` | 40가지 상황별 백업 설치 스크립트가 들어 있습니다. |

## 빠른 사용법

1. Python 3.10 이상을 설치하고 PATH에 추가합니다.
2. 상위 폴더의 **`setup_all.bat`**을 더블 클릭합니다.
3. 안내에 따라 진행합니다.

## 통합 설치 방법

`setup_master.ps1`이 다음 10가지 방법을 순서대로 시도합니다.

1. `methods\method_01_venv_build.ps1` — 표준 가상 환경 설치
2. `methods\method_02_user_pip_build.ps1` — venv 없이 사용자 영역 설치
3. `methods\method_03_source_venv.ps1` — 소스 코드로 실행
4. `methods\method_04_prebuilt_exe.ps1` — 미리 빌드된 exe 설치
5. `methods\method_05_offline_wheels.ps1` — 오프라인 wheel 설치
6. `methods\method_06_embedded_python.ps1` — 임베디드 Python 사용
7. `methods\method_07_pip_mirror.ps1` — 대체 미러 사용
8. `methods\method_08_antivirus_safe.ps1` — 백신 예외 등록
9. `methods\method_09_admin_systemwide.ps1` — 관리자 권한 설치
10. `methods\method_10_portable.ps1` — 현재 폴더에서 바로 실행

## 백업 방법 사용법

특정 문제가 발생하면 `backups\`에서 해당 파일을 더블 클릭하세요.

예시:
- Python이 없음 → `03_setup_download_python.ps1`
- 인터넷 없음 → `02_setup_offline.ps1` (wheelhouse 준비 필요)
- 빌드 실패 → `11_setup_run_from_source.ps1`
- 기존 설치 충돌 → `16_setup_clean_reinstall.ps1`
- 모든 방법 실패 → `20_setup_emergency_repair.ps1`

## 모든 방법 한 번에 시도

```powershell
powershell -ExecutionPolicy Bypass -File run_all_backups.ps1
```

## 공유 라이브러리

`common.ps1`은 설치에 필요한 공통 함수들을 제공합니다. 다른 스크립트에서 아래처럼 사용합니다.

```powershell
. (Join-Path $PSScriptRoot "common.ps1")
$Ctx = Get-SetupContext
```

## 로그

설치 로그는 다음 위치에 저장됩니다.

```text
%APPDATA%\하태욱프로그램\setup.log
%APPDATA%\하태욱프로그램\run_all_backups.log
```
