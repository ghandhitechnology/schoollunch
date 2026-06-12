@echo off
chcp 65001 >nul
rem ── 하태욱 프로그램.exe 빌드 (Windows에서 실행) ──
rem 사전 준비: python 3.10+ 설치 후 pip install -r requirements.txt

pyinstaller --onefile --noconsole ^
  --name "하태욱 프로그램" ^
  --icon "assets\icons\app_icon.ico" ^
  --add-data "assets;assets" ^
  main.py

echo.
echo 빌드 완료: dist\하태욱 프로그램.exe
pause
