# cdp-agent-kit

> Let AI agents control your browser via Chrome DevTools Protocol.
>
> No browser extensions. No custom drivers. Just Chrome + CDP.

## What it does

cdp-agent-kit connects an LLM (Claude, GPT, DeepSeek, local models) to your **existing Chrome browser** via the CDP debugging port. The agent inherits your cookies, sessions, and logged-in state — it operates as *you*.

```
┌─────────────┐     CDP (localhost:9222)     ┌──────────────┐
│  Your Chrome │◄──────────────────────────►│  Agent / LLM  │
│  (cookies,   │   screenshot, snapshot,     │  decides what  │
│   sessions)  │   click, type, navigate     │  to do next    │
└─────────────┘                              └──────────────┘
```

## Quick Start

### 1. Install

```bash
pip install cdp-agent-kit
playwright install chromium
```

### 2. Launch Chrome with CDP

```bash
./scripts/start_chrome.sh
```

Or manually:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/cdp-chrome
```

### 3. Use it

```python
import asyncio
from cdp_agent_kit import CDPBridge

async def main():
    async with CDPBridge() as bridge:
        # Navigate (cookies included!)
        await bridge.navigate("https://github.com")

        # Read the page
        text = await bridge.get_page_text()
        print(text[:200])

        # Take a screenshot
        await bridge.screenshot(path="github.png")

        # Click and type
        await bridge.click("input[name='q']")
        await bridge.type_text("input[name='q']", "cdp-agent-kit")
        await bridge.press_key("Enter")

asyncio.run(main())
```

## Tools for LLMs

The `cdp_agent_kit.tools` module provides OpenAI/Claude-compatible function definitions:

| Tool | What it does |
|------|-------------|
| `browser_navigate` | Go to a URL |
| `browser_snapshot` | Get accessibility tree (structured page view) |
| `browser_screenshot` | Screenshot → base64 (for vision models) |
| `browser_click` | Click by CSS selector |
| `browser_type` | Type into input fields |
| `browser_select` | Select dropdown options |
| `browser_press_key` | Press Enter/Tab/Escape/etc |
| `browser_get_text` | Extract all visible text |
| `browser_exec_js` | Run arbitrary JavaScript |
| `browser_list_pages` | List all open tabs |

```python
from cdp_agent_kit.tools import TOOL_SCHEMAS, ToolExecutor

# Give these schemas to your LLM as available functions
# When the LLM calls one, execute it:
executor = ToolExecutor(bridge)
result = await executor.execute("browser_click", {"selector": "button.submit"})
```

## Google Forms Auto-Fill Demo

```bash
# 1. Start Chrome with CDP
./scripts/start_chrome.sh

# 2. Run the demo
python examples/google_forms.py "https://docs.google.com/forms/d/e/YOUR-FORM-ID/viewform"
```

The agent will:
1. Navigate to the form (already logged in via your cookies)
2. Analyze all form fields automatically
3. Fill them with provided data
4. Save a confirmation screenshot

## How it's different

| | cdp-agent-kit | Selenium / Playwright scripts |
|---|---|---|
| Cookie/session | ✅ Shared with your browser | ❌ Fresh profile every time |
| Login required? | ❌ Already logged in | ✅ Must script login flow |
| Vision capability | ✅ Screenshot → LLM vision | ❌ Manual |
| For LLMs? | ✅ Function-calling schemas built in | ❌ |

## Requirements

- Python 3.10+
- Chrome / Chromium
- Playwright (`pip install playwright && playwright install chromium`)

## License

MIT
