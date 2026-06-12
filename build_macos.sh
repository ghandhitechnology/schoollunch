#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[하태욱 프로그램] macOS .app 빌드를 시작합니다..."

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

OUTPUT_DIR="dist-macos"
WORK_DIR="build-macos"
APP_PATH="$OUTPUT_DIR/하태욱 프로그램.app"
APP_EXEC="$APP_PATH/Contents/MacOS/하태욱 프로그램"
REAL_EXEC="$APP_PATH/Contents/MacOS/하태욱 프로그램.real"

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --distpath "$OUTPUT_DIR" \
  --workpath "$WORK_DIR" \
  --windowed \
  --name "하태욱 프로그램" \
  --osx-bundle-identifier "com.hataewook.wallpaper" \
  --icon "assets/icons/app_icon.icns" \
  --add-data "assets:assets" \
  main.py

if command -v dot_clean >/dev/null 2>&1; then
  dot_clean "$APP_PATH" || true
fi
xattr -cr "$APP_PATH" || true

if [ -f "$APP_EXEC" ] && [ ! -f "$REAL_EXEC" ]; then
  mv "$APP_EXEC" "$REAL_EXEC"
  cat > "$APP_EXEC" <<'SH'
#!/bin/sh
DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec "$DIR/하태욱 프로그램.real" "$@"
SH
  chmod +x "$APP_EXEC"
fi

if [ "${CODESIGN_APP:-0}" = "1" ] && command -v codesign >/dev/null 2>&1; then
  codesign -s - --force --deep "$APP_PATH" || {
    echo "경고: ad-hoc codesign 실패. 앱은 생성됐지만 macOS 보안 설정에 따라 첫 실행 확인이 필요할 수 있습니다."
  }
fi

echo
echo "빌드 완료: $APP_PATH"
