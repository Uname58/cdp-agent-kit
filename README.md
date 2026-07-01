<p align="center">
  <img src="https://img.shields.io/pypi/v/cdp-agent-kit?color=blue" alt="PyPI">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License">
</p>

<h1 align="center">cdp-agent-kit</h1>
<p align="center"><b>Give your AI agent a browser.</b> Not a sandbox. <i>Your</i> browser.</p>
<p align="center">把浏览器交给 AI Agent——共享你的 cookie，你登录过的地方它都能操作。</p>

---

```
┌──────────────┐                              ┌──────────────┐
│  Your Chrome │◄──── CDP (localhost:9222) ───│  AI Agent    │
│              │                               │              │
│  cookies ✅  │   screenshot, snapshot,       │  GPT / Claude│
│  session ✅  │   click, type, navigate       │  DeepSeek    │
│  logged in ✅│                               │  local LLM   │
└──────────────┘                              └──────────────┘
```

## Why / 为什么用它

| | cdp-agent-kit | Selenium / Playwright |
|---|---|---|
| 登录 | ❌ 不需要，cookie 已存在 | ✅ 必须写登录脚本 |
| Vision | ✅ 截图 → LLM vision | ❌ |
| 给 LLM 用 | ✅ function calling 内置 | ❌ 得自己写 |

## Install / 安装

```bash
pip install cdp-agent-kit
playwright install chromium
```

## Quick Start / 快速开始

```bash
# 1. 启动 CDP Chrome
./scripts/start_chrome.sh

# 或手动
google-chrome --remote-debugging-port=9222
```

```python
import asyncio
from cdp_agent_kit import CDPBridge

async def main():
    async with CDPBridge() as browser:
        # 跳转 — cookie 天然带着，不需要登录
        await browser.navigate("https://github.com")

        # 读页面
        print(await browser.get_page_text()[:200])

        # 点搜索框、输入、回车
        await browser.click("input[name='q']")
        await browser.type_text("input[name='q']", "cdp-agent-kit")
        await browser.press_key("Enter")

        # 截图
        await browser.screenshot(path="result.png")

asyncio.run(main())
```

## LLM Tools / Agent 工具

10 built-in tools, ready for OpenAI / Claude / DeepSeek function calling:

| Tool / 工具 | What / 做什么 |
|---|---|
| `browser_navigate` | Go to URL / 跳转 |
| `browser_snapshot` | Read page structure / 读页面结构 |
| `browser_screenshot` | Screenshot for vision / 截图给视觉模型 |
| `browser_click` | Click element / 点击 |
| `browser_type` | Type text / 输入 |
| `browser_select` | Select dropdown / 选下拉框 |
| `browser_press_key` | Press key / 按键 |
| `browser_get_text` | Extract text / 提文字 |
| `browser_exec_js` | Run JS / 执行脚本 |
| `browser_list_pages` | List tabs / 列出所有标签页 |

```python
from cdp_agent_kit.tools import TOOL_SCHEMAS, ToolExecutor

# Feed TOOL_SCHEMAS to your LLM as available functions
# LLM calls one → executor handles it
executor = ToolExecutor(bridge)
result = await executor.execute("browser_click", {"selector": "button.submit"})
```

## Google Forms Demo / 自动填表

```bash
python examples/google_forms.py "https://docs.google.com/forms/d/e/YOUR-FORM/viewform"
```

Agent automatically detects all fields and fills them — no CSS selector hunting.

## Full Docs / 完整教程

→ [TUTORIAL.md](TUTORIAL.md) (Chinese, with LLM integration examples)

## License / 许可

MIT
