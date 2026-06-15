@echo off
chcp 65001 >nul
rem ── 하태욱 프로그램 Windows 설치 (cmd) ──
rem 빌드된 dist\하태욱 프로그램.exe를 %LOCALAPPDATA%\하태욱프로그램에 복사하고 바로가기를 만든다.

setlocal enabledelayedexpansion

set "APP_NAME=하태욱 프로그램"
set "APP_DIR_NAME=하태욱프로그램"
set "EXE_NAME=하태욱 프로그램.exe"
set "SOURCE_EXE=%~dp0dist\%EXE_NAME%"
set "INSTALL_DIR=%LOCALAPPDATA%\%APP_DIR_NAME%"
set "TARGET_EXE=%INSTALL_DIR%\%EXE_NAME%"
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\%APP_NAME%"

if not exist "%SOURCE_EXE%" (
    echo [오류] %SOURCE_EXE% 파일이 없습니다. 먼저 build.bat 또는 build.ps1로 빌드하세요.
    pause
    exit /b 1
)

echo [%APP_NAME%] 설치를 시작합니다...

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
del /q "%INSTALL_DIR%\*.exe" 2>nul
copy /y "%SOURCE_EXE%" "%TARGET_EXE%" >nul
echo 실행 파일 복사 완료: %TARGET_EXE%

if not exist "%START_MENU%" mkdir "%START_MENU%"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%START_MENU%\%APP_NAME%.lnk'); $s.TargetPath='%TARGET_EXE%'; $s.WorkingDirectory='%INSTALL_DIR%'; $s.IconLocation='%TARGET_EXE%,0'; $s.Save()" >nul
echo 시작 메뉴 바로가기 생성 완료

set /p DESKTOP_ANSWER="바탕화면 바로가기를 만드시겠습니까? (Y/n) "
if /i "%DESKTOP_ANSWER%"=="" set DESKTOP_ANSWER=Y
if /i "%DESKTOP_ANSWER%"=="y" (
    powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%USERPROFILE%\Desktop\%APP_NAME%.lnk'); $s.TargetPath='%TARGET_EXE%'; $s.WorkingDirectory='%INSTALL_DIR%'; $s.IconLocation='%TARGET_EXE%,0'; $s.Save()" >nul
    echo 바탕화면 바로가기 생성 완료
)

echo.
echo 설치가 완료되었습니다.
echo 처음 실행 시 설정창이 열리며, 시작 프로그램 등록은 설정에서 처리됩니다.

set /p RUN_ANSWER="지금 %APP_NAME%을 실행할까요? (Y/n) "
if /i "%RUN_ANSWER%"=="" set RUN_ANSWER=Y
if /i "%RUN_ANSWER%"=="y" (
    start "" "%TARGET_EXE%" --ui
)

pause
