"""raw CDP client — 读 Chrome 状态 + 页面 DOM + 黑盒验证 XSS（从 HackMate cdp.py 迁移，v2）。

- HTTP 端点：列 tab、读标题/URL（零依赖）
- WebSocket：读 DOM / 跑 JS / 监听 dialog（需 websocket-client）
- 卡死自愈：WS 断开/超时自动重启 Chrome 重试一次
- 跨平台：WSL 网关 IP 解析 + Windows launcher + Mac/Linux 直连
"""


import json
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path


try:
    import websocket  # websocket-client
    _HAS_WS = True
    # WS 卡死/断开/超时（WebSocketTimeoutException 等均为 WebSocketException 子类）+ socket 层错误
    _WS_ERRORS = (websocket.WebSocketException, OSError)
except ImportError:
    websocket = None
    _HAS_WS = False
    _WS_ERRORS = (OSError,)


class CDPError(Exception):
    pass


class CDPConnError(CDPError):
    """连接类错误（HTTP 端点连不上/超时），用于卡死自愈的重启判定。"""
    pass


# verify_xss 的交互触发：对带事件处理器的元素派发 mouseover/focus/click，并点 javascript: 链接，
# 让需点击/悬停才触发的 XSS 也能弹窗。只碰有处理器的元素，不点普通链接（避免误导航）。
_XSS_TRIGGER_JS = (
    "(function(){try{"
    "var s='[onclick],[onmouseover],[onmouseenter],[onfocus],[onpointerover],a[href^=\"javascript:\"]';"
    "document.querySelectorAll(s).forEach(function(el){try{"
    "el.dispatchEvent(new MouseEvent('mouseover',{bubbles:true}));"
    "el.dispatchEvent(new MouseEvent('mouseenter',{bubbles:true}));"
    "if(el.focus)el.focus();"
    "el.dispatchEvent(new FocusEvent('focus',{bubbles:true}));"
    "if(el.click)el.click();"
    "}catch(e){}});"
    "}catch(e){}return 'triggered';})()"
)


# 「AI 引导光标」注入 JS：假光标 + 说明气泡，手动一步步推进（点「下一步」才继续，不自动播放）。
# 纯页面注入（不动真鼠标），刷新即消失。__STEPS__ 由 guide_tour() 替换成 [[sel,text,showcode],...]。
# showcode=true 时气泡里展示该元素的真实 outerHTML（指出「源代码/反射点」）。
_GUIDE_TOUR_JS = r"""
(function(){
  function cleanup(){ for(const id of ['hmCur','hmTip','hmStyle']){const e=document.getElementById(id);if(e)e.remove();} }
  cleanup();
  const st=document.createElement('style'); st.id='hmStyle';
  st.textContent=`
    #hmCur{position:fixed;z-index:1000000;width:28px;height:28px;left:50%;top:50%;pointer-events:none;
      transition:left 1.0s cubic-bezier(.4,0,.2,1),top 1.0s cubic-bezier(.4,0,.2,1);
      filter:drop-shadow(0 2px 4px rgba(0,0,0,.4))}
    #hmTip{position:fixed;z-index:1000000;max-width:360px;background:#111827;color:#f9fafb;
      font:500 14px/1.6 system-ui,sans-serif;padding:14px 16px;border-radius:12px;
      box-shadow:0 10px 30px rgba(0,0,0,.4);transition:left .9s,top .9s;border-left:3px solid #22c55e}
    #hmTip .hmStep{font-size:12px;color:#22c55e;font-weight:700;margin-bottom:6px;letter-spacing:.5px}
    #hmTip pre{margin:10px 0 0;padding:8px;background:#0b1220;border-radius:8px;max-height:140px;
      overflow:auto;font:12px/1.5 ui-monospace,Menlo,monospace;color:#93c5fd;white-space:pre-wrap;word-break:break-all}
    #hmTip .hmBtn{margin-top:12px;background:#22c55e;color:#06281a;font-weight:700;border:none;
      border-radius:8px;padding:7px 16px;cursor:pointer;font-size:13px}
    #hmTip .hmBtn:hover{background:#16a34a;color:#fff}
    .hmHot{outline:3px solid #f59e0b !important;outline-offset:2px;transition:outline .3s}
  `;
  document.head.appendChild(st);
  const cur=document.createElement('div'); cur.id='hmCur';
  cur.innerHTML='<svg viewBox="0 0 24 24" width="28" height="28"><path d="M4 2l16 7-6 2-2 6z" fill="#22c55e" stroke="#065f46" stroke-width="1.2"/></svg>';
  document.body.appendChild(cur);
  const tip=document.createElement('div'); tip.id='hmTip'; document.body.appendChild(tip);
  const STEPS=__STEPS__;
  const q=s=>{try{return s?document.querySelector(s):null}catch(e){return null}};
  let i=0, prev=null;
  function render(){
    if(prev){prev.classList.remove('hmHot');prev=null;}
    const s=STEPS[i]||['body','',false]; const sel=s[0], text=s[1], showcode=s[2];
    const el=q(sel); let x=innerWidth/2, y=innerHeight/2;
    if(el){const r=el.getBoundingClientRect();x=r.left+r.width/2;y=r.top+r.height/2;
      el.classList.add('hmHot'); prev=el; el.scrollIntoView({block:'center',behavior:'smooth'});}
    cur.style.left=x+'px'; cur.style.top=y+'px';
    tip.style.left=Math.max(12,Math.min(x+24,innerWidth-380))+'px';
    tip.style.top=Math.max(12,Math.min(y+24,innerHeight-160))+'px';
    const last=i===STEPS.length-1;
    tip.innerHTML='';
    const sc=document.createElement('div'); sc.className='hmStep'; sc.textContent=`步骤 ${i+1}/${STEPS.length}`;
    const bd=document.createElement('div'); bd.textContent=text;
    tip.appendChild(sc); tip.appendChild(bd);
    if(showcode && el){ const pre=document.createElement('pre'); pre.textContent=el.outerHTML.slice(0,500); tip.appendChild(pre); }
    const bt=document.createElement('button'); bt.className='hmBtn'; bt.textContent=last?'完成 ✓':'下一步 →';
    bt.onclick=()=>{ if(last){cleanup();return;} i++; render(); };
    tip.appendChild(bt);
  }
  render();   // 只显示第一步，等用户点「下一步」
  return 'guide ready';
})()
"""


class CDPClient:
    def __init__(self, host="localhost", port=9222, timeout=5):
        self.host = host
        self.port = port
        self.base = f"http://{host}:{port}"
        self.timeout = timeout
        self._test_tab_id = None

    def _get_json(self, path):
        url = f"{self.base}{path}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            raise CDPConnError(f"无法连接 CDP ({url}): {e}")
        except Exception as e:
            raise CDPError(f"CDP 响应异常 ({url}): {e}")

    def list_tabs(self):
        data = self._get_json("/json")
        tabs = []
        for t in data:
            if t.get("type") != "page":
                continue
            tabs.append({
                "id": t.get("id", ""),
                "title": t.get("title", ""),
                "url": t.get("url", ""),
                "ws": t.get("webSocketDebuggerUrl", ""),
            })
        return tabs

    def is_tab_active(self, tab):
        """Return whether a page is the currently visible Chrome tab."""
        ws_url = tab.get("ws")
        if not ws_url:
            raise CDPError("该 tab 没有 webSocketDebuggerUrl")
        return self._cdp_eval(
            ws_url, "document.visibilityState === 'visible'", timeout=3) is True

    def open_new_tab(self, url="about:blank"):
        from urllib.parse import quote
        req = urllib.request.Request(
            f"{self.base}/json/new?{quote(url, safe=':/?&=')}", method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            raise CDPError(f"开新标签页失败: {e}")

    def ensure_test_tab(self, initial_url="about:blank"):
        """返回 HackMate 专用测试标签；同一 CDPClient 生命周期内只创建一次。"""
        tabs = self.list_tabs()
        if self._test_tab_id:
            for tab in tabs:
                if tab.get("id") == self._test_tab_id:
                    return tab
        tab = self.open_new_tab(initial_url)
        self._test_tab_id = tab.get("id")
        if not self._test_tab_id:
            raise CDPError("创建测试标签失败：Chrome 未返回 tab id")
        return tab

    def _cdp_cmd(self, ws_url, method, params=None, timeout=10):
        if not _HAS_WS:
            raise CDPError("缺少 websocket-client，请 pip install websocket-client")
        ws = websocket.create_connection(ws_url, timeout=timeout)
        try:
            ws.send(json.dumps({"id": 1, "method": method, "params": params or {}}))
            msg = None
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == 1:
                    break
        finally:
            ws.close()
        if msg.get("error"):
            raise CDPError(f"CDP {method} 错误: {msg['error'].get('message', '')}")
        return msg.get("result", {})

    def _cdp_eval(self, ws_url, expression, timeout=10):
        result = self._cdp_cmd(
            ws_url, "Runtime.evaluate",
            {"expression": expression, "returnByValue": True}, timeout)
        r = result.get("result", {})
        if r.get("subtype") == "error":
            raise CDPError(f"Runtime.evaluate 出错: {r.get('description', '')}")
        return r.get("value", "")

    def _get_tab(self, index=0, tab_id=None):
        tabs = self.list_tabs()
        if tab_id:
            for tab in tabs:
                if tab.get("id") == tab_id:
                    return tab
            raise CDPError(f"找不到标签 id={tab_id}")
        if not (0 <= index < len(tabs)):
            raise CDPError(f"序号 {index} 超出范围（0-{len(tabs)-1}）")
        return tabs[index]

    def restart(self):
        """卡死自愈：杀掉调试 Chrome → 重新拉起 → 等 CDP 就绪。返回是否恢复。"""
        _kill_debug_chrome()
        time.sleep(1.5)
        launch_chrome(self.port)
        return wait_for_cdp(self.host, self.port, timeout=25)

    def _resilient(self, index, op, tab_id=None, test_tab=False):
        """跑 op(tab)；WS 卡死(超时/断开)或端点连不上则重启 Chrome、重取 tab、重试一次，仍失败才抛。"""
        try:
            tab = self.ensure_test_tab() if test_tab else self._get_tab(index, tab_id)
            return op(tab)
        except _WS_ERRORS + (CDPConnError,):
            if not self.restart():
                raise
            if test_tab:
                self._test_tab_id = None
                tab = self.ensure_test_tab()
            else:
                tab = self._get_tab(index)
            return op(tab)

    def navigate(self, url, index=0, test_tab=False):
        def op(tab):
            self._cdp_cmd(tab["ws"], "Page.navigate", {"url": url})
            return f"已导航到 {url}"
        return self._resilient(index, op, test_tab=test_tab)

    def fill_form(self, selector, value, index=0, test_tab=False):
        js = (
            "(function(){"
            f"const el=document.querySelector({json.dumps(selector)});"
            "if(!el)return '未找到元素: '+" + json.dumps(selector) + ";"
            "if(el.tagName==='SELECT'){"
            f"el.value={json.dumps(value)};"
            "el.dispatchEvent(new Event('change',{bubbles:true}));"
            "return '已选: '+" + json.dumps(selector) + ";"
            "}"
            "const proto=el.tagName==='TEXTAREA'?window.HTMLTextAreaElement.prototype:window.HTMLInputElement.prototype;"
            f"Object.getOwnPropertyDescriptor(proto,'value').set.call(el,{json.dumps(value)});"
            "el.dispatchEvent(new Event('input',{bubbles:true}));"
            "el.dispatchEvent(new Event('change',{bubbles:true}));"
            "return '已填: '+" + json.dumps(selector) + ";"
            "})()"
        )
        return self._resilient(index, lambda tab: self._cdp_eval(tab["ws"], js),
                               test_tab=test_tab)

    def click(self, selector, index=0, test_tab=False):
        js = (
            "(function(){"
            f"const el=document.querySelector({json.dumps(selector)});"
            "if(!el)return '未找到元素: '+" + json.dumps(selector) + ";"
            "el.click();"
            "return '已点击: '+" + json.dumps(selector) + ";"
            "})()"
        )
        return self._resilient(index, lambda tab: self._cdp_eval(tab["ws"], js),
                               test_tab=test_tab)

    def find_xss_entries(self, index=0, test_tab=False):
        js = (
            "(function(){"
            "const out={url:location.href,"
            "url_params:Array.from(new URLSearchParams(location.search).keys()),"
            "inputs:[],textareas:[],selects:[],forms:[],links_with_params:[]};"
            "document.querySelectorAll('input').forEach(el=>{out.inputs.push("
            "{name:el.name||'',type:el.type||'',id:el.id||'',placeholder:el.placeholder||''})});"
            "document.querySelectorAll('textarea').forEach(el=>{out.textareas.push("
            "{name:el.name||'',id:el.id||'',placeholder:el.placeholder||''})});"
            "document.querySelectorAll('select').forEach(el=>{out.selects.push("
            "{name:el.name||'',id:el.id||''})});"
            "document.querySelectorAll('form').forEach(el=>{out.forms.push("
            "{action:el.action||'',method:el.method||''})});"
            "document.querySelectorAll('a[href*=\"?\"]').forEach(el=>{out.links_with_params.push("
            "{text:(el.innerText||'').trim().slice(0,50),href:el.getAttribute('href')})});"
            "return JSON.stringify(out);"
            "})()"
        )
        return self._resilient(index, lambda tab: self._cdp_eval(tab["ws"], js),
                               test_tab=test_tab)

    def verify_xss(self, url, index=0, wait=4, autotrigger=True, test_tab=False):
        """黑盒验证：导航到带 payload 的 URL，监听 alert 弹窗（弹=JS 真执行=XSS 成立）。

        三态：CONFIRMED（dialog 触发）/ INCONCLUSIVE（未触发，不能排除）/ NOT_CONFIRMED（预留）。
        autotrigger=True：导航后自动对带事件处理器的元素（onclick/onmouseover/onfocus、javascript: 链接）
        派发 mouseover/focus/click，让需点击/悬停才触发的 XSS 也能验出来（纯 <script> 注入不受影响）。
        WS 卡死会自动重启 Chrome 重试一次（见 _resilient）。
        """
        if not _HAS_WS:
            raise CDPError("缺少 websocket-client")
        return self._resilient(
            index, lambda tab: self._verify_xss_on(tab, url, wait, autotrigger),
            test_tab=test_tab)

    def _verify_xss_on(self, tab, url, wait=4, autotrigger=True):
        ws = websocket.create_connection(tab["ws"], timeout=wait + 8)
        try:
            ws.send(json.dumps({"id": 1, "method": "Page.enable", "params": {}}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == 1:
                    break
            ws.send(json.dumps({"id": 2, "method": "Page.navigate", "params": {"url": url}}))
            deadline = time.time() + wait
            trigger_at = time.time() + 1.2 if autotrigger else None
            triggered = not autotrigger
            dialog = None
            while time.time() < deadline:
                if not triggered and time.time() >= trigger_at:
                    try:
                        ws.send(json.dumps({"id": 3, "method": "Runtime.evaluate",
                                            "params": {"expression": _XSS_TRIGGER_JS}}))
                    except Exception:
                        pass
                    triggered = True
                ws.settimeout(0.3)
                try:
                    msg = json.loads(ws.recv())
                except Exception:
                    continue  # 0.3s 轮询片无消息，继续等（可能稍后才触发 dialog）
                if msg.get("method") == "Page.javascriptDialogOpening":
                    dialog = msg.get("params", {}).get("message", "")
                    ws.send(json.dumps({"id": 99, "method": "Page.handleJavaScriptDialog",
                                        "params": {"accept": True}}))
                    break
            if dialog is not None:
                result = {
                    "status": "CONFIRMED",
                    "evidence": f"观察到 Page.javascriptDialogOpening，dialog 消息: {dialog}",
                    "reason": "alert 弹窗触发，说明注入的 JS 在该执行路径上真的执行了",
                    "scope": f"URL: {url}",
                }
            else:
                result = {
                    "status": "INCONCLUSIVE",
                    "evidence": "导航完成，wait 窗口内未观察到 javascriptDialogOpening",
                    "reason": "alert 未触发不能排除 XSS：可能 CSP 拦截 / 上下文不符 / payload 不合适 / 事件未触发",
                    "scope": f"URL: {url}（黑盒验证，未读响应源码，故不判 NOT_CONFIRMED）",
                }
            return json.dumps(result, ensure_ascii=False)
        finally:
            ws.close()

    def read_page_text(self, tab=None, timeout=10, test_tab=False):
        if test_tab:
            return self._resilient(
                0, lambda target: self._cdp_eval(
                    target["ws"], "document.body ? document.body.innerText : ''", timeout),
                test_tab=True)
        if tab is None:
            tab = self._get_tab(0)
        ws_url = tab.get("ws")
        if not ws_url:
            raise CDPError("该 tab 没有 webSocketDebuggerUrl")
        return self._cdp_eval(ws_url, "document.body ? document.body.innerText : ''", timeout)

    def read_page_html(self, tab=None, timeout=10, test_tab=False):
        if test_tab:
            return self._resilient(
                0, lambda target: self._cdp_eval(
                    target["ws"], "document.documentElement.outerHTML", timeout),
                test_tab=True)
        if tab is None:
            tab = self._get_tab(0)
        ws_url = tab.get("ws")
        if not ws_url:
            raise CDPError("该 tab 没有 webSocketDebuggerUrl")
        return self._cdp_eval(ws_url, "document.documentElement.outerHTML", timeout)

    def guide_tour(self, steps, index=0, test_tab=False):
        """注入「AI 引导光标」+ 说明气泡，手动一步步推进（用户点「下一步」才继续，不自动播放）。

        steps: [(selector, text, showcode), ...] 或 [{'selector','text','code'}, ...]。
        showcode=True 时气泡里展示该元素真实 outerHTML（指出源代码/反射点）。
        selector 找不到的元素会指向屏幕中央。返回 'guide ready'（先只显示第一步）。
        """
        norm = []
        for s in steps:
            if isinstance(s, dict):
                sel = s.get("selector") or s.get("sel") or "body"
                code = bool(s.get("code") or s.get("showcode"))
                norm.append([sel, str(s.get("text", "")), code])
            else:
                code = bool(s[2]) if len(s) > 2 else False
                norm.append([s[0] or "body", str(s[1]), code])
        js = _GUIDE_TOUR_JS.replace("__STEPS__", json.dumps(norm, ensure_ascii=False))
        return self._resilient(index, lambda tab: self._cdp_eval(tab["ws"], js),
                               test_tab=test_tab)


# ---- 跨平台启动 / 发现 ----

def _wsl_to_windows_path(path):
    p = str(path)
    if p.startswith("/mnt/") and len(p) > 6:
        drive = p[5:6].upper()
        rest = p[6:]
        return f"{drive}:{rest}".replace("/", "\\")
    return p.replace("/", "\\")


def _is_wsl():
    """仅在 WSL 下为真。launcher 代理只对 WSL 必需；原生 Windows/Git Bash/Mac/Linux 直连。"""
    try:
        with open("/proc/version", "r") as f:
            ver = f.read().lower()
        return "microsoft" in ver or "wsl" in ver
    except Exception:
        return False


def find_launcher():
    base = Path(__file__).resolve().parent.parent
    for rel in ("scripts/cdp_launcher.vbs", "scripts/cdp_launcher.exe",
                "tools/cdp/launcher/cdp_launcher.exe"):
        p = base / rel
        if p.exists():
            return str(p)
    return None


def _find_chrome():
    import shutil
    for name in ("google-chrome", "chromium", "chromium-browser", "google-chrome-stable"):
        p = shutil.which(name)
        if p:
            return p
    mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if Path(mac).exists():
        return mac
    for c in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Chromium\Application\chrome.exe",
    ):
        if Path(c).exists():
            return c
    return None


def _cleanup_wsl_cdp():
    cmd = (
        "Get-Process -Name cdp_launcher -ErrorAction SilentlyContinue | Stop-Process -Force; "
        "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
        "Where-Object { $_.CommandLine -match 'remote-debugging-port' } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    try:
        subprocess.run(["powershell.exe", "-Command", cmd], capture_output=True, timeout=20)
    except Exception:
        pass


def _kill_debug_chrome():
    """跨平台杀掉带 --remote-debugging-port 的调试 Chrome（best-effort），用于卡死自愈重启。
    只杀调试实例，不碰用户日常 Chrome（后者不带该参数）。"""
    import sys as _sys
    try:
        if _sys.platform == "win32":
            cmd = (
                "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
                "Where-Object { $_.CommandLine -match 'remote-debugging-port' } | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
            )
            subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                           capture_output=True, timeout=20)
        else:
            subprocess.run(["pkill", "-f", "remote-debugging-port"],
                           capture_output=True, timeout=10)
    except Exception:
        pass


def launch_chrome(port=9222):
    launcher = find_launcher()
    if launcher and _is_wsl():
        _cleanup_wsl_cdp()
        time.sleep(2)
        win_path = _wsl_to_windows_path(launcher)
        try:
            subprocess.Popen(
                ["powershell.exe", "-Command", f"Start-Process '{win_path}'"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (FileNotFoundError, OSError):
            return False
    chrome = _find_chrome()
    if not chrome:
        return False
    try:
        subprocess.Popen(
            [chrome, f"--remote-debugging-port={port}", "--remote-allow-origins=*",
             f"--user-data-dir={Path.home() / '.hackmate-chrome'}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (FileNotFoundError, OSError):
        return False


def wait_for_cdp(host, port, timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{host}:{port}/json/version", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def resolve_cdp_host(host="localhost"):
    """WSL 下 localhost 换成网关 IP（否则连不到 Windows Chrome proxy）；原生环境返回原值。"""
    if host not in ("localhost", "127.0.0.1", "::1"):
        return host
    if not _is_wsl():
        return host
    try:
        out = subprocess.run(["ip", "route", "show", "default"],
                             capture_output=True, text=True, timeout=5).stdout
        parts = out.split()
        if "via" in parts:
            gw = parts[parts.index("via") + 1]
            if gw:
                return gw
    except Exception:
        pass
    return host


def ensure_cdp(host, port, auto_launch=True, timeout=25):
    host = resolve_cdp_host(host)
    c = CDPClient(host, port)
    try:
        c._get_json("/json/version")
        return c
    except CDPError:
        pass
    if auto_launch and launch_chrome():
        print("[cdp] 已触发 Chrome 启动，等待 CDP 就绪（如弹 UAC/MessageBox 请点确认）...")
        if wait_for_cdp(host, port, timeout):
            print("[cdp] CDP 已就绪")
            return c
        print("[cdp] 等待超时，CDP 仍未就绪")
    return None
