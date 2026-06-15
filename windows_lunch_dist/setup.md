# 하태욱 프로그램 Windows 설치 가이드

Windows에서 **하태욱 프로그램**을 설치하는 방법을 설명합니다.

이 폴더에는 다음이 포함되어 있습니다.

- **10가지 통합 설치 방법** (`easy_setup\methods\`) — 마스터 설치가 순차적으로 시도
- **40가지 개별 백업 방법** (`easy_setup\backups\`) — 특정 문제별 수동 실행
- **1개의 마스터 설치 스크립트** (`easy_setup\setup_master.ps1`)
- **1개의 전체 백업 순차 실행 스크립트** (`easy_setup\run_all_backups.ps1`)

---

## 준비 사항

- Windows 10 (1903 이상) 또는 Windows 11
- Python 3.10 이상 ([python.org](https://www.python.org/downloads/))
- 인터넷 연결 (패키지 다운로드 및 급식/시간표 데이터 갱신용)

---

## 가장 쉬운 방법 (추천)

### 1. Python 설치

1. https://www.python.org/downloads/ 에 접속합니다.
2. Python **3.10 이상**을 다운로드합니다.
3. 설치 중 **"Add python.exe to PATH"** 옵션을 꼭 체크합니다.
4. **Install Now**를 클릭합니다.

### 2. 프로그램 폴더 준비

`windows_lunch_dist` 폴더를 Windows PC의 적당한 위치에 압축 해제합니다.  
가능하면 경로에 공백이나 특수 문자가 없는 위치를 사용하세요. 예:

```text
C:\schoollunch\
```

### 3. 설치 실행

**`setup_all.bat`** 파일을 **더블 클릭**합니다.

이 파일은 다음을 자동으로 수행합니다.

1. Python 설치 여부 확인
2. 가상 환경 생성
3. 필요한 패키지 설치
4. 실행 파일(`하태욱 프로그램.exe`) 빌드
5. `%LOCALAPPDATA%\하태욱프로그램`에 설치
6. 시작 메뉴 바로가기 생성
7. 설치 완료 메시지 표시

설치 중 문제가 생기면 창이 닫히지 않고 오류 메시지를 보여줍니다.

---

## 다른 설치 방법

### PowerShell에서 직접 실행

```powershell
powershell -ExecutionPolicy Bypass -File easy_setup\setup_master.ps1
```

### 모든 백업 방법 순차 시도

```powershell
powershell -ExecutionPolicy Bypass -File easy_setup\run_all_backups.ps1
```

이 스크립트는 10가지 통합 방법과 핵심 백업 방법을 하나씩 시도하여 성공하면 멈춥니다.

---

## 10가지 통합 설치 방법

`easy_setup\methods\` 폴더에 있으며, `setup_master.ps1`이 순서대로 시도합니다.

| 번호 | 파일 | 용도 |
|------|------|------|
| 01 | `method_01_venv_build.ps1` | 표준: 가상 환경 → 패키지 → 빌드 → 설치 |
| 02 | `method_02_user_pip_build.ps1` | venv 없이 사용자 영역에 설치 |
| 03 | `method_03_source_venv.ps1` | 빌드 실패 시 소스 코드로 실행 |
| 04 | `method_04_prebuilt_exe.ps1` | 이미 빌드된 exe만 설치 |
| 05 | `method_05_offline_wheels.ps1` | 인터넷 없이 wheels 폴더 사용 |
| 06 | `method_06_embedded_python.ps1` | Python 없을 때 임베디드 Python 사용 |
| 07 | `method_07_pip_mirror.ps1` | 대체 미러로 패키지 설치 |
| 08 | `method_08_antivirus_safe.ps1` | 백신 예외 등록 후 설치 |
| 09 | `method_09_admin_systemwide.ps1` | 관리자 권한으로 시스템 전체 설치 |
| 10 | `method_10_portable.ps1` | 현재 폴더에서 바로 실행 |

---

## 40가지 개별 백업 방법

`easy_setup\backups\` 폴더에 있으며, 특정 상황에서 직접 실행할 수 있습니다.

| 번호 | 파일 | 용도 |
|------|------|------|
| 01 | `01_setup_with_existing_python.bat` | Python이 PATH에 있을 때 |
| 02 | `02_setup_offline.ps1` | 인터넷 없이 미리 받은 패키지 사용 |
| 03 | `03_setup_download_python.ps1` | Python이 없을 때 자동 설치 |
| 04 | `04_setup_user_only.ps1` | 관리자 권한 없이 설치 |
| 05 | `05_setup_antivirus_safe.bat` | 백신 차단 문제 해결 |
| 06 | `06_setup_cmd_only.bat` | PowerShell 없이 cmd만 사용 |
| 07 | `07_setup_safe_path.ps1` | 경로에 공백/한글이 있을 때 |
| 08 | `08_setup_prebuilt_exe.ps1` | 이미 빌드된 exe만 설치 |
| 09 | `09_setup_system_pip.ps1` | 가상 환경 생성 실패 시 |
| 10 | `10_setup_manual_packages.bat` | 패키지를 수동으로 다운로드 |
| 11 | `11_setup_run_from_source.ps1` | 실행 파일 빌드 없이 소스 실행 |
| 12 | `12_setup_windows_store_python.ps1` | Windows Store Python 문제 |
| 13 | `13_setup_portable_usb.ps1` | USB 등 이동식 폴더에 설치 |
| 14 | `14_setup_proxy.ps1` | 프록시 환경에서 설치 |
| 15 | `15_setup_old_windows.ps1` | 오래된 Windows 10용 |
| 16 | `16_setup_clean_reinstall.ps1` | 기존 설치 제거 후 재설치 |
| 17 | `17_setup_desktop_only.ps1` | 바탕화면 바로가기만 생성 |
| 18 | `18_setup_task_scheduler.ps1` | 작업 예약으로 자동 시작 |
| 19 | `19_setup_runtime_check.ps1` | VC++ 런타임 확인 후 설치 |
| 20 | `20_setup_emergency_repair.ps1` | 모든 방법을 순차 시도 |
| 21 | `21_setup_no_venv.ps1` | 가상 환경 없이 설치 |
| 22 | `22_setup_python_from_store.ps1` | Microsoft Store Python 사용 |
| 23 | `23_setup_admin_required.bat` | 관리자 권한으로 실행 |
| 24 | `24_setup_silent_no_prompt.ps1` | 사용자 확인 없이 자동 설치 |
| 25 | `25_setup_repair_shortcuts.ps1` | 바로가기만 수리 |
| 26 | `26_setup_reinstall_keep_settings.ps1` | 설정 유지하며 재설치 |
| 27 | `27_setup_no_internet_prebuilt.ps1` | 오프라인으로 미리 빌드된 exe 설치 |
| 28 | `28_setup_network_proxy_manual.ps1` | 수동 프록시 입력 |
| 29 | `29_setup_corrupted_venv.ps1` | 손상된 가상 환경 제거 후 재설치 |
| 30 | `30_setup_move_install_location.ps1` | 설치 위치 변경 |
| 31 | `31_setup_create_only_shortcut.ps1` | 이미 설치된 exe에 바로가기만 |
| 32 | `32_setup_verify_only.ps1` | 설치 상태만 검증 |
| 33 | `33_setup_uninstall_only.ps1` | 완전 제거 |
| 34 | `34_setup_autostart_only.ps1` | 자동 시작만 등록 |
| 35 | `35_setup_build_only.ps1` | 빌드만 수행 |
| 36 | `36_setup_install_only.ps1` | 빌드된 파일 설치만 |
| 37 | `37_setup_python310_compat.ps1` | Python 3.10 호환 설치 |
| 38 | `38_setup_no_pyinstaller.ps1` | PyInstaller 없이 설치 |
| 39 | `39_setup_oneclick_repair.bat` | 원클릭 복구 |
| 40 | `40_setup_final_resort_run.bat` | 최후의 수단으로 소스 직접 실행 |

---

## 처음 실행

1. 설치 후 프로그램을 처음 실행하면 설정창이 열립니다.
2. 본인의 반(1-1 ~ 1-4)을 선택합니다.
3. 원하는 테마와 배경 이미지를 고릅니다.
4. **설정 저장** → **배경화면 적용** 순서로 클릭합니다.

---

## 시작 프로그램 등록

설정창의 **시작 시 자동 실행** 체크박스를 켜면, Windows 부팅 시 프로그램이 자동으로 실행됩니다.

---

## 문제 해결

### 설치 파일을 더블 클릭핏 때 아무 일도 일어나지 않음

- Python이 설치되어 있는지 확인하세요.
- 폴더 경로에 공백이나 특수 문자가 있으면 `C:\schoollunch\`로 옮겨 보세요.
- `easy_setup\backups\07_setup_safe_path.ps1`을 실행해 보세요.

### Python을 찾을 수 없다는 오류

- `easy_setup\backups\03_setup_download_python.ps1`을 실행하면 Python을 자동으로 설치합니다.
- 또는 https://www.python.org/downloads/ 에서 수동으로 설치하세요.

### 빌드가 안 될 때

- `easy_setup\methods\method_03_source_venv.ps1`을 사용하여 실행 파일 없이 소스로 실행할 수 있습니다.
- `easy_setup\backups\08_setup_prebuilt_exe.ps1`은 미리 빌드된 exe를 설치합니다.

### 인터넷이 안 될 때

- 인터넷 연결된 PC에서 `pip download -r requirements.txt -d wheels`를 실행하여 패키지를 받아오세요.
- 그 후 `easy_setup\methods\method_05_offline_wheels.ps1`을 실행합니다.

### 백신/보안 프로그램이 차단함

- `easy_setup\methods\method_08_antivirus_safe.ps1`을 관리자 권한으로 실행해 보세요.
- 수동으로 설치 폴더를 백신 예외 목록에 추가하세요.

### 바탕화면이 바뀌지 않음

- Windows 배경 설정이 **사진** 모드인지 확인하세요.
- Windows 설정 앱의 "개인 설정 > 배경" 창을 닫고 다시 시도하세요.

---

## 제거 방법

### 일반 제거

`uninstall_windows.bat`을 더블 클릭하세요.

### 완전 제거

```powershell
powershell -ExecutionPolicy Bypass -File easy_setup\backups\33_setup_uninstall_only.ps1
```

---

## 파일 구조

```text
windows_lunch_dist/
├── setup_all.bat          # 가장 쉬운 설치 (더블 클릭)
├── setup.md                       # 이 문서
├── setup_all.bat / setup_all.ps1  # 기존 설치 스크립트
├── install_windows.*              # 설치 스크립트
├── build.*                        # 빌드 스크립트
├── requirements.txt               # Python 패키지 목록
├── windows_build.spec             # PyInstaller 설정
└── easy_setup/
    ├── setup_master.ps1           # 통합 마스터 설치
    ├── run_all_backups.ps1        # 모든 방법 순차 실행
    ├── common.ps1                 # 공유 라이브러리
    ├── README.md                  # easy_setup 안내
    ├── methods/                   # 10가지 통합 설치 방법
    │   ├── method_01_venv_build.ps1
    │   ├── ...
    │   └── method_10_portable.ps1
    └── backups/                   # 40가지 개별 백업 스크립트
        ├── 01_setup_with_existing_python.bat
        ├── ...
        └── 40_setup_final_resort_run.bat
```

---

## 지원

설치 로그는 다음 위치에 저장됩니다.

```text
%APPDATA%\하태욱프로그램\setup.log
%APPDATA%\하태욱프로그램\run_all_backups.log
```

문제가 지속되면 `easy_setup\run_all_backups.ps1` 또는 `easy_setup\backups\20_setup_emergency_repair.ps1`을 실행해 보세요.
