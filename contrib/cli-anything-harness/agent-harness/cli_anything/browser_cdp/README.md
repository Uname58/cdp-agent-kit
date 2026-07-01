# cdp-agent-kit: CLI-Anything Harness

> CLI-Anything harness for browser automation via **Chrome DevTools Protocol (CDP)**.
> Connects to **your existing Chrome** — no new browser, no extensions, no login scripts.

## Why This Exists

[CLI-Anything](https://github.com/HKUDS/CLI-Anything) makes desktop software agent-native by wrapping them with CLI commands. This harness brings that same philosophy to web automation — but with a key difference:

**It connects to YOUR Chrome.** The one you're already using. With your cookies, sessions, and login state.

Existing browser harness (CLIBrowser) uses DOMShell MCP, which launches a fresh Chrome instance. This harness uses raw CDP WebSocket to talk to any Chrome with `--remote-debugging-port=9222`.

## Architecture

```
┌─────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│   CLI Commands   │────▶│ browser_cdp_cli.py │────▶│   CDPBridge     │
│  (Click groups)  │     │   (Click CLI)      │     │ (cdp-agent-kit) │
└─────────────────┘     └───────────────────┘     └────────┬────────┘
                                                           │
                                                    WebSocket (CDP)
                                                           │
                                                    ┌──────▼──────┐
                                                    │ Your Chrome │
                                                    │ cookies ✅  │
                                                    │ sessions ✅ │
                                                    └─────────────┘
```

## Usage

```bash
# One-shot commands
cli-anything-browser-cdp page open https://github.com
cli-anything-browser-cdp page snapshot
cli-anything-browser-cdp act click "input[name='q']"
cli-anything-browser-cdp act type "input[name='q']" "cdp-agent-kit"
cli-anything-browser-cdp util screenshot

# JSON output for agents
cli-anything-browser-cdp --json page snapshot

# Custom CDP endpoint
cli-anything-browser-cdp --cdp ws://172.27.64.1:9222 page open https://example.com
```

## Command Reference

### page — Navigation
| Command | Description |
|---------|-------------|
| `page open <url>` | Navigate to URL |
| `page reload` | Reload current page |
| `page back` | Go back |
| `page forward` | Go forward |
| `page title` | Get page title |
| `page url` | Get current URL |
| `page snapshot` | Get full DOM accessibility snapshot |

### act — Actions
| Command | Description |
|---------|-------------|
| `act click <selector>` | Click element (CSS selector or text) |
| `act type <selector> <text>` | Type into input field |
| `act press <key>` | Press keyboard key |
| `act eval <js>` | Execute JavaScript in page |
| `act select <selector> <value>` | Select dropdown option |

### util — Utilities
| Command | Description |
|---------|-------------|
| `util screenshot [path]` | Take screenshot |
| `util list-pages` | List all open Chrome tabs |
| `util text [selector]` | Extract text from page/element |
| `util wait <ms>` | Wait milliseconds |

### daemon — Persistent Connection
| Command | Description |
|---------|-------------|
| `daemon start` | Start persistent CDP session |
| `daemon stop` | Stop persistent session |
| `daemon status` | Check session status |

## Key Differences from CLIBrowser (DOMShell)

| | browser-cdp (this) | browser (DOMShell) |
|---|---|---|
| Backend | Raw CDP WebSocket | DOMShell MCP |
| Chrome | **Yours** (cookie sharing) | Fresh instance |
| Extensions | ❌ None needed | ✅ Chrome extension |
| DOM access | Full DOM + screenshots | Accessibility Tree only |
| Dependencies | `cdp-agent-kit` | `@apireno/domshell` (npm) |

## Known Limitations

See [EXPERIMENTS.md](../../../EXPERIMENTS.md) for detailed battle-tested findings:
- React controlled components (Arco Design) resist CDP injection
- Chinese IME input incompatible with `Input.dispatchKeyEvent`
- Server-side anti-cheat can trigger IP bans on automated play
- `event.isTrusted` blocks Canvas/WebGL game automation
