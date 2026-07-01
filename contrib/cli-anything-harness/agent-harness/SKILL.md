---
name: cli-anything-browser-cdp
description: Use when an agent needs to control a web browser via Chrome DevTools Protocol. Connects to the user's existing Chrome — no new browser, no extensions, no login scripts. Supports navigation, DOM snapshot, click, type, screenshot, JS execution, and tab management. Best for tasks that require the user's existing login state (cookies/sessions).
---

# Browser CDP — Chrome Automation via DevTools Protocol

Use this CLI when an agent needs to interact with web pages through the user's **existing Chrome browser**. Unlike sandboxed browser tools, this connects to the browser the user is already using — inheriting all cookies, sessions, and login state automatically.

## Quick Start

```bash
# Navigate
cli-anything-browser-cdp --json page open https://example.com

# Read the page
cli-anything-browser-cdp --json page snapshot

# Interact
cli-anything-browser-cdp --json act click "button.submit"
cli-anything-browser-cdp --json act type "input[name='email']" "user@example.com"

# Capture
cli-anything-browser-cdp --json util screenshot

# List all tabs
cli-anything-browser-cdp --json util list-pages
```

## Prerequisites

Chrome must be running with remote debugging enabled:

```bash
google-chrome --remote-debugging-port=9222
```

For WSL → Windows Chrome, use the launcher from cdp-agent-kit:

```bash
./scripts/start_chrome.sh
```

Then connect:

```bash
cli-anything-browser-cdp --cdp http://172.27.64.1:9222 page open https://example.com
```

## Command Groups

### page — Navigation
- `open <url>` — Navigate to URL
- `reload` — Reload current page
- `back` / `forward` — Navigate history
- `title` — Get page title
- `url` — Get current URL
- `snapshot` — Get DOM accessibility tree

### act — Interaction
- `click <selector>` — Click element (CSS selector or text match)
- `type <selector> <text>` — Type into input
- `press <key>` — Press keyboard key
- `eval <js>` — Execute JavaScript
- `select <selector> <value>` — Select dropdown option

### util — Utilities
- `screenshot [path]` — Capture page screenshot
- `list-pages` — List all Chrome tabs
- `text [selector]` — Extract text from page/element
- `wait <ms>` — Wait N milliseconds

### daemon — Persistent Connection
- `start` / `stop` / `status` — Manage persistent CDP session

## Key Differentiator

Unlike Playwright, Selenium, or DOMShell-based tools:

1. **No new browser** — connects to YOUR Chrome
2. **No login** — inherits existing cookies/sessions
3. **No extensions** — raw CDP WebSocket, zero browser-side setup
4. **Agent-friendly** — `--json` flag on all commands for machine-readable output

## Limitations

Documented in [EXPERIMENTS.md](https://github.com/Uname58/cdp-agent-kit/blob/master/EXPERIMENTS.md):
- React controlled components (Arco Design) resist CDP value injection
- Chinese/Japanese/Korean IME input not supported via CDP
- Server-side anti-cheat may IP-ban automated patterns
- Canvas/WebGL games check `event.isTrusted` and block CDP events

## References

- Repository: https://github.com/Uname58/cdp-agent-kit
- Harness location: `contrib/cli-anything-harness/agent-harness/`
- CLI-Anything integration: https://github.com/HKUDS/CLI-Anything
