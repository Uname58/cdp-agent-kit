"""
Core CDP Bridge — connect to a user's Chrome instance and control it.

Usage:
    async with CDPBridge() as bridge:
        page = await bridge.get_page()
        await bridge.click("button.submit")
        await bridge.type("input[name='email']", "user@example.com")
        img = await bridge.screenshot()
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page


@dataclass
class ElementSnapshot:
    """A lightweight representation of an interactive element."""
    tag: str
    text: str = ""
    role: str = ""
    selector: str = ""
    visible: bool = True
    attributes: dict = field(default_factory=dict)


class CDPBridge:
    """
    Connects to an existing Chrome instance via CDP.

    The user must launch Chrome with:
        chrome --remote-debugging-port=9222
    """

    def __init__(self, cdp_url: str = "http://localhost:9222"):
        self.cdp_url = cdp_url
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._connected = False

    async def __aenter__(self) -> "CDPBridge":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(self.cdp_url)
        self._connected = True
        return self

    async def __aexit__(self, *args):
        self._connected = False
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    # ── page management ──────────────────────────────────

    async def list_pages(self) -> list[dict]:
        """List all open tabs with url and title."""
        pages = []
        for ctx in self._browser.contexts:
            for page in ctx.pages:
                try:
                    title = await page.title()
                    url = page.url
                except Exception:
                    title, url = "(closed)", ""
                pages.append({"title": title, "url": url})
        return pages

    async def get_page(self, index: int = 0) -> Page:
        """Get a page by index (default: first tab)."""
        pages = []
        for ctx in self._browser.contexts:
            pages.extend(ctx.pages)
        if not pages:
            raise RuntimeError("No open pages. Open at least one tab in Chrome.")
        if index >= len(pages):
            raise IndexError(f"Page index {index} out of range ({len(pages)} pages)")
        return pages[index]

    async def new_page(self, url: str = "about:blank") -> Page:
        """Open a new tab and navigate to url."""
        ctx = self._browser.contexts[0]
        page = await ctx.new_page()
        if url != "about:blank":
            await page.goto(url)
        return page

    # ── navigation ───────────────────────────────────────

    async def navigate(self, url: str, page_index: int = 0) -> Page:
        """Navigate a page to url."""
        page = await self.get_page(page_index)
        await page.goto(url, wait_until="domcontentloaded")
        return page

    # ── screenshots ──────────────────────────────────────

    async def screenshot(self, page_index: int = 0, path: Optional[str] = None) -> bytes:
        """Take a full-page screenshot. Returns PNG bytes."""
        page = await self.get_page(page_index)
        data = await page.screenshot(full_page=False, path=path)
        return data

    async def screenshot_b64(self, page_index: int = 0) -> str:
        """Take a screenshot and return as base64 string (for vision models)."""
        data = await self.screenshot(page_index)
        return base64.b64encode(data).decode("utf-8")

    # ── DOM interaction ──────────────────────────────────

    async def get_snapshot(self, page_index: int = 0) -> str:
        """
        Get accessibility tree snapshot — gives agent structured understanding
        of the page (buttons, inputs, links with labels and refs).
        """
        page = await self.get_page(page_index)
        snapshot = await page.accessibility.snapshot()
        return self._flatten_snapshot(snapshot)

    async def get_page_text(self, page_index: int = 0) -> str:
        """Extract all visible text from the page."""
        page = await self.get_page(page_index)
        return await page.evaluate("""() => document.body.innerText""")

    async def get_interactive_elements(self, page_index: int = 0) -> list[ElementSnapshot]:
        """Get all clickable/fillable elements with selectors."""
        page = await self.get_page(page_index)
        elements = await page.evaluate("""() => {
            const results = [];
            const interactives = document.querySelectorAll(
                'a, button, input, select, textarea, [role="button"], [role="checkbox"], [role="link"], [role="menuitem"], [role="tab"], [onclick]'
            );
            interactives.forEach((el, i) => {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return;
                const label = el.getAttribute('aria-label') || el.textContent?.trim().slice(0, 100) || '';
                results.push({
                    tag: el.tagName.toLowerCase(),
                    text: label,
                    role: el.getAttribute('role') || '',
                    selector: el.id ? '#' + el.id : el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase(),
                    visible: rect.top < window.innerHeight && rect.bottom > 0,
                    attributes: {
                        type: el.getAttribute('type') || '',
                        name: el.getAttribute('name') || '',
                        placeholder: el.getAttribute('placeholder') || '',
                        href: el.getAttribute('href') || '',
                    }
                });
            });
            return results;
        }""")
        return [ElementSnapshot(**e) for e in elements]

    # ── actions ──────────────────────────────────────────

    async def click(self, selector: str, page_index: int = 0) -> bool:
        """Click an element by CSS selector. Returns True if successful."""
        page = await self.get_page(page_index)
        try:
            await page.click(selector, timeout=5000)
            return True
        except Exception:
            return False

    async def type_text(self, selector: str, text: str, page_index: int = 0, clear: bool = True) -> bool:
        """Type text into an input field."""
        page = await self.get_page(page_index)
        try:
            if clear:
                await page.fill(selector, text, timeout=5000)
            else:
                await page.type(selector, text, timeout=5000)
            return True
        except Exception:
            return False

    async def select_option(self, selector: str, value: str, page_index: int = 0) -> bool:
        """Select an option from a <select> element."""
        page = await self.get_page(page_index)
        try:
            await page.select_option(selector, value, timeout=5000)
            return True
        except Exception:
            return False

    async def press_key(self, key: str, page_index: int = 0):
        """Press a keyboard key (e.g. 'Enter', 'Tab', 'Escape')."""
        page = await self.get_page(page_index)
        await page.keyboard.press(key)

    async def scroll(self, direction: str = "down", amount: int = 500, page_index: int = 0):
        """Scroll the page."""
        page = await self.get_page(page_index)
        delta = amount if direction == "down" else -amount
        await page.evaluate(f"window.scrollBy(0, {delta})")

    async def execute_js(self, code: str, page_index: int = 0) -> str:
        """Execute arbitrary JavaScript in the page context."""
        page = await self.get_page(page_index)
        result = await page.evaluate(code)
        return str(result) if result is not None else ""

    # ── helpers ──────────────────────────────────────────

    def _flatten_snapshot(self, node: dict | None, depth: int = 0) -> str:
        """Flatten accessibility tree to readable text."""
        if node is None:
            return ""
        lines = []
        indent = "  " * depth
        role = node.get("role", "unknown")
        name = node.get("name", "")
        value = node.get("value", "")
        line = f"{indent}[{role}]"
        if name:
            line += f" '{name}'"
        if value:
            line += f" = {value}"
        lines.append(line)
        for child in node.get("children", []):
            if isinstance(child, dict):
                lines.append(self._flatten_snapshot(child, depth + 1))
        return "\n".join(lines)
