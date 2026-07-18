' ============================================================
' cdp-agent-kit — Chrome CDP Standard Launcher (WSL2 NAT Mode)
' ============================================================
' Purpose:  Start Chrome with remote debugging from WSL2
' Platform: Windows 11 + WSL2 (NAT networking)
' WSL IP:   Gateway = 172.27.64.1 (auto-detect on WSL side)
' 
' USAGE:    Double-click this file (auto-elevates via UAC)
'           After "Done" popup, from WSL:
'             curl http://172.27.64.1:9222/json
'
' ⚠️  CRITICAL ORDER — DO NOT CHANGE:
'   ① Kill all existing Chrome instances
'   ② Delete any stale portproxy rule (free port 9222)
'   ③ Start Chrome FIRST (so it binds 127.0.0.1:9222 cleanly)
'   ④ ADD portproxy AFTER Chrome is running (0.0.0.0→127.0.0.1)
'   ⑤ Ensure firewall rule exists
'
'   Wrong order = Chrome can't bind IPv4 = WSL unreachable
' ============================================================

' --- Auto-elevate if not already running as admin ---
If Not WScript.Arguments.Named.Exists("elevated") Then
    CreateObject("Shell.Application").ShellExecute _
        "wscript.exe", """" & WScript.ScriptFullName & """ /elevated", "", "runas", 1
    WScript.Quit
End If

Dim WshShell, chrome, chromePath
Set WshShell = CreateObject("WScript.Shell")

' ============================================
' Step ①: Kill all existing Chrome processes
' ============================================
WshShell.Run "taskkill /f /im chrome.exe >nul 2>&1", 0, True
WScript.Sleep 2000

' ======================================================
' Step ②: Delete stale portproxy rule (free port 9222)
' ======================================================
WshShell.Run "netsh interface portproxy delete v4tov4 listenport=9222 listenaddress=0.0.0.0 >nul 2>&1", 0, True
WScript.Sleep 500

' ====================================================
' Step ③: Start Chrome FIRST (clean bind to 127.0.0.1)
' ====================================================
chromePath = WshShell.ExpandEnvironmentStrings("%ProgramFiles%") & "\Google\Chrome\Application\chrome.exe"
WshShell.Run """" & chromePath & """ " & _
    "--remote-debugging-port=9222 " & _
    "--remote-debugging-address=0.0.0.0 " & _
    "--user-data-dir=" & WshShell.ExpandEnvironmentStrings("%TEMP%") & "\cdp-chrome", _
    1, False
WScript.Sleep 4000   ' Wait for Chrome to fully start

' ==============================================
' Step ④: Add portproxy (AFTER Chrome is running)
' ==============================================
WshShell.Run "netsh interface portproxy add v4tov4 listenport=9222 listenaddress=0.0.0.0 connectport=9222 connectaddress=127.0.0.1", 0, True

' ======================================
' Step ⑤: Ensure firewall rule exists
' ======================================
WshShell.Run "netsh advfirewall firewall add rule name=""CDP_9222"" dir=in action=allow protocol=TCP localport=9222 >nul 2>&1", 0, True

MsgBox "Chrome CDP is ready!" & vbCrLf & vbCrLf & _
       "From WSL, run:" & vbCrLf & _
       "  curl http://172.27.64.1:9222/json", _
       64, "CDP Ready"
