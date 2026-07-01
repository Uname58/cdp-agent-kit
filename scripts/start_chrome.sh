#!/usr/bin/env bash
# cdp-agent-kit — WSL Chrome launcher
# Opens Windows Chrome with CDP enabled, accessible from WSL.
# Usage: ./scripts/start_chrome.sh

CHROME="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
USER_DIR="$HOME/.cdp-chrome"

mkdir -p "$USER_DIR"

echo "Launching Chrome via WSL interop..."
echo "CDP → http://localhost:9222"
echo ""

# Translate WSL path to Windows path
WIN_USER_DIR=$(wslpath -w "$USER_DIR")

powershell.exe -Command "Start-Process '${CHROME}' -ArgumentList '--remote-debugging-port=9222','--user-data-dir=${WIN_USER_DIR}','--no-first-run'" 2>/dev/null

sleep 2

# Verify
if curl -s http://localhost:9222/json/version > /dev/null 2>&1; then
    echo "✅ Chrome CDP is running"
else
    echo "❌ Failed to connect. Is Chrome installed at:"
    echo "   $CHROME"
fi
