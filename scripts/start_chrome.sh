#!/usr/bin/env bash
# Launch Chrome with remote debugging enabled.
# cdp-agent-kit connects to localhost:9222.

set -euo pipefail

CDP_PORT="${CDP_PORT:-9222}"
CHROME="${CHROME:-google-chrome}"

# Platform-specific paths
case "$(uname -s)" in
    Linux*)
        # Try standard locations
        for path in google-chrome google-chrome-stable chromium chromium-browser; do
            if command -v "$path" &>/dev/null; then
                CHROME="$path"
                break
            fi
        done
        USER_DATA="$HOME/.config/cdp-agent-kit-chrome"
        ;;
    Darwin*)
        CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        USER_DATA="$HOME/Library/Application Support/cdp-agent-kit-chrome"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        CHROME="C:/Program Files/Google/Chrome/Application/chrome.exe"
        USER_DATA="$HOME/AppData/Local/cdp-agent-kit-chrome"
        ;;
    *)
        echo "Unsupported OS: $(uname -s)"
        exit 1
        ;;
esac

echo "╔══════════════════════════════════════════════╗"
echo "║   CDP Agent Kit — Chrome Launcher          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "  Port:      $CDP_PORT"
echo "  User data: $USER_DATA"
echo "  Binary:    $CHROME"
echo ""
echo "  Agent connect: CDPBridge(cdp_url='http://localhost:$CDP_PORT')"
echo ""

mkdir -p "$USER_DATA"

exec "$CHROME" \
    --remote-debugging-port="$CDP_PORT" \
    --user-data-dir="$USER_DATA" \
    --no-first-run \
    --no-default-browser-check \
    --disable-extensions \
    --disable-sync \
    --disable-background-networking \
    "$@"
