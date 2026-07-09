#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CDP Reddit Post — cdp-agent-kit — live build."""
import json, time, sys, socket, struct, random, subprocess, base64, re, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TITLE = "I built cdp-agent-kit -- let AI agents control your existing Chrome instead of launching a new one every time"
BODY = """I've been using Claude Code, Codex, and other coding agents a lot, and one thing drove me crazy: every time they need a browser, they spin up a brand new Chrome instance.

Fresh Chrome means:
- No cookies, no login sessions
- CAPTCHA hell all over again
- Can't access your authenticated tabs
- Duplicate extensions, no history

So I built **cdp-agent-kit** -- a lightweight Python toolkit that connects AI agents to **the Chrome you're already using**.

## What it does

Instead of `agent -> launch Chrome -> struggle with auth`, it's:

```
agent -> CDP -> your existing Chrome -> authenticated tabs
```

The kit wraps Chrome DevTools Protocol into clean Python functions that agents can call:
- `screenshot()` -- capture any tab
- `navigate(url)` -- go to a page
- `click()`, `type()` -- interact with pages
- `evaluate(js)` -- run arbitrary JavaScript
- `network_monitor()` -- intercept requests

## Why this matters

The killer feature: your Chrome already has all your logins, cookies, and sessions. Instead of an agent fighting Cloudflare and reCAPTCHA in a fresh browser, it can operate in an already-authenticated environment.

I've been using it to:
- Auto-post to Reddit (from my logged-in account)
- Scrape authenticated dashboards
- Automate form filling on sites with SSO
- Monitor network requests in real-time

## Under the hood

Pure Python, zero dependencies for the CDP layer. Raw WebSocket frames (RFC 6455), no websocket-client library needed. Works with any agent that can call external tools -- Claude Code, Codex, Aider, you name it.

GitHub: [https://github.com/willingerror/cdp-agent-kit](https://github.com/willingerror/cdp-agent-kit)

Would love feedback -- especially from anyone who's hit the "new browser every time" problem with AI agents."""
SUB = "ClaudeAI"
FLAIR = "Other"
SIG = r"C:\Users\kwokk\Desktop\go.txt"

class WS:
    def __init__(self, url):
        rest = url.replace("ws://localhost:9222/", "")
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(10)
        self.sock.connect(("::1", 9222, 0, 0))
        key = base64.b64encode(random.randbytes(16)).decode()
        req = (f"GET /{rest} HTTP/1.1\r\nHost: localhost:9222\r\n"
               f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        if b"101" not in self.sock.recv(4096)[:30]:
            raise RuntimeError("WS fail")
        self._mid = 0

    def send(self, data):
        p = data.encode(); f = bytes([0x81]); l = len(p)
        if l <= 125:      f += bytes([0x80 | l])
        elif l <= 65535:  f += bytes([0x80 | 126]) + struct.pack("!H", l)
        else:             f += bytes([0x80 | 127]) + struct.pack("!Q", l)
        m = random.randbytes(4); f += m
        f += bytes(b ^ m[i % 4] for i, b in enumerate(p))
        self.sock.sendall(f)

    def recv(self):
        b1, b2 = self.sock.recv(1)[0], self.sock.recv(1)[0]
        l = b2 & 0x7F
        if l == 126:   l = struct.unpack("!H", self.sock.recv(2))[0]
        elif l == 127: l = struct.unpack("!Q", self.sock.recv(8))[0]
        d = bytearray()
        while len(d) < l:
            c = self.sock.recv(min(l - len(d), 65536))
            if not c: break
            d.extend(c)
        if (b1 & 0x0F) == 0x09:
            self.sock.sendall(bytes([0x8A, 0x00]))
            return self.recv()
        return bytes(d).decode()

    def close(self):
        try: self.sock.sendall(bytes([0x88, 0x00]))
        except: pass
        self.sock.close()

def get_tab():
    r = subprocess.run(["curl.exe", "-s", "http://localhost:9222/json"],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5)
    for t in json.loads(r.stdout):
        if t["type"] == "page" and "reddit.com" in t.get("url", "").lower():
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No Reddit tab")

def cmd(ws, m, p=None):
    ws._mid += 1; mid = ws._mid
    ws.send(json.dumps({"id": mid, "method": m, "params": p or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == mid: return msg.get("result", {})

def js(ws, c):
    return cmd(ws, "Runtime.evaluate",
               {"expression": c, "returnByValue": True, "awaitPromise": True}).get("result", {}).get("value")

def wait():
    with open(SIG, "w") as f: f.write("w")
    print("   [WAITING] Delete go.txt to continue...")
    while os.path.exists(SIG): time.sleep(1)

# ===== MAIN =====
print("=" * 50)
print("  CDP Reddit Poster")
print("=" * 50)

# 1. Connect
print("\n-- Step 1: Connect CDP --")
ws = WS(get_tab())
cmd(ws, "Runtime.enable"); cmd(ws, "Page.enable")
print("   OK")

# 2. Navigate
print(f"\n-- Step 2: Navigate to /r/{SUB}/submit --")
cmd(ws, "Page.navigate", {"url": f"https://old.reddit.com/r/{SUB}/submit"})
time.sleep(3)

# 3. Text mode
print("\n-- Step 3: Text mode --")
js(ws, """(function(){
    var t = document.querySelectorAll('.formtab a');
    for (var i=0;i<t.length;i++)
        if (t[i].textContent.trim().toLowerCase()==='text'){t[i].click();return;}
})()""")
time.sleep(0.5)
print("   OK")

# 4. CAPTCHA first
print("\n-- Step 4: CAPTCHA --")
print("   Solve in Chrome now!")
wait()
c = js(ws, "(function(){var r=document.querySelector('textarea[name=g-recaptcha-response]');return(r&&r.value.length>10)?'OK':'NO'})()")
if c != "OK":
    print("   Not solved! Try again.")
    wait()
print("   CAPTCHA OK")

# 5. Flair
print(f"\n-- Step 5: Flair '{FLAIR}' --")
js(ws, ("window.__F=null;fetch('/r/"+SUB+"/api/link_flair.json',{credentials:'include'})"
        ".then(r=>r.json()).then(d=>window.__F=JSON.stringify(d))"))
time.sleep(2)
uuid = None
try:
    for x in json.loads(str(js(ws, "window.__F||'[]'"))):
        t = re.sub(r':[a-zA-Z_]+\\d*:', '', (x.get("text") or "").strip()).strip()
        if t == FLAIR: uuid = x.get("id") or x.get("flair_template_id",""); break
except: pass
print(f"   UUID: {uuid}")

# 6. Fill
print("\n-- Step 6: Fill --")
js(ws, f"document.querySelector('textarea[name=title]').value={json.dumps(TITLE)}")
js(ws, f"document.querySelector('textarea[name=text]').value={json.dumps(BODY)}")
tl = js(ws, 'document.querySelector("textarea[name=title]").value.length')
bl = js(ws, 'document.querySelector("textarea[name=text]").value.length')
print(f"   Title: {tl} | Body: {bl}")

# 7. Set flair
print("\n-- Step 7: Set flair --")
if uuid:
    js(ws, f"document.querySelector('#flair-field input[name=flair_id]').value={json.dumps(uuid)};"+
           f"document.querySelector('#flair-field input[name=flair_text]').value={json.dumps(FLAIR)};"+
           f"document.querySelector('#flair-field .flair-preview').textContent={json.dumps(FLAIR)};")
    print(f"   Set: {FLAIR}")

# 8. Submit
print("\n-- Step 8: Submit --")
js(ws, """
window.__R='PENDING';
(function(){
    var f=document.querySelector('#newlink'),fd=new FormData(f),p=new URLSearchParams();
    for(var e of fd.entries())p.append(e[0],e[1]);
    fetch('/api/submit',{method:'POST',credentials:'include',
        headers:{'Content-Type':'application/x-www-form-urlencoded'},body:p.toString()})
    .then(r=>r.text()).then(t=>{window.__R=t});
})();
""")
time.sleep(4)
raw = str(js(ws, "window.__R||'PENDING'"))

# 9. Result
print("\n-- Step 9: Result --")
try:
    d = json.loads(raw)
    if d.get("success"):
        m = re.findall(r'"redirect"\].*?"(https:[^\"]+)"', str(d))
        if m:
            print(f"\n   POSTED: {m[0]}")
            cmd(ws, "Page.navigate", {"url": m[0]})
            time.sleep(3)
            ws.close()
            print("\nDone!")
            sys.exit(0)
    errs = set(re.findall(r'\.error\.([A-Z_]+)', str(d)))
    print(f"   Rejected: {errs}")
except Exception as e:
    print(f"   Error: {e}")

ws.close()
