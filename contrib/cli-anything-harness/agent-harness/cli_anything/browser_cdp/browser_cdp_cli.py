#!/usr/bin/env python3
"""Browser CDP CLI — Chrome DevTools Protocol browser automation via CLI-Anything.

Connects to YOUR existing Chrome (no new browser, no extensions).
All commands support --json flag for agent-friendly output.

Usage:
    cli-anything-browser-cdp page open https://github.com
    cli-anything-browser-cdp page snapshot
    cli-anything-browser-cdp act click "button.submit"
    cli-anything-browser-cdp --json util screenshot
    cli-anything-browser-cdp --cdp ws://172.27.64.1:9222 page open https://example.com
"""

import sys
import json
import click
from typing import Optional

from .core import CDPSession, CDPBackend

# ─── Global State ───
_session: Optional[CDPSession] = None
_backend: Optional[CDPBackend] = None
_json_mode = False


def get_backend() -> CDPBackend:
    global _session, _backend
    if _session is None:
        _session = CDPSession()
    if _backend is None:
        _backend = CDPBackend(_session)
    return _backend


def output(data, ok: bool = True):
    """Print output in JSON or human-readable format."""
    if _json_mode:
        if isinstance(data, str):
            click.echo(json.dumps({"result": data}))
        elif isinstance(data, dict):
            click.echo(json.dumps(data, indent=2, default=str, ensure_ascii=False))
        else:
            click.echo(json.dumps({"result": str(data)}, ensure_ascii=False))
    else:
        if isinstance(data, dict):
            for k, v in data.items():
                if k not in ("status", "clicked", "typed", "pressed", "selected", "waited_ms"):
                    if isinstance(v, str) and "\n" in v:
                        click.echo(f"{k}:")
                        click.echo(v[:1000])
                    else:
                        click.echo(f"{k}: {v}")
        elif isinstance(data, list):
            for item in data:
                click.echo(str(item))
        else:
            click.echo(str(data))


def handle_errors(func):
    """Decorator to catch and format errors."""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except RuntimeError as e:
            msg = {"error": str(e)} if _json_mode else f"Error: {e}"
            if _json_mode:
                click.echo(json.dumps(msg))
            else:
                click.echo(f"❌ Error: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            msg = {"error": str(e)} if _json_mode else f"Error: {e}"
            if _json_mode:
                click.echo(json.dumps(msg))
            else:
                click.echo(f"❌ Error: {e}", err=True)
            sys.exit(1)
    wrapper.__name__ = func.__name__
    return wrapper


# ─── CLI Entry Point ───

@click.group()
@click.option("--json", "_json", is_flag=True, help="Output in JSON format for agents")
@click.option("--cdp", "cdp_url", default="http://localhost:9222",
              help="Chrome CDP endpoint (default: http://localhost:9222)")
@click.pass_context
def main(ctx, _json, cdp_url):
    """Browser CDP — Chrome automation via DevTools Protocol.
    
    Connects to YOUR existing Chrome. No new browser, no extensions.
    """
    global _json_mode, _session
    _json_mode = _json
    if _session is None:
        _session = CDPSession(cdp_url=cdp_url)
    else:
        _session.cdp_url = cdp_url


# ─── page Group ───

@main.group()
def page():
    """Page navigation commands."""
    pass


@page.command("open")
@click.argument("url")
@handle_errors
def page_open(url):
    """Navigate to a URL."""
    backend = get_backend()
    result = backend.navigate(url)
    output(result)


@page.command("reload")
@handle_errors
def page_reload():
    """Reload current page."""
    result = get_backend().reload()
    output(result)


@page.command("back")
@handle_errors
def page_back():
    """Go back in history."""
    result = get_backend().back()
    output(result)


@page.command("forward")
@handle_errors
def page_forward():
    """Go forward in history."""
    result = get_backend().forward()
    output(result)


@page.command("title")
@handle_errors
def page_title():
    """Get current page title."""
    result = get_backend().get_title()
    output(result)


@page.command("url")
@handle_errors
def page_url():
    """Get current URL."""
    result = get_backend().get_url()
    output(result)


@page.command("snapshot")
@handle_errors
def page_snapshot():
    """Get DOM snapshot of current page."""
    result = get_backend().snapshot()
    output(result)


# ─── act Group ───

@main.group()
def act():
    """Page interaction commands."""
    pass


@act.command("click")
@click.argument("selector")
@handle_errors
def act_click(selector):
    """Click an element by CSS selector or text content."""
    result = get_backend().click(selector)
    output(result)


@act.command("type")
@click.argument("selector")
@click.argument("text")
@handle_errors
def act_type(selector, text):
    """Type text into an input field."""
    result = get_backend().type_text(selector, text)
    output(result)


@act.command("press")
@click.argument("key")
@handle_errors
def act_press(key):
    """Press a keyboard key."""
    result = get_backend().press_key(key)
    output(result)


@act.command("eval")
@click.argument("code")
@handle_errors
def act_eval(code):
    """Execute JavaScript in the page."""
    result = get_backend().eval_js(code)
    output(result)


@act.command("select")
@click.argument("selector")
@click.argument("value")
@handle_errors
def act_select(selector, value):
    """Select a dropdown option."""
    result = get_backend().select_option(selector, value)
    output(result)


# ─── util Group ───

@main.group()
def util():
    """Utility commands."""
    pass


@util.command("screenshot")
@click.argument("path", required=False, default=None)
@handle_errors
def util_screenshot(path):
    """Take a screenshot. Saves to path or auto-named file."""
    result = get_backend().screenshot(path)
    output(result)


@util.command("list-pages")
@handle_errors
def util_list_pages():
    """List all open Chrome tabs."""
    result = get_backend().list_pages()
    output(result)


@util.command("text")
@click.argument("selector", required=False, default=None)
@handle_errors
def util_text(selector):
    """Extract text from page or element."""
    result = get_backend().extract_text(selector)
    output(result)


@util.command("wait")
@click.argument("ms", type=int)
@handle_errors
def util_wait(ms):
    """Wait for N milliseconds."""
    result = get_backend().wait(ms)
    output(result)


# ─── daemon Group ───

@main.group()
def daemon():
    """Persistent connection management."""
    pass


@daemon.command("start")
@handle_errors
def daemon_start():
    """Start persistent CDP session."""
    session = _session or CDPSession()
    session.daemon_mode = True
    output({"daemon": "started", "cdp_url": session.cdp_url})


@daemon.command("stop")
@handle_errors
def daemon_stop():
    """Stop persistent CDP session."""
    if _session:
        _session.daemon_mode = False
    output({"daemon": "stopped"})


@daemon.command("status")
@handle_errors
def daemon_status():
    """Check daemon status."""
    session = _session or CDPSession()
    output({
        "daemon_mode": session.daemon_mode,
        "current_url": session.current_url,
        "cdp_url": session.cdp_url,
    })


if __name__ == "__main__":
    main()
