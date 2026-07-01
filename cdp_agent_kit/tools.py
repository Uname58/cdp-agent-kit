"""
Agent tool definitions — formatted for LLM function calling (OpenAI / Claude / Hermes).

An LLM receives these as available tools, and calls them via the bridge.
"""

from typing import Any
from cdp_agent_kit.bridge import CDPBridge

# ── Tool schemas for LLM function calling ──────────────────

TOOL_SCHEMAS = [
    {
        "name": "browser_navigate",
        "description": "Navigate a browser tab to a URL.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL to navigate to."},
                "page_index": {"type": "integer", "default": 0, "description": "Tab index."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "browser_snapshot",
        "description": "Get the accessibility tree of the current page — a structured view of all interactive elements with labels.",
        "parameters": {
            "type": "object",
            "properties": {
                "page_index": {"type": "integer", "default": 0},
            },
        },
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current page. Returns a description of what's visible (for vision models).",
        "parameters": {
            "type": "object",
            "properties": {
                "page_index": {"type": "integer", "default": 0},
            },
        },
    },
    {
        "name": "browser_click",
        "description": "Click an element identified by CSS selector.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the element to click."},
                "page_index": {"type": "integer", "default": 0},
            },
            "required": ["selector"],
        },
    },
    {
        "name": "browser_type",
        "description": "Type text into an input field.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the input field."},
                "text": {"type": "string", "description": "Text to type."},
                "page_index": {"type": "integer", "default": 0},
            },
            "required": ["selector", "text"],
        },
    },
    {
        "name": "browser_select",
        "description": "Select an option from a dropdown (<select> element).",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of the <select> element."},
                "value": {"type": "string", "description": "The value to select."},
                "page_index": {"type": "integer", "default": 0},
            },
            "required": ["selector", "value"],
        },
    },
    {
        "name": "browser_press_key",
        "description": "Press a keyboard key (Enter, Tab, Escape, etc.) on the page.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key to press (e.g., 'Enter', 'Tab')."},
                "page_index": {"type": "integer", "default": 0},
            },
            "required": ["key"],
        },
    },
    {
        "name": "browser_list_pages",
        "description": "List all open browser tabs with their URLs and titles.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "browser_get_text",
        "description": "Extract all visible text content from the page.",
        "parameters": {
            "type": "object",
            "properties": {
                "page_index": {"type": "integer", "default": 0},
            },
        },
    },
    {
        "name": "browser_exec_js",
        "description": "Execute JavaScript in the page context and return the result.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "JavaScript code to execute."},
                "page_index": {"type": "integer", "default": 0},
            },
            "required": ["code"],
        },
    },
]


# ── Tool executor ──────────────────────────────────────────

class ToolExecutor:
    """Routes LLM function calls to CDPBridge methods."""

    def __init__(self, bridge: CDPBridge):
        self.bridge = bridge

    async def execute(self, name: str, args: dict) -> Any:
        page_index = args.get("page_index", 0)

        if name == "browser_navigate":
            await self.bridge.navigate(args["url"], page_index)
            return f"Navigated to {args['url']}"

        elif name == "browser_snapshot":
            return await self.bridge.get_snapshot(page_index)

        elif name == "browser_screenshot":
            b64 = await self.bridge.screenshot_b64(page_index)
            return {"type": "image", "data": b64}

        elif name == "browser_click":
            ok = await self.bridge.click(args["selector"], page_index)
            return f"Click {'OK' if ok else 'FAILED'} on {args['selector']}"

        elif name == "browser_type":
            ok = await self.bridge.type_text(args["selector"], args["text"], page_index)
            return f"Type {'OK' if ok else 'FAILED'} into {args['selector']}"

        elif name == "browser_select":
            ok = await self.bridge.select_option(args["selector"], args["value"], page_index)
            return f"Select {'OK' if ok else 'FAILED'} on {args['selector']}"

        elif name == "browser_press_key":
            await self.bridge.press_key(args["key"], page_index)
            return f"Pressed {args['key']}"

        elif name == "browser_list_pages":
            pages = await self.bridge.list_pages()
            return "\n".join(f"[{i}] {p['title'][:60]} — {p['url'][:80]}" for i, p in enumerate(pages))

        elif name == "browser_get_text":
            return await self.bridge.get_page_text(page_index)

        elif name == "browser_exec_js":
            return await self.bridge.execute_js(args["code"], page_index)

        else:
            return f"Unknown tool: {name}"
