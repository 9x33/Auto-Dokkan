#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"
DIST_DIR="$ROOT_DIR/dist"
APP_NAME="Auto Dokkan"
APP_DIR="$BUILD_DIR/$APP_NAME.app"
DMG_STAGING="$BUILD_DIR/dmg"
DMG_PATH="$DIST_DIR/AutoDokkan.dmg"

rm -rf "$BUILD_DIR"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources" "$DMG_STAGING" "$DIST_DIR"

cp "$ROOT_DIR/packaging/Info.plist" "$APP_DIR/Contents/Info.plist"
cp "$ROOT_DIR/packaging/auto-dokkan-launcher" "$APP_DIR/Contents/MacOS/auto-dokkan-launcher"
chmod +x "$APP_DIR/Contents/MacOS/auto-dokkan-launcher"

cp "$ROOT_DIR/dokkan_replay_watcher.py" "$APP_DIR/Contents/Resources/dokkan_replay_watcher.py"
cp "$ROOT_DIR/requirements.txt" "$APP_DIR/Contents/Resources/requirements.txt"

if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "$APP_DIR" >/dev/null 2>&1 || true
fi

cp -R "$APP_DIR" "$DMG_STAGING/$APP_NAME.app"
ln -s /Applications "$DMG_STAGING/Applications"

rm -f "$DMG_PATH"

hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$DMG_STAGING" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo "$DMG_PATH"
