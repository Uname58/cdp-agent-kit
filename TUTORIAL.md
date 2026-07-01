# cdp-agent-kit 详细教程

> 让你的 AI Agent 直接用你的浏览器——共享 cookie、session、登录态，无需重复登录。

---

## 目录

1. [原理](#1-原理)
2. [安装](#2-安装)
3. [启动 Chrome（CDP 模式）](#3-启动-chrome)
4. [基础 Python API](#4-基础-python-api)
5. [全部 API 参考](#5-全部-api-参考)
6. [接入 LLM](#6-接入-llm-agent-函数调用)
7. [Google Forms 自动填表](#7-google-forms-实战)
8. [常见问题](#8-常见问题)

---

## 1. 原理

```
你打开 Chrome（正常用）          AI Agent
       │                            │
       │   --remote-debugging-port=9222
       │                            │
       ├──────── CDP ───────────────┤
       │  WebSocket 协议             │
       │                            │
       │  Agent 能看到：              │
       │  - 所有标签页                │
       │  - 你的 cookie / session    │
       │  - 页面 DOM                 │
       │  - 实时截图                  │
       │                            │
       │  Agent 能操作：              │
       │  - 导航到任何 URL            │
       │  - 点击按钮                  │
       │  - 填写表单                  │
       │  - 执行 JS                   │
       │  - 截图                     │
```

**和 Selenium/Playwright 的区别**：不用开新浏览器、不用写登录脚本——agent 直接用你**已经在用的浏览器**。

---

## 2. 安装

```bash
# 从 GitHub 安装
pip install git+https://github.com/Uname58/cdp-agent-kit.git

# 或本地开发安装
git clone https://github.com/Uname58/cdp-agent-kit.git
cd cdp-agent-kit
pip install -e .

# 安装 Playwright 的 Chromium 驱动
playwright install chromium
```

依赖：Python 3.10+, Chrome/Chromium。

---

## 3. 启动 Chrome

### 方式 A：用项目脚本（推荐）

```bash
./scripts/start_chrome.sh
```

输出：

```
╔══════════════════════════════════════════════╗
║   CDP Agent Kit — Chrome Launcher          ║
╚══════════════════════════════════════════════╝

  Port:      9222
  User data: ~/.config/cdp-agent-kit-chrome
  Binary:    google-chrome

  Agent connect: CDPBridge(cdp_url='http://localhost:9222')
```

这个脚本会：
- 用一个**独立的 Chrome 用户数据目录**（不影响你日常浏览器）
- 关闭同步、扩展（干净环境）
- 打开 CDP 端口 9222

### 方式 B：手动启动

```bash
google-chrome \
    --remote-debugging-port=9222 \
    --user-data-dir=/tmp/cdp-chrome \
    --no-first-run
```

### ⚠️ 安全提醒

`--remote-debugging-port=9222` 开后，**本机任何进程**都能控制这个 Chrome。
只在本地开发用，不要暴露到公网！

---

## 4. 基础 Python API

### 4.1 连接

```python
import asyncio
from cdp_agent_kit import CDPBridge

async def main():
    # 连接已有的 Chrome
    async with CDPBridge("http://localhost:9222") as bridge:
        print("已连接")

asyncio.run(main())
```

`async with` 会自动连接，退出时清理。

### 4.2 导航 & 截图

```python
async with CDPBridge() as bridge:
    # 打开 GitHub（cookie 已经有了，不需要登录）
    await bridge.navigate("https://github.com")

    # 截图保存
    await bridge.screenshot(path="github.png")

    # 截图拿 base64（发给 vision LLM）
    b64 = await bridge.screenshot_b64()
```

### 4.3 读页面内容

```python
# 方式 1：纯文本（适合给 LLM 阅读）
text = await bridge.get_page_text()
print(text[:300])

# 方式 2：结构化 snapshot（accessibility tree）
snapshot = await bridge.get_snapshot()
print(snapshot)
# 输出：
# [WebArea] 'GitHub'
#   [banner]
#     [navigation]
#       [link] 'Pull requests'
#       [link] 'Issues'
#   [main]
#     [heading] 'cdp-agent-kit'
#     [button] 'Star'
#     [button] 'Fork'

# 方式 3：获取可交互元素列表
elements = await bridge.get_interactive_elements()
for el in elements:
    print(f"<{el.tag}> {el.text[:50]} — selector: {el.selector}")
```

### 4.4 点击 & 输入

```python
# 点击按钮
await bridge.click("button.submit")

# 输入文字（默认会先清空）
await bridge.type_text("input[name='email']", "user@example.com")

# 追加输入（不清空）
await bridge.type_text("textarea", "more text...", clear=False)

# 选择下拉框
await bridge.select_option("select#country", "HK")

# 按键
await bridge.press_key("Enter")
await bridge.press_key("Tab")
```

### 4.5 切换标签页

```python
# 列出所有标签
pages = await bridge.list_pages()
for p in pages:
    print(f"{p['title']} — {p['url']}")

# 切换到第 2 个标签
page = await bridge.get_page(1)

# 开新标签
await bridge.new_page("https://example.com")
```

> ⚠️ 如果不指定 `page_index`，默认操作第 0 个标签（最左边那个）。

### 4.6 执行 JS

```python
# 读任何 DOM 属性
result = await bridge.execute_js("document.title")
print(result)  # "GitHub"

# 改页面
await bridge.execute_js("""
    document.querySelector('.btn').style.background = 'red';
""")
```

---

## 5. 全部 API 参考

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `navigate(url, page_index=0)` | url: str | Page 对象 | 导航到 URL |
| `screenshot(path=None, page_index=0)` | path: str（可选） | bytes (PNG) | 截图 |
| `screenshot_b64(page_index=0)` | — | str (base64) | 截图→base64 |
| `get_snapshot(page_index=0)` | — | str | accessibility tree |
| `get_page_text(page_index=0)` | — | str | 页面文字 |
| `get_interactive_elements(page_index=0)` | — | list[ElementSnapshot] | 可交互元素 |
| `click(selector, page_index=0)` | selector: str | bool | 点击元素 |
| `type_text(selector, text, page_index=0, clear=True)` | selector, text | bool | 输入文字 |
| `select_option(selector, value, page_index=0)` | selector, value | bool | 选下拉框 |
| `press_key(key, page_index=0)` | key: str | — | 按键 |
| `list_pages()` | — | list[dict] | 所有标签 |
| `get_page(index)` | index: int | Page 对象 | 获取标签 |
| `new_page(url)` | url: str | Page 对象 | 开新标签 |
| `scroll(direction, amount, page_index=0)` | "up"/"down", int | — | 滚动 |
| `execute_js(code, page_index=0)` | code: str | str | 执行 JS |

---

## 6. 接入 LLM（Agent 函数调用）

cdp-agent-kit 内置了 **OpenAI/Claude/DeepSeek 兼容的函数调用 schema**。

### 6.1 获取 Tool Schema

```python
from cdp_agent_kit.tools import TOOL_SCHEMAS, ToolExecutor

# 这 10 个 schema 可以直接喂给任何 LLM
for tool in TOOL_SCHEMAS:
    print(tool["name"], "—", tool["description"])
```

输出：

```
browser_navigate        — 导航到 URL
browser_snapshot        — 获取页面结构化视图
browser_screenshot      — 截图（给 vision 模型）
browser_click           — 点击元素
browser_type            — 输入文字
browser_select          — 选择下拉框
browser_press_key       — 按键
browser_list_pages      — 列出标签页
browser_get_text        — 提取页面文字
browser_exec_js         — 执行 JS 代码
```

### 6.2 完整 LLM 循环

```python
import json
from cdp_agent_kit import CDPBridge
from cdp_agent_kit.tools import TOOL_SCHEMAS, ToolExecutor
from openai import AsyncOpenAI  # 以 OpenAI 为例

async def run_agent(task: str):
    client = AsyncOpenAI()
    executor = None

    messages = [
        {"role": "system", "content": "你是一个浏览器操控 agent。使用工具操作当前页面。"},
        {"role": "user", "content": task},
    ]

    async with CDPBridge() as bridge:
        executor = ToolExecutor(bridge)

        while True:
            # 1. 让 LLM 决定下一步
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )

            msg = response.choices[0].message

            # 2. 如果 LLM 回复文字 = 任务完成
            if msg.content and not msg.tool_calls:
                print(f"Agent: {msg.content}")
                break

            # 3. 如果 LLM 调用了工具 → 执行
            messages.append(msg)
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = await executor.execute(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })

# 示例任务
asyncio.run(run_agent("打开 GitHub，搜索 cdp-agent-kit，然后截图"))
```

LLM 会自动：
1. 看当前页面状态（`browser_snapshot`）
2. 决定点哪里（`browser_click`）
3. 需要输入就调用（`browser_type`）
4. 操作完继续看页面，直到任务完成

### 6.3 接入 Hermes

把 `TOOL_SCHEMAS` 放进 Hermes 的工具集就行：

```yaml
# ~/.hermes/profiles/default/config.yaml
toolsets:
  cdp_browser:
    provider: cdp-agent-kit
    tools: TOOL_SCHEMAS  # 直接用
```

---

## 7. Google Forms 实战

### 7.1 准备

1. 启动 CDP Chrome
2. 打开一个 Google Forms 链接

### 7.2 运行

```bash
python examples/google_forms.py "https://docs.google.com/forms/d/e/YOUR-FORM-ID/viewform"
```

### 7.3 发生了什么

```
╔══════════════════════════════════╗
║   CDP Agent Kit — Google Forms  ║
╚══════════════════════════════════╝

Connecting to Chrome (localhost:9222)...
Found 3 open tabs

Navigating to: https://docs.google.com/forms/...

Analyzing form fields...

Detected fields:
  Text inputs:  3
  Textareas:    1
  Radio groups: 2
  Checkboxes:   1
  Dropdowns:    1
  Submit:        div[role='button']

Filling form...
  ✓ Filled 'email' → 'demo@example.com'
  ✓ Filled 'name' → 'Test User'
  ✓ Filled 'feedback' → 'cdp-agent-kit works!'

Screenshot saved: /tmp/google_form_filled.png

✅ Demo complete!
```

### 7.4 定制填入数据

修改 `examples/google_forms.py` 里的 `form_data` 字典：

```python
form_data = {
    "email": "your-real@email.com",
    "name": "Your Name",
    "feedback": "Your feedback here",
    # 添加你的 form 的字段...
}
```

---

## 8. 常见问题

### Q: Cookie 怎么共享的？

A: Chrome 用 `--user-data-dir` 指定目录启动后，所有 cookie/session/localStorage 都在那个目录。agent 连上去后，自动继承。

### Q: 微信/支付宝网页版可以用吗？

A: 可以。你手动扫码登录一次后，agent 就能操作所有需要登录的页面。

### Q: 多个 agent 同时用会冲突吗？

A: 不会。每个 `CDPBridge` 实例独立连接。但建议一个 agent 操作一个标签页。

### Q: 安全吗？

A: CDP 端口只在 `localhost` 监听，外部无法访问。但本地恶意进程可以连——别在不可信环境跑。

### Q: 需要 vision 模型吗？

A: 不一定。`get_snapshot()` 和 `get_interactive_elements()` 给的结构化数据对 LLM 已经够用。但截图对复杂 UI（CAPTCHA、图表）有帮助。
