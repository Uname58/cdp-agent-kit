<p align="center">
  <img src="https://img.shields.io/pypi/v/cdp-agent-kit?color=blue" alt="PyPI">
  <img src="https://img.shields.io/badge/python-3.10%2B-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License">
</p>

<h1 align="center">cdp-agent-kit</h1>
<p align="center"><b>Give your AI agent a browser.</b> Not a sandbox. <i>Your</i> browser.</p>
<p align="center">把真实用户浏览器作为 AI Agent 的执行环境——共享登录状态、Cookie、Session 和浏览器上下文。</p>

---

## Architecture / 架构

```
┌─────────────────────────────────┐
│          AI Agent               │  ← GPT / Claude / DeepSeek
│    (function-calling loop)      │
└──────────────┬──────────────────┘
               │ tool calls
┌──────────────▼──────────────────┐
│        ToolExecutor             │  ← 10 built-in tools
│  navigate | click | type | ...  │
└──────────────┬──────────────────┘
               │ async commands
┌──────────────▼──────────────────┐
│         CDPBridge               │  ← WebSocket → Chrome
│   (Chrome DevTools Protocol)    │
└──────────────┬──────────────────┘
               │ ws://localhost:9222
┌──────────────▼──────────────────┐
│     Your Existing Chrome        │  ← cookies, sessions, login state
│   (the one you're using now)    │
└─────────────────────────────────┘
```

## Demo / 演示

> Videos recorded on real platforms. Each demo validates a specific capability.

| Demo | Platform | Validates | Recording |
|------|----------|-----------|-----------|
| MBTI Survey | 16personalities | 93 questions, bot detection bypass | 📹 |
| Moodle Quiz | VTC Moodle | Form detection + auto-submit | 📹 |
| Minesweeper | Minesweeper Online | Screenshot→reason→click loop | 📹 |
| 番茄小说 | Fanqie Novel | Long-form workflow (create→write→publish) | 📹 |
| Google Forms | Google Forms | Unknown form auto-fill | [script](examples/google_forms.py) |

## What / 这是什么

**cdp-agent-kit** 是一个让 AI Agent 接管你当前 Chrome 浏览器的工具包。它通过 Chrome DevTools Protocol（CDP）连接已经打开的浏览器，而不是启动新的自动化实例，因此可以直接复用登录状态、Cookie、Session 和浏览器上下文。

传统自动化工具每次都要开新浏览器 → 写登录脚本 → 过验证码 → 维护 cookie，换个网站又重来一遍。cdp-agent-kit 跳过了这一整层——Agent 操作的就是你日常用的那个 Chrome，你登录过什么它就能操作什么。

核心就两个类：
- **CDPBridge** — WebSocket 连 Chrome，截图、读 DOM、点击、输入、执行 JS，一套 API 搞定
- **ToolExecutor** — 把上面那些操作包装成 10 个 LLM function calling 工具，任何支持 function call 的模型都能直接调

| | cdp-agent-kit | Selenium / Playwright |
|---|---|---|
| 登录 | ❌ 不需要，cookie 已存在 | ✅ 必须写登录脚本 |
| Vision | ✅ 截图 → LLM vision | ❌ |
| 给 LLM 用 | ✅ function calling 内置 | ❌ 得自己写 |

## Capability Validation / 能力验证

实战记录见 → [EXPERIMENTS.md](EXPERIMENTS.md)

| Demo | 验证能力 |
|------|----------|
| Cookie Clicker | 长时间循环操作与状态保持 |
| Minesweeper | 截图→推理→操作→再截图的闭环 |
| Google Forms | 未知页面的表单理解与自动填写 |
| 番茄小说 | 真实网站上长流程、多步骤任务执行 |
| React/Arco Design | 受控组件 & 中文 IME 兼容性边界 |

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

## vs Playwright MCP

两者在浏览器控制能力上没有本质差异（`--cdp-endpoint` 也能连真实 Chrome）。Playwright MCP 的关注点在浏览器控制本身，Hermes 在此基础上进一步提供 AgentOS 层能力（定时任务、跨会话记忆、后台推送、多 Agent 协作）。关注点不同，不是替代关系。

## Full Docs / 完整教程

→ [TUTORIAL.md](TUTORIAL.md) (Chinese, with LLM integration examples)

## License / 许可

MIT
