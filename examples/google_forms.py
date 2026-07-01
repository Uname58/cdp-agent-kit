"""
Google Forms auto-fill demo — the first real-world test of cdp-agent-kit.

Flow:
    1. User opens a Google Form in Chrome (already logged in)
    2. Agent connects via CDP, reads the form fields
    3. Agent fills all fields and submits

Usage:
    1. Start Chrome:  ./scripts/start_chrome.sh
    2. Open a Google Form in Chrome
    3. Run:          python examples/google_forms.py --form-url "https://forms.gle/..."
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cdp_agent_kit import CDPBridge


async def analyze_form(bridge: CDPBridge) -> dict:
    """Analyze the Google Form structure and return all fields found."""
    await asyncio.sleep(2)  # Wait for form to fully render

    # Get interactive elements
    elements = await bridge.get_interactive_elements()
    snapshot = await bridge.get_snapshot()

    fields = {
        "text_inputs": [],
        "textareas": [],
        "radios": [],
        "checkboxes": [],
        "selects": [],
        "submit_button": None,
    }

    for el in elements:
        if el.tag == "input":
            t = el.attributes.get("type", "text")
            name = el.attributes.get("name", "")
            placeholder = el.attributes.get("placeholder", "")

            if t in ("text", "email", "number", "url", "tel"):
                fields["text_inputs"].append({
                    "label": el.text or placeholder or name,
                    "name": name,
                    "type": t,
                })
            elif t == "radio":
                fields["radios"].append({
                    "label": el.text,
                    "name": name,
                })
            elif t == "checkbox":
                fields["checkboxes"].append({
                    "label": el.text,
                    "name": name,
                })

        elif el.tag == "textarea":
            fields["textareas"].append({
                "label": el.text or el.attributes.get("name", ""),
                "name": el.attributes.get("name", ""),
            })

        elif el.tag == "select":
            fields["selects"].append({
                "label": el.text,
                "name": el.attributes.get("name", ""),
            })

        # Detect submit button
        if ("submit" in (el.text + el.attributes.get("type", "")).lower()
                or "提交" in el.text
                or "next" in el.text.lower()):
            fields["submit_button"] = el.selector or "div[role='button']"

    return fields


async def fill_form(bridge: CDPBridge, data: dict[str, str]) -> bool:
    """
    Fill form fields using best-guess selectors.
    `data` is a mapping of label_text → value.
    """
    elements = await bridge.get_interactive_elements()

    for el in elements:
        label = (el.text or "").strip().lower()
        input_name = (el.attributes.get("name", "") or "").lower()
        placeholder = (el.attributes.get("placeholder", "") or "").lower()

        # Build a composite key for matching
        composite = f"{label} {input_name} {placeholder}"

        for key, value in data.items():
            if key.lower() in composite or key.lower() == label:
                t = el.attributes.get("type", "text")

                if t in ("text", "email", "number", "url", "tel"):
                    await bridge.type_text(el.selector or f"input[name='{el.attributes.get('name', '')}']", value)
                    print(f"  ✓ Filled '{label}' → '{value}'")
                    break

                elif el.tag == "textarea":
                    await bridge.type_text(
                        el.selector or f"textarea[name='{el.attributes.get('name', '')}']",
                        value,
                    )
                    print(f"  ✓ Filled textarea '{label}' → '{value}'")
                    break

    return True


async def main():
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSf-demo/viewform"
    if len(sys.argv) > 1:
        form_url = sys.argv[1]

    # Dummy data — replace with real data or pass via CLI
    form_data = {
        "email": "demo@example.com",
        "name": "Test User",
        "feedback": "cdp-agent-kit works perfectly!",
    }

    print(f"╔══════════════════════════════════╗")
    print(f"║   CDP Agent Kit — Google Forms  ║")
    print(f"╚══════════════════════════════════╝")
    print(f"\nConnecting to Chrome (localhost:9222)...")

    async with CDPBridge() as bridge:
        pages = await bridge.list_pages()
        print(f"Found {len(pages)} open tabs")

        # Navigate to the form
        print(f"\nNavigating to: {form_url}")
        await bridge.navigate(form_url)
        await asyncio.sleep(3)

        # Analyze form structure
        print("\nAnalyzing form fields...")
        fields = await analyze_form(bridge)

        print("\nDetected fields:")
        print(f"  Text inputs:  {len(fields['text_inputs'])}")
        print(f"  Textareas:    {len(fields['textareas'])}")
        print(f"  Radio groups: {len(fields['radios'])}")
        print(f"  Checkboxes:   {len(fields['checkboxes'])}")
        print(f"  Dropdowns:    {len(fields['selects'])}")
        if fields["submit_button"]:
            print(f"  Submit:       {fields['submit_button']}")

        # Fill the form
        print("\nFilling form...")
        await fill_form(bridge, form_data)

        # Take confirmation screenshot
        screenshot_path = "/tmp/google_form_filled.png"
        await bridge.screenshot(path=screenshot_path)
        print(f"\nScreenshot saved: {screenshot_path}")

        print("\n✅ Demo complete!")
        print("   Review the form and press Submit manually, or use:")
        btn = fields['submit_button'] or "div[role='button']"
        print(f"   bridge.click('{btn}')")


if __name__ == "__main__":
    asyncio.run(main())
