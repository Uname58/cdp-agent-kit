"""CDP Backend — wraps cdp-agent-kit's CDPBridge for CLI-Anything harness.

Uses raw CDP WebSocket (no Chrome extension, no npm dependencies).
Connects to an already-running Chrome with --remote-debugging-port=9222.
"""

import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CDPSession:
    """In-memory session state for browser navigation."""
    cdp_url: str = "http://localhost:9222"
    current_page_id: Optional[str] = None
    current_url: str = ""
    history: list = field(default_factory=list)
    history_pos: int = -1
    daemon_mode: bool = False

    def __post_init__(self):
        # Normalize: http://host:9222 → ws://host:9222/devtools/page/{id}
        if self.cdp_url.startswith("http"):
            self.cdp_http = self.cdp_url.rstrip("/")
            self.cdp_ws_base = self.cdp_http.replace("http://", "ws://") + "/devtools/page/"
        else:
            self.cdp_ws_base = self.cdp_url.rstrip("/") + "/devtools/page/"
            self.cdp_http = self.cdp_url.replace("ws://", "http://")


class CDPBackend:
    """Backend that talks to Chrome via CDP WebSocket.
    
    Uses low-level CDP messages — no dependency on cdp-agent-kit runtime.
    Designed to be importable standalone.
    """

    def __init__(self, session: CDPSession):
        self.session = session
        self._ws = None

    def _get_pages(self) -> list[dict]:
        """List all open pages/tabs."""
        try:
            resp = urllib.request.urlopen(f"{self.session.cdp_http}/json", timeout=5)
            return json.loads(resp.read())
        except Exception as e:
            raise RuntimeError(f"Cannot connect to Chrome at {self.session.cdp_http}. "
                             f"Is Chrome running with --remote-debugging-port? Error: {e}")

    def _get_ws_url(self, page_id: str = None) -> str:
        """Get WebSocket URL for a page."""
        if page_id:
            return f"{self.session.cdp_ws_base}{page_id}"
        pages = self._get_pages()
        if not pages:
            raise RuntimeError("No open pages in Chrome")
        # Prefer the last active page, or the first one
        target = pages[-1]
        return target.get("webSocketDebuggerUrl", "")

    def _ws_send(self, message: dict, timeout: float = 10) -> dict:
        """Send a CDP message and get the response. Uses a fresh connection each call."""
        import websocket as _ws_mod
        
        ws_url = self._get_ws_url(self.session.current_page_id)
        if not ws_url:
            raise RuntimeError("No WebSocket URL available. Navigate to a page first.")
        
        ws = _ws_mod.create_connection(ws_url, timeout=timeout)
        try:
            ws.send(json.dumps(message))
            # Collect responses until we get the matching id or timeout
            deadline = time.time() + timeout
            while time.time() < deadline:
                ws.settimeout(deadline - time.time())
                try:
                    raw = ws.recv()
                    resp = json.loads(raw)
                    if resp.get("id") == message.get("id"):
                        return resp
                except:
                    break
            return {"error": "timeout"}
        finally:
            ws.close()

    def _exec_js(self, expression: str, timeout: float = 10) -> dict:
        """Execute JavaScript in the page."""
        msg_id = int(time.time() * 1000) % 100000
        return self._ws_send({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "returnByValue": True,
            }
        }, timeout)

    # ─── Page Operations ───

    def navigate(self, url: str) -> dict:
        """Navigate to a URL, creating a new tab if needed."""
        # Check if we have a page already
        pages = self._get_pages()
        
        # Try to find an existing page we can reuse
        if not self.session.current_page_id:
            # Create new tab
            try:
                req = urllib.request.Request(
                    f"{self.session.cdp_http}/json/new?{url}",
                    method="PUT"
                )
                resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
                self.session.current_page_id = resp.get("id", "")
            except:
                # Fallback: reuse first page
                if pages:
                    self.session.current_page_id = pages[0]["id"]
                    url_full = url if "://" in url else f"https://{url}"
                    self._exec_js(f'window.location.href = "{url_full}"')
        else:
            # Navigate existing page
            url_full = url if "://" in url else f"https://{url}"
            self._exec_js(f'window.location.href = "{url_full}"')
        
        # Update state
        if url not in self.session.history or self.session.history[-1] != url:
            # Trim forward history
            self.session.history = self.session.history[:self.session.history_pos + 1]
            self.session.history.append(url)
            self.session.history_pos = len(self.session.history) - 1
        
        self.session.current_url = url
        return {"url": url, "status": "navigated"}

    def reload(self) -> dict:
        self._exec_js("location.reload()")
        return {"url": self.session.current_url, "status": "reloaded"}

    def back(self) -> dict:
        if self.session.history_pos > 0:
            self.session.history_pos -= 1
            url = self.session.history[self.session.history_pos]
            self._exec_js(f'window.location.href = "{url}"')
            self.session.current_url = url
            return {"url": url, "status": "back"}
        return {"error": "No history"}

    def forward(self) -> dict:
        if self.session.history_pos < len(self.session.history) - 1:
            self.session.history_pos += 1
            url = self.session.history[self.session.history_pos]
            self._exec_js(f'window.location.href = "{url}"')
            self.session.current_url = url
            return {"url": url, "status": "forward"}
        return {"error": "No forward history"}

    def get_title(self) -> dict:
        result = self._exec_js("document.title")
        title = result.get("result", {}).get("result", {}).get("value", "")
        return {"title": title}

    def get_url(self) -> dict:
        result = self._exec_js("location.href")
        url = result.get("result", {}).get("result", {}).get("value", "")
        return {"url": url}

    def snapshot(self) -> dict:
        """Get a text-based snapshot of the page (accessibility-ish)."""
        js = """
        (() => {
            const body = document.body;
            if (!body) return 'No body element';
            
            function snapshot(el, depth) {
                if (depth > 8) return '';
                let result = '';
                const tag = el.tagName ? el.tagName.toLowerCase() : '';
                const id = el.id ? '#' + el.id : '';
                const cls = el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : '';
                const text = (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3) 
                    ? ' "' + el.textContent.trim().substring(0, 40) + '"' 
                    : '';
                const role = el.getAttribute('role') || '';
                const aria = el.getAttribute('aria-label') || '';
                
                const indent = '  '.repeat(depth);
                result += indent + '<' + tag + id + cls + text + (role ? ' [role=' + role + ']' : '') + (aria ? ' [aria=' + aria + ']' : '');
                
                if (el.children.length > 0) {
                    result += '>\\n';
                    for (const child of el.children) {
                        result += snapshot(child, depth + 1);
                    }
                    result += indent + '</' + tag + '>\\n';
                } else {
                    result += '/>\\n';
                }
                return result;
            }
            return snapshot(body, 0).substring(0, 5000);
        })()
        """
        result = self._exec_js(js, timeout=15)
        snapshot = result.get("result", {}).get("result", {}).get("value", "")
        return {"snapshot": snapshot}

    # ─── Actions ───

    def click(self, selector: str) -> dict:
        """Click an element by CSS selector or text content."""
        js = f"""
        (() => {{
            // Try CSS selector first
            let el = document.querySelector('{selector}');
            
            // Try text content match
            if (!el) {{
                const all = document.querySelectorAll('button, a, input[type=submit], input[type=button], [role=button], span, div');
                for (const e of all) {{
                    if (e.textContent.trim() === '{selector}') {{
                        el = e;
                        break;
                    }}
                }}
            }}
            
            if (!el) return JSON.stringify({{error: 'Element not found: {selector}'}});
            
            el.scrollIntoView({{block: 'center'}});
            el.click();
            return JSON.stringify({{clicked: true, tag: el.tagName, text: el.textContent.trim().substring(0, 50)}});
        }})()
        """
        result = self._exec_js(js)
        value = result.get("result", {}).get("result", {}).get("value", "")
        try:
            return json.loads(value)
        except:
            return {"clicked": True, "raw": str(value)[:200]}

    def type_text(self, selector: str, text: str) -> dict:
        """Type text into an input field."""
        escaped_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        js = f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (!el) return JSON.stringify({{error: 'Element not found: {selector}'}});
            el.focus();
            el.value = '{escaped_text}';
            el.dispatchEvent(new Event('input', {{bubbles: true}}));
            el.dispatchEvent(new Event('change', {{bubbles: true}}));
            return JSON.stringify({{typed: true, selector: '{selector}', length: {len(text)}}});
        }})()
        """
        result = self._exec_js(js)
        value = result.get("result", {}).get("result", {}).get("value", "")
        try:
            return json.loads(value)
        except:
            return {"typed": True}

    def press_key(self, key: str) -> dict:
        js = f"""
        (() => {{
            document.activeElement.dispatchEvent(new KeyboardEvent('keydown', {{key: '{key}', bubbles: true}}));
            document.activeElement.dispatchEvent(new KeyboardEvent('keyup', {{key: '{key}', bubbles: true}}));
            return JSON.stringify({{pressed: '{key}'}});
        }})()
        """
        result = self._exec_js(js)
        value = result.get("result", {}).get("result", {}).get("value", "")
        try:
            return json.loads(value)
        except:
            return {"pressed": key}

    def eval_js(self, code: str) -> dict:
        result = self._exec_js(code, timeout=15)
        value = result.get("result", {}).get("result", {}).get("value", "")
        return {"result": value}

    def select_option(self, selector: str, value: str) -> dict:
        js = f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (!el) return JSON.stringify({{error: 'Element not found'}});
            el.value = '{value}';
            el.dispatchEvent(new Event('change', {{bubbles: true}}));
            return JSON.stringify({{selected: '{value}'}});
        }})()
        """
        result = self._exec_js(js)
        val = result.get("result", {}).get("result", {}).get("value", "")
        try:
            return json.loads(val)
        except:
            return {"selected": value}

    # ─── Utilities ───

    def screenshot(self, path: str = None) -> dict:
        """Take a screenshot via CDP Page.captureScreenshot."""
        import base64
        
        msg_id = int(time.time() * 1000) % 100000
        resp = self._ws_send({
            "id": msg_id,
            "method": "Page.captureScreenshot",
            "params": {"format": "png"}
        })
        
        data = resp.get("result", {}).get("data", "")
        if not data:
            return {"error": "Screenshot failed", "raw": str(resp)[:200]}
        
        if path:
            with open(path, "wb") as f:
                f.write(base64.b64decode(data))
            return {"screenshot": path, "size": len(base64.b64decode(data))}
        else:
            # Save to current directory with timestamp
            import time as _t
            filename = f"screenshot_{int(_t.time())}.png"
            with open(filename, "wb") as f:
                f.write(base64.b64decode(data))
            return {"screenshot": filename, "size": len(base64.b64decode(data))}

    def list_pages(self) -> dict:
        pages = self._get_pages()
        return {
            "pages": [
                {"id": p.get("id", "")[:8], "title": p.get("title", ""), "url": p.get("url", "")}
                for p in pages
            ]
        }

    def extract_text(self, selector: str = None) -> dict:
        if selector:
            js = f"document.querySelector('{selector}')?.innerText || 'Element not found'"
        else:
            js = "document.body.innerText.substring(0, 3000)"
        result = self._exec_js(js)
        text = result.get("result", {}).get("result", {}).get("value", "")
        return {"text": text}

    def wait(self, ms: int) -> dict:
        time.sleep(ms / 1000)
        return {"waited_ms": ms}
