# Reddit Auto-Post via CDP

> `cdp-agent-kit` demo: use raw CDP to automate Reddit post creation, handling React forms, flair selection, and CAPTCHA.

## What It Does

Navigates to `old.reddit.com/r/ClaudeAI/submit`, fills in title/body/flair, and submits — all via Chrome DevTools Protocol, sharing your real browser session (cookies, login, 2FA).

## The Hard Part

Reddit's frontend is hostile to automation:
- `form.submit()` is intercepted by JS event handlers
- Button `click()` is blocked by `isTrusted` checks
- CAPTCHA tokens expire quickly

## Solution: `fetch()` direct POST

Instead of fighting the frontend, the script extracts form fields, waits for user to solve CAPTCHA manually, then POSTs directly to Reddit's `/api/submit` endpoint with `FormData`. This bypasses all frontend validation.

## Usage

```bash
# 1. Start Chrome with CDP
chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\temp\chrome-cdp

# 2. Run script (interactive CAPTCHA step)
python examples/cdp_reddit_post.py

# Or with file-signal for headless/background
# Script waits for go.txt to be deleted → CAPTCHA solved
```

## Key Findings

| Approach | Result |
|----------|--------|
| `form.submit()` | ❌ Intercepted by JS |
| Button `click()` via CDP | ❌ `isTrusted` = false |
| `Input.dispatchMouseEvent` | ❌ No synthetic trust |
| `fetch()` POST `/api/submit` | ✅ Bypasses all frontend |

## Dependencies

- Raw CDP (WebSocket to `localhost:9222`)
- No Selenium, no Playwright
- Just Python stdlib + your real Chrome browser session
