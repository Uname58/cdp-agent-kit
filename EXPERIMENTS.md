# CDP 实战报告

> 用真实 Chrome × AI Agent 操控 Web 应用的边界测试记录。

---

## 测试环境

- **Chrome**: Windows 11, `--remote-debugging-port=9222 --remote-debugging-address=0.0.0.0`
- **Agent 端**: WSL2 (Ubuntu), `ws://172.27.64.1:9222`
- **Agent**: Hermes (DeepSeek-v4-pro) + 自研 CDPBridge

---

## 1. React SPA 表单 — 番茄小说作家后台

**平台**: [番茄小说](https://fanqienovel.com) 作家专区  
**框架**: React + Arco Design (字节跳动)  
**任务**: 创建新书、填写书名/标签/简介、发布章节

### 结果：部分成功

| 操作 | CDP 方式 | 结果 |
|------|----------|------|
| 导航 | CDP `Page.navigate` | ✅ |
| 读页面 | `Runtime.evaluate` + DOM snapshot | ✅ |
| 点击按钮 | `element.click()` + 完整事件链 | ⚠️ 不稳定 |
| 文本输入 (英文) | JS `value` setter + `input` event | ⚠️ React 不识别 |
| 文本输入 (中文) | `Input.dispatchKeyEvent` | ❌ 不支持 IME |
| 选择下拉 | `element.click()` + click option | ⚠️ 不稳定 |
| 富文本编辑器 (章节) | `contenteditable` + `innerHTML` | ✅ 可用 |

### 关键发现

**Arco Design 的 React 受控组件几乎完全抵抗 CDP 注入：**

```javascript
// 这些方法全都不行：
input.value = "xxx"; input.dispatchEvent(new Event('input'));  // React 看不到
input.dispatchEvent(new Event('change'));                       // 也看不到
// React__proprietary fiber 注入                        // 找不到入口
Input.dispatchKeyEvent({type:'keyDown', ...})                   // 英文可以，中文不行
```

**唯一有效的方案：用户手动填写 + AI 提供内容。**

HTML 富文本编辑器 (`contenteditable`) 是例外——直接写 `innerHTML` 可以。

---

## 2. 游戏操控

### Cookie Clicker ✅
```javascript
// 直接改状态，无服务端验证
Game.cookies = 1e100;
```
- **结论**: DOM 游戏 + 无服务端反作弊 = 完全可控

### Minesweeper Online ⚠️ → 🚫
- **操控**: 成功，CDP 点击 + JS 读棋盘状态
- **反作弊**: 服务端检测到非人类行为模式 → **IP 被封** (61.92.234.48)
- **教训**: 即使操作看起来像人，服务端行为分析能识别自动化

### Deeeep.io ❌
- WebGL Canvas 游戏
- 检查 `event.isTrusted` — CDP 合成事件固定为 `false`
- **结论**: Canvas/WebGL 游戏不可控

### Snake 🟡
- DOM 游戏，但延迟太高
- 理论上可注入 JS solver 直接计算最优路径

### 游戏操控总结

| 类型 | CDP 可行 | 风险 |
|------|----------|------|
| DOM + 无服务端验证 | ✅ | 无 |
| DOM + 有服务端反作弊 | ⚠️ | IP 封禁 |
| Canvas/WebGL (`isTrusted`) | ❌ | — |
| WebSocket 实时游戏 | ❌ | 延迟过高 |

---

## 3. 问卷侦查绕过

**平台**: 16personalities  
**框架**: React  
**任务**: 自动填写 MBTI 人格测试（93 题）

### 结果：成功绕过，但答案质量差

```javascript
// 完整事件链驱动 React 合成事件
el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
el.dispatchEvent(new MouseEvent('click', {bubbles: true}));
el.dispatchEvent(new Event('change', {bubbles: true}));
```

- **绕过**: 平台完全没检测到自动化——共享真实 cookie/session/指纹
- **问题**: LLM 在否定句式（"我不喜欢..."）上匹配出错，得出 ISFJ-A 而非 INTJ-T
- **改进方向**: LLM 逐题推理 + prompt 提示否定句式，而非简单关键词匹配

---

## 4. 番茄小说网文创作

### 完整流程

1. CDP 导航至作家后台 → 检测到 Arco Design React 组件
2. 书名标签简介等关键表单由用户手动填写
3. AI 通过 CDP 读取页面、提供内容建议
4. 章节编辑器 (`contenteditable`) CDP 可控——AI 直接写了 1320 字第一章
5. 用户手动填章节号 + 点击提交 → 发布成功

### 数据

- 书名: 《黑网猎手》(ID: 7657504777403632665)
- 笔名: 零日372
- 第一章: 1320 字 (ID: 7657505137191043609)
- 状态: 待审核

### 关键教训

| 环节 | 谁做 | 原因 |
|------|------|------|
| 内容创作 | AI | LLM 强项 |
| 中文表单 | 人 | CDP 不支持 IME + React 受控组件 |
| 最终提交 | 人 | Arco Design 按钮不响应 CDP 点击 |
| 策略决策 | 人 | 市场判断、题材选择 |

**最佳模式：AI 做内容 + 读页面，人做关键操作。**

---

## 5. CDP vs Codex/Playwright

| 维度 | CDP 直连 | Playwright MCP (`--cdp-endpoint`) |
|------|----------|----------------------------------|
| 浏览器共享 | ✅ 你的 Chrome | ✅ 也能连 |
| cookie/session | ✅ 自带 | ✅ 自带 |
| 功能差距 | — | 操控能力无本质差异 |
| 定时任务 | ✅ cron | ❌ |
| 跨会话记忆 | ✅ memory | ❌ |
| 后台推送 | ✅ notify | ❌ |
| 多 Agent 并行 | ✅ delegate_task | ❌ |

**结论**: 纯 CDP 操控能力没区别，差异在 AgentOS 基础设施。

---

## 6. WSL → Windows CDP 连接配置

```powershell
# Windows PowerShell (Admin)
New-NetFirewallRule -DisplayName "CDP" -Direction Inbound -LocalPort 9222 -Protocol TCP -Action Allow
netsh interface portproxy add v4tov4 listenport=9222 listenaddress=0.0.0.0 connectport=9222 connectaddress=127.0.0.1
```

```bash
# 启动 Chrome（Windows）
chrome.exe --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --user-data-dir=%TEMP%\cdp-chrome

# WSL 连接
curl http://172.27.64.1:9222/json
```

---

## 7. 核心教训

1. **React 受控组件是最难的对手** — 不是 CDP 的问题，是 React 的合成事件系统刻意隔离了 DOM
2. **中文 IME 无解** — `Input.dispatchKeyEvent` 只能发 ASCII，涉及 IME 的输入必须人来
3. **反作弊会封 IP** — 即使单次操作像人，行为模式分析能识别自动化
4. **人是必要环节** — 最佳实践是 AI 读 + 想 + 写，人在关键节点确认
5. **cookie 共享是最大优势** — 能绕过一切登录/验证码/设备指纹侦查

---

## 8. Reddit 自动发帖

**任务**: CDP 操控 Reddit 发帖（填标题/正文/选择flair/提交）  
**难点**: `form.submit()` 被 JS 拦截，按钮 `click()` 被 `isTrusted` 检查拒绝

### 结果：✅ 成功

| 方式 | 结果 |
|------|------|
| `form.submit()` | ❌ JS event handler 拦截 |
| `el.click()` CDP 事件 | ❌ `isTrusted=false` |
| `Input.dispatchMouseEvent` | ❌ 同样被拒 |
| `fetch()` POST `/api/submit` | ✅ **绕过所有前端验证** |

### 核心发现

**Reddit 前端反自动化 = `isTrusted` + 事件拦截。但 API 层不检查。**
直接用 `fetch()` 构造 `FormData` POST 到 `/api/submit` 即可绕过。

### 流程
1. CDP 导航至 `old.reddit.com/r/.../submit`
2. 切到文本 Tab → 等待用户手动完成 CAPTCHA
3. `Runtime.evaluate` 提取表单字段
4. 通过 JSON API `/r/.../api/link_flair.json` 获取 flair UUID
5. `fetch()` POST `FormData` → 成功发布

### CAPTCHA 协作模式
- 脚本等待文件信号 (`go.txt` 被删除) → 用户解决 CAPTCHA
- 解决后脚本填表 → `fetch()` 提交
- 不需要手动填任何表单字段

**脚本**: [`examples/cdp_reddit_post.py`](examples/cdp_reddit_post.py)  
**成功帖子**: `r/ClaudeAI` — 推广 cdp-agent-kit

---

*最后更新: 2026-07-10*
