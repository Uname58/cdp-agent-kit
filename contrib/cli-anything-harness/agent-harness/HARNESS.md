# Browser CDP Harness: Raw CDP (Chrome DevTools Protocol)

## Purpose

This harness provides browser automation using raw Chrome DevTools Protocol (CDP)
via WebSocket — **no Chrome extension, no npm dependencies, no new browser instance**.

Unlike the DOMShell-based browser harness which spawns a fresh Chrome, this harness
connects to **your existing Chrome** (the one you're already using). It inherits
your cookies, sessions, and login state automatically.

## Architecture Overview

```
┌─────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│   CLI Commands   │────▶│ browser_cdp_cli.py │────▶│   CDPBackend    │
│  (Click groups)  │     │   (Click CLI)      │     │  (core/init.py) │
└─────────────────┘     └───────────────────┘     └────────┬────────┘
                                                           │
                                                    WebSocket (CDP)
                                                           │
                                                    ┌──────▼──────┐
                                                    │ Your Chrome │
                                                    │ cookies ✅  │
                                                    │ sessions ✅ │
                                                    │ logged in ✅│
                                                    └─────────────┘

State Management:
┌─────────────────────────────────────────────────────────────────┐
│  CDPSession                                                     │
│    - cdp_url: str          (Chrome CDP endpoint)               │
│    - current_page_id: str  (active tab ID)                     │
│    - current_url: str      (current page URL)                  │
│    - history: list[str]    (back/forward navigation)           │
│    - history_pos: int      (position in history)               │
│    - daemon_mode: bool     (persistent connection)             │
└─────────────────────────────────────────────────────────────────┘
```

## CDP Backend

This harness uses raw CDP WebSocket messages — no MCP server, no Chrome extension.

### Prerequisites

Chrome must be running with remote debugging enabled:

```bash
# Linux
google-chrome --remote-debugging-port=9222

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

# WSL → Windows Chrome
# See cdp-agent-kit/scripts/start_chrome.sh
```

### CDP Messages Used

| Operation | CDP Method | Notes |
|-----------|-----------|-------|
| List tabs | `GET /json` (HTTP) | Returns all open pages |
| Navigate | `GET /json/new?{url}` (HTTP PUT) | Creates or reuses tab |
| Execute JS | `Runtime.evaluate` | Primary way to interact with pages |
| Screenshot | `Page.captureScreenshot` | Base64 PNG |
| Click/Type | `Runtime.evaluate` → JS `el.click()` / `el.value =` | Injected via CDP |

### Key Design Decisions

#### 1. No Chrome Extension

DOMShell requires a Chrome extension + npm package. This harness uses only CDP's
built-in `Runtime.evaluate` — no installation beyond `pip install`.

**Trade-off:** Less structured page access (no Accessibility Tree filesystem).
**Advantage:** Zero browser-side setup, works with any Chrome instance.

#### 2. Fresh WebSocket Per Command

Each CLI command opens a new WebSocket, sends one CDP message, reads response,
and closes. This is simpler than maintaining a persistent connection and avoids
timeout/stale-connection issues.

**Daemon mode** (`daemon start`) is available for when low latency matters.

#### 3. Cookie/Session Sharing (Killer Feature)

Because this connects to YOUR Chrome, not a new instance:
- No login scripts needed
- No CAPTCHA solving
- No session management
- Whatever you're logged into, the agent can use

This is the single biggest advantage over Selenium, Playwright, and DOMShell.

#### 4. JS-Based Interaction

Instead of CDP's `Input.dispatchMouseEvent` / `Input.dispatchKeyEvent`:

```
# We use JS injection
Runtime.evaluate("document.querySelector('button').click()")

# Not CDP input events
Input.dispatchMouseEvent({type: 'mousePressed', ...})
```

**Why:** JS injection avoids `event.isTrusted` issues and handles React's
synthetic event system better (though Arco Design still resists — see
[EXPERIMENTS.md](../../../EXPERIMENTS.md)).

## Command-to-CDP Mapping

| CLI Command | CDP Operation |
|-------------|---------------|
| `page open <url>` | HTTP PUT `/json/new?{url}` or `Runtime.evaluate("location.href=...")` |
| `page snapshot` | `Runtime.evaluate` → JS DOM tree walker |
| `page title` | `Runtime.evaluate("document.title")` |
| `act click <sel>` | `Runtime.evaluate` → `el.click()` |
| `act type <sel> <text>` | `Runtime.evaluate` → `el.value=...; el.dispatchEvent(...)` |
| `act eval <js>` | `Runtime.evaluate` (raw JS passthrough) |
| `util screenshot` | `Page.captureScreenshot` |
| `util list-pages` | HTTP GET `/json` |

## Known Limitations

### 1. React Controlled Components
Arco Design (ByteDance) and similar React component libraries swallow
programmatic value changes. JS `el.value = "text"` + `input`/`change` events
are not enough — React's fiber reconciliation ignores them.

**Workaround:** User performs critical form filling manually. Agent handles
content creation and page reading.

### 2. Chinese IME
`Input.dispatchKeyEvent` only sends ASCII key codes. Chinese, Japanese,
Korean input requires IME composition which CDP cannot simulate.

**Workaround:** Pre-composed text via `el.value = "中文"` (when React isn't
blocking it).

### 3. Anti-Cheat Detection
Server-side behavioral analysis can detect automation patterns even when
individual actions look human-like. Minesweeper Online IP-banned us despite
normal-looking click timings.

### 4. Canvas/WebGL Games
`event.isTrusted` is `false` for all CDP-injected events. Canvas/WebGL
games that check this property are immune to CDP automation.

## Integration with cdp-agent-kit

This harness is part of the [cdp-agent-kit](https://github.com/Uname58/cdp-agent-kit)
ecosystem. For higher-level agent integration (LLM function calling, multi-step
task planning, memory), use cdp-agent-kit directly:

```python
from cdp_agent_kit import CDPBridge

async with CDPBridge() as browser:
    await browser.navigate("https://example.com")
    await browser.click("button.submit")
```

This harness provides the CLI-Anything compatible wrapper around that same
CDP connection.

## Contributing

This harness lives at `cdp-agent-kit/contrib/cli-anything-harness/`.

To register in CLI-Hub:
1. Open a PR against [HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything)
2. Add entry to `public_registry.json`
3. Include link to this harness

## References

- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
- [cdp-agent-kit](https://github.com/Uname58/cdp-agent-kit)
- [CLI-Anything](https://github.com/HKUDS/CLI-Anything)
- [EXPERIMENTS.md — CDP Battle Report](../../../EXPERIMENTS.md)
