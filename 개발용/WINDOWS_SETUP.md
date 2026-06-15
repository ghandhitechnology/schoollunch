# Windows 설치 및 사용 가이드

이 문서는 Windows PC에서 **하태욱 프로그램**을 빌드·설치·사용할 때 필요한 내용을 담고 있습니다.

## 준비 사항

- Windows 10(1903 이상) 또는 Windows 11 권장
- Python 3.10 이상 ([python.org](https://www.python.org/downloads/))
- pip로 의존성 설치: `pip install -r requirements.txt`

## 1. 실행 파일 빌드

### 방법 A: 명령 프롬프트(cmd)

```bat
pip install -r requirements.txt
build.bat
```

### 방법 B: PowerShell

```powershell
pip install -r requirements.txt
.\build.ps1
```

> PowerShell 실행 정책으로 막히면 다음처럼 실행하세요:
> ```powershell
> powershell -ExecutionPolicy Bypass -File build.ps1
> ```

빌드가 완료되면 `dist\하태욱 프로그램.exe`가 생성됩니다.

## 2. 설치

빌드 후 `dist` 폐기지의 실행 파일을 원하는 위치에 설치할 수 있습니다.

### PowerShell 설치 (권장)

```powershell
powershell -ExecutionPolicy Bypass -File install_windows.ps1
```

### 명령 프롬프트 설치

```bat
install_windows.bat
```

설치 스크립트는 다음 작업을 수행합니다:

- `%LOCALAPPDATA%\하태욱프로그램`에 실행 파일 복사
- 시작 메뉴에 바로가기 생성
- 선택적으로 바탕화면 바로가기 생성
- 처음 실행 시 설정창 열기

## 3. 처음 사용

1. 실행 파일을 처음 실행하면 설정창이 열립니다.
2. 본인의 반(1-1 ~ 1-4)을 선택합니다.
3. 원하는 테마와 배경 이미지를 고릅니다.
4. **설정 저장** → **배경화면 적용** 순서로 클릭하면 바탕화면이 변경됩니다.

## 4. 시작 프로그램 등록

설정창의 **시작 시 자동 실행** 체크박스를 켜면, Windows 레지스트리 `Run` 키에 등록됩니다. 부팅 직후 인터넷이 연결될 때까지 최대 5분간 기다렸다가 급식·시간표를 가져와 바탕화면을 갱신합니다.

## 5. 문제 해결

### 빌드가 안 될 때

- Python이 설치되어 있고 `python` 명령이 작동하는지 확인하세요.
- `pip install -r requirements.txt`를 다시 실행해 의존성을 최신으로 맞추세요.
- 폐기지 경로에 한글이 포함되어 있어도 `.spec` 빌드를 사용하면 정상적으로 빌드됩니다.

### 실행 파일이 켜지지 않을 때

- `%APPDATA%\하태욱프로그램\log.txt` 파일을 확인하세요.
- 백신/보안 프로그램이 실행 파일을 차단하지 않는지 확인하세요.
- 한글 경로에 압축을 풀어 실행한 경우, 영문 경로로 옮겨 보세요.

### 바탕화면이 바뀌지 않을 때

- Windows가 **슬라이드 쇼** 또는 **Spotlight** 모드로 설정되어 있으면 단일 이미지 적용이 덮어쓰이지 않을 수 있습니다. 개인 설정 → 배경에서 **사진** 모드로 바꿔 보세요.
- Windows 11 22H2 이상에서는 설정 앱의 "개인 설정 > 배경" 메뉴가 열린 상태일 때 외부 프로그램이 배경을 바꾸지 못할 수 있습니다. 설정 창을 닫고 다시 시도하세요.
- 노트북에서 외부 모니터를 연결/분리한 직후에는 Windows가 배경을 재동기화하는 시간이 필요할 수 있습니다.

### 급식/시간표가 안 불러와질 때

- 인터넷 연결 상태를 확인하세요.
- 학교 홈페이지나 NEIS 서버가 점검 중이면 캐시 데이터를 보여줍니다.
- `log.txt`에 `"인터넷 연결 대기 중"` 메시지가 반복되면 방화벽/프록시 설정을 확인하세요.

### UI 글씨가 흐릿하게 보일 때

- `.exe` 속성 → 호환성 → **높은 DPI 설정 변경** → **높은 DPI 조정 동작을 재정의**를 끄세요.
- 빌드에 포함된 `windows_manifest.xml`이 자동으로 DPI 인식을 선언하므로, 별도의 호환성 설정은 필요 없습니다.

### 수동 제거

```powershell
# 실행 파일과 데이터 제거
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\하태욱프로그램"
Remove-Item -Recurse -Force "$env:APPDATA\하태욱프로그램"
Remove-Item -Recurse -Force "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\하태욱 프로그램"
# 자동 실행 레지스트리 제거
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "하태욱프로그램" /f
```

## 6. 개발 모드로 실행

소스 코드로 직접 실행하려면:

```bat
python main.py --ui
```

또는:

```bat
python main.py --once
```

`--ui`는 설정창만 열고, `--once`는 한 번 갱신한 뒤 종료합니다.
