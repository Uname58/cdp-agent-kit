<p align="center">
  <img src="https://img.shields.io/pypi/v/cdp-agent-kit?color=blue" alt="PyPI">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License">
</p>

<h1 align="center">cdp-agent-kit</h1>
<p align="center"><strong>An Agent Browser Runtime.</strong> Connect your AI to the browser you are already using — not a fresh, headless copy.</p>
<p align="center">Give your agent your cookies, your tabs, your logins. Skip the login script. Skip the CAPTCHA. Just work.</p>

---

## The Problem

Every existing browser automation tool starts from zero.

```
Launch new browser
      ↓
Login again
      ↓
Handle cookies
      ↓
Handle authentication
      ↓
Solve CAPTCHA
      ↓
Run automation
```

Each task rebuilds the world. Your agent spends more time proving it is you than doing actual work.

**cdp-agent-kit** inverts this model.

```
Your real Chrome
      ↓
Already logged in
      ↓
Existing cookies
      ↓
Existing tabs
      ↓
Extensions, bookmarks, history
      ↓
AI connects via Chrome DevTools Protocol
      ↓
Continue working immediately
```

No login. No cookie export. No duplicated browser. No session rebuilding.

The AI joins **your** browsing session — the one you have been building for months.

---

## What Makes This Different

### 1. Existing Browser Session

Your agent does not launch a browser. It connects to yours.

This means your GitHub, Gmail, Notion, Jira, AWS Console — every service you are already logged into — is immediately available to the agent. The cookies, OAuth tokens, and session state that took you weeks to accumulate are not copied. They are shared.

### 2. Persistent Context Across Tasks

The browser stays alive. One session can serve multiple AI tasks throughout the day.

```
Morning:   "Open my Gmail inbox"
Afternoon: "Reply to the first unread email"
Evening:   "Download the attachment from today's thread"
```

No state is lost between calls. The agent picks up exactly where it left off, because the browser never restarted.

### 3. Human + AI Collaboration

This is not automation that replaces you. It is automation that works **alongside** you.

- You browse normally — checking email, reading docs, scrolling Twitter
- The AI takes over a tab — fills a form, scrapes data, submits a post
- You continue browsing in another tab
- The AI finishes its task and returns the tab to you

Everything happens inside the same browser instance. You and the agent share the same viewport, the same session, the same reality.

### 4. LLM Agnostic

**cdp-agent-kit** does not belong to one model. Any LLM that supports Tool Calling can use it.

| Model | Integration |
|-------|-------------|
| GPT-4o / GPT-4.1 | OpenAI function calling |
| Claude 3.5 / 4 | Anthropic tool use |
| DeepSeek-V3 / V4 | Function calling |
| Gemini 2.5 | Google function calling |
| Qwen 2.5 / 3 | Tool calling |
| Hermes | Native tool integration |
| Local models (via vLLM / Ollama) | OpenAI-compatible endpoint |

The same `TOOL_SCHEMAS` array works across all of them.

---

## Architecture

```
┌─────────────────────────────────┐
│          Your LLM               │  ← GPT, Claude, DeepSeek, Gemini…
│    (function-calling loop)      │
└──────────────┬──────────────────┘
               │ tool calls
┌──────────────▼──────────────────┐
│        ToolExecutor             │  ← 10 built-in tools
│  navigate | click | type | …    │
└──────────────┬──────────────────┘
               │ async commands
┌──────────────▼──────────────────┐
│         CDPBridge               │  ← Playwright over CDP
│   (Chrome DevTools Protocol)    │
└──────────────┬──────────────────┘
               │ ws://localhost:9222
┌──────────────▼──────────────────┐
│     Your Existing Chrome        │  ← cookies, sessions, logins, tabs
│   (the one you are using now)   │
└─────────────────────────────────┘
```

Two layers:

- **CDPBridge** — connects to a running Chrome instance via `connect_over_cdp`, wraps navigation, screenshots, DOM interaction, and JS execution into a clean async API.
- **ToolExecutor** — exposes that API as 10 function-calling tools that any LLM can invoke directly.

---

## Quick Start

### 1. Install

```bash
pip install git+https://github.com/Uname58/cdp-agent-kit.git
```

The core (`CDPClient`, raw CDP) needs only `websocket-client` — auto-installed, no Playwright. For the optional Playwright-based bridge (`CDPBridge`):

```bash
pip install "cdp-agent-kit[playwright]"
playwright install chromium
```

### 2. Launch Chrome with CDP

```bash
# macOS / Linux
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/cdp-chrome

# Windows (WSL2 NAT mode)
# Double-click scripts/cdp_launcher.vbs
# Or manually:
chrome.exe --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir=%TEMP%\cdp-chrome
```

> **WSL2 users:** See [EXPERIMENTS.md §6](EXPERIMENTS.md#6-wsl--windows-cdp-连接配置) for the complete connection setup, including portproxy configuration and startup order.

### 3. Use It

The core is `CDPClient` — a raw CDP client, synchronous, zero Playwright:

```python
from cdp_agent_kit import CDPClient

# Connect to your existing Chrome (cookies, logins, tabs already there)
client = CDPClient("localhost", 9222)

# List tabs
for t in client.list_tabs():
    print(t["title"], "—", t["url"])

# Navigate (cookies included)
client.navigate("https://github.com")

# Read the page
text = client.read_page_text()
print(text[:200])

# Click + fill a form
client.click("input[name='q']")
client.fill_form("input[name='q']", "cdp-agent-kit")

# Security testing: black-box XSS verification (detects the alert dialog)
result = client.verify_xss("https://target/?q=<script>alert(1)</script>")
print(result)  # {"status": "CONFIRMED", ...} or INCONCLUSIVE
```

`CDPClient` also auto-heals — if the WebSocket hangs or drops, it restarts the debug Chrome and retries once. Cross-platform: WSL gateway-IP resolution, Windows launcher, macOS/Linux direct connect.

> **Prefer the Playwright-based `CDPBridge`?** It's the async, higher-level API with structured snapshots (`get_snapshot`, `get_interactive_elements`, `scroll`) — install the `[playwright]` extra and use `CDPBridge` as before.

### 4. Run a demo

The fastest way to confirm it works — run one of the shipped examples:

```bash
# Auto-fill a Google Form (auto-detects fields, no CSS selector hunting)
python examples/google_forms.py "https://docs.google.com/forms/d/e/YOUR-FORM/viewform"

# Post to Reddit with your logged-in account (fetch() submit, bypasses isTrusted)
python examples/cdp_reddit_post.py
```

See [Examples](#examples) for the full list (MBTI survey, Minesweeper solver, Cookie Clicker, and more).

---

## What Changed Since v0.1.0

The first release (v0.1.0, July 1) was a minimal proof-of-concept: a CDP bridge with `navigate`, `screenshot`, `click`, `type`, plus a Google Forms auto-fill demo. Here is what has changed since:

| Area | v0.1.0 | Now |
|------|--------|-----|
| **Positioning** | "Let AI control your browser via CDP" | **Agent Browser Runtime** — connect to the browser you already use |
| **Tools** | 5 core tools | **10 tools** — added `browser_select`, `browser_press_key`, `browser_list_pages`, `browser_get_text`, `browser_exec_js` |
| **Platforms** | macOS / Linux only | **+ Windows** — WSL2 → Windows Chrome via NAT mode + portproxy + `cdp_launcher.vbs` |
| **Validation** | None (toy examples) | **EXPERIMENTS.md** — 7 real websites, incl. `isTrusted` defeat, `fetch()` submit bypass |
| **Demos** | Google Forms auto-fill | **+ Reddit auto-post, MBTI survey, Moodle, Minesweeper solver, Cookie Clicker** |
| **Integrations** | OpenAI / Claude tool schemas | **+ CLI-Anything harness, SKILL.md, demo GIFs** |
| **Architecture** | Single bridge module | **Layered** — LLM → ToolExecutor → CDPBridge → Chrome |

The core idea never changed — control your *existing* browser, inherit cookies/logins/sessions, skip the login script. Everything added since v0.1.0 makes that idea work on more platforms, against harder real-world targets, and with richer tool coverage.

---

## LLM Integration

Feed `TOOL_SCHEMAS` to any function-calling model:

```python
from openai import AsyncOpenAI
from cdp_agent_kit import CDPBridge
from cdp_agent_kit.tools import TOOL_SCHEMAS, ToolExecutor

async def run_agent(task: str):
    client = AsyncOpenAI()
    messages = [
        {"role": "system", "content": "You control a browser. Use the provided tools."},
        {"role": "user", "content": task},
    ]

    async with CDPBridge() as bridge:
        executor = ToolExecutor(bridge)

        while True:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            msg = response.choices[0].message

            if msg.content and not msg.tool_calls:
                print(msg.content)
                break

            messages.append(msg)
            for tc in msg.tool_calls or []:
                args = json.loads(tc.function.arguments)
                result = await executor.execute(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })

asyncio.run(run_agent("Open GitHub, search for cdp-agent-kit, and take a screenshot"))
```

---

## Tool API

10 tools, same interface across all LLMs:

| Tool | What it does |
|------|-------------|
| `browser_navigate` | Navigate a tab to a URL |
| `browser_snapshot` | Get structured accessibility tree of the page |
| `browser_screenshot` | Take a screenshot (returns base64 for vision models) |
| `browser_click` | Click an element by CSS selector |
| `browser_type` | Type text into an input field |
| `browser_select` | Select an option from a `<select>` dropdown |
| `browser_press_key` | Press a keyboard key (Enter, Tab, Escape…) |
| `browser_list_pages` | List all open tabs with URLs and titles |
| `browser_get_text` | Extract all visible text from the page |
| `browser_exec_js` | Execute arbitrary JavaScript in the page |

---

## Real-World Validation

This project has been tested against real websites — not toy examples. Full write-up in [EXPERIMENTS.md](EXPERIMENTS.md).

| Test | Platform | Result | Key Finding |
|------|----------|--------|-------------|
| MBTI Survey (93 questions) | 16personalities (React) | ✅ Bypassed | Event chain simulation defeats `isTrusted`-less platforms |
| Reddit post | Reddit (old.reddit.com) | ✅ Bypassed | `fetch()` to `/api/submit` bypasses all frontend automation checks |
| Google Forms | Google Forms | ✅ Works | Auto-detects fields from any unknown form |
| Minesweeper solver | Minesweeper Online | ✅ Works | Screenshot → reason → click loop |
| Cookie Clicker | Cookie Clicker | ✅ Works | Direct state injection via JS |
| Fanqie Novel (React + Arco Design) | Fanqie Novel | ⚠️ Partial | React controlled components resist CDP injection; Chinese IME unsupported |
| Deeeep.io (WebGL) | Deeeep.io | ❌ Blocked | `event.isTrusted` checked; CDP synthetic events always `false` |

---

## Comparison

Design goals differ. This table describes what each project is built for — not which is "better."

| | Playwright | Selenium | Browser Use | cdp-agent-kit |
|---|---|---|---|---|
| **Primary purpose** | E2E testing & automation | E2E testing & automation | AI browser agent | Agent Browser Runtime |
| **Existing browser support** | Via `connect_over_cdp` | Via ChromeDriver | Launches fresh browser | ✅ Core design |
| **Uses current login session** | Possible, not default | Possible, not default | No (fresh profile) | ✅ Default |
| **Human-AI collaboration** | No | No | No | ✅ Same browser, shared tabs |
| **Persistent browser state** | Per-test cleanup | Per-test cleanup | Per-task | ✅ Browser lives across tasks |
| **E2E testing** | ✅ Built for this | ✅ Built for this | No | Not designed for this |
| **Tool Calling ready** | Via MCP | Via MCP | ✅ Built-in | ✅ Built-in (10 tools) |
| **Python API** | ✅ Rich | ✅ Rich | ✅ | ✅ Async, 15 methods |

Playwright and Selenium are testing frameworks. **Browser Use** is an AI agent that launches its own browser. **cdp-agent-kit** is a runtime layer that lets any AI agent work inside the browser you already have open.

---

## Examples

### Navigate, read, click

```python
async with CDPBridge() as bridge:
    await bridge.navigate("https://news.ycombinator.com")
    text = await bridge.get_page_text()
    await bridge.click("a.storylink")
```

### Fill any form automatically

```bash
python examples/google_forms.py "https://docs.google.com/forms/d/e/YOUR-FORM/viewform"
```

The agent detects fields (text inputs, radios, checkboxes, dropdowns), fills them, and takes a confirmation screenshot — no CSS selector hunting required.

### Post to Reddit with your logged-in account

```
python examples/cdp_reddit_post.py
```

Uses `fetch()` to bypass `isTrusted` checks. CAPTCHA solved by the human; everything else is automatic.

### WSL2 → Windows Chrome

For developers running AI agents inside WSL2 who want to control their Windows Chrome:

1. Ensure WSL2 is in NAT mode (not mirrored)
2. Double-click `scripts/cdp_launcher.vbs` on Windows
3. From WSL: `curl http://172.27.64.1:9222/json`

Full setup documented in [EXPERIMENTS.md §6](EXPERIMENTS.md#6-wsl--windows-cdp-连接配置).

---

## FAQ

### Why not just use Playwright?

Playwright is a testing framework. Its design assumes ephemeral browser instances — launch, test, tear down. cdp-agent-kit assumes the opposite: a long-lived browser that persists across tasks. Different problems, different tools.

### Is this secure?

CDP exposes full browser control to any process on the same machine. Bind to `localhost` only. Do not expose the debugging port to a network. For remote access, tunnel through SSH.

### Does it work with my existing Chrome profile?

Yes. Point `--user-data-dir` to your existing Chrome profile directory, or use the scripts provided to launch a dedicated profile. Either way, the agent inherits whatever state that profile contains.

### Can multiple agents share one browser?

Yes. Each `CDPBridge` instance connects independently. Assign different tabs to different agents. The browser handles concurrent operations at the Chromium level.

### What about CAPTCHA?

cdp-agent-kit shares your real browser fingerprint and session, which reduces CAPTCHA triggers. When one does appear, the human-in-the-loop model solves it — the agent pauses, you complete the CAPTCHA, the agent resumes.

---

## Roadmap

- [ ] Multi-tab orchestration (agent assigns subtasks across tabs)
- [ ] Structured element selectors (beyond CSS — by label, role, text content)
- [ ] Vision model integration (GPT-4V / Claude vision for UI understanding)
- [ ] Record-and-replay for common workflows
- [ ] MCP server wrapper (expose tools over Model Context Protocol)
- [ ] Session snapshot / restore (save and reload browser state)
- [ ] Headless fallback mode (for environments without a display)

---

## Contributing

Bug reports, feature requests, and pull requests are welcome. For significant changes, open an issue first to discuss the direction.

Areas where contributions are especially valuable:

- Testing against more real-world websites (especially React / Vue / Svelte SPAs)
- Additional LLM integration examples (Claude, Gemini, local models)
- Platform-specific setup guides (macOS, Linux distributions, Docker)

---

## License

MIT — [Uname58](https://github.com/Uname58)
