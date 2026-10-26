"""Browser tools for OpsAgent - wraps Playwright for headless browser automation."""
import asyncio
import base64
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from opsagent.tools.registry import tool


class BrowserManager:
    """Manages a headless browser instance for the agent."""

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def ensure_browser(self):
        """Ensure browser is launched."""
        if not self._browser:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="OpsAgent/1.0"
            )
            self._page = await self._context.new_page()

    async def get_page(self) -> Page:
        await self.ensure_browser()
        return self._page

    async def close(self):
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# Global browser manager
_browser_mgr = BrowserManager()


@tool(
    name="browser_goto",
    description="Navigate the browser to a URL. Returns the page title and status.",
    risk="read",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to navigate to"}
        },
        "required": ["url"]
    }
)
async def browser_goto(url: str) -> dict:
    page = await _browser_mgr.get_page()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        status = response.status if response else 0
        title = await page.title()
        return {
            "success": True,
            "url": page.url,
            "title": title,
            "status_code": status,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "url": url}


@tool(
    name="browser_read_page",
    description="Read the current page content. Returns visible text content of the page, useful for extracting information. Optionally specify a CSS selector to read specific elements.",
    risk="read",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "Optional CSS selector to read specific elements. Leave empty for full page."}
        },
        "required": []
    }
)
async def browser_read_page(selector: str = "") -> dict:
    page = await _browser_mgr.get_page()
    try:
        if selector:
            elements = await page.query_selector_all(selector)
            texts = []
            for el in elements[:20]:  # Limit to 20 elements
                text = await el.inner_text()
                texts.append(text.strip())
            content = "\n".join(texts)
        else:
            content = await page.inner_text("body")

        # Truncate to avoid overwhelming the LLM
        if len(content) > 8000:
            content = content[:8000] + "\n... [content truncated]"

        return {
            "success": True,
            "url": page.url,
            "title": await page.title(),
            "content": content,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="browser_click",
    description="Click an element on the page. Specify either a CSS selector or text content to find the element.",
    risk="write",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector of the element to click (e.g. '#submit-btn', 'a[href=\"/login\"]')"},
            "text": {"type": "string", "description": "Text content to find and click (alternative to selector)"}
        },
        "required": []
    }
)
async def browser_click(selector: str = "", text: str = "") -> dict:
    page = await _browser_mgr.get_page()
    try:
        if text and not selector:
            # Find by text
            el = page.get_by_text(text, exact=False).first
            await el.click(timeout=10000)
        elif selector:
            await page.click(selector, timeout=10000)
        else:
            return {"success": False, "error": "Must provide either 'selector' or 'text'"}

        await page.wait_for_load_state("domcontentloaded", timeout=10000)
        return {
            "success": True,
            "url": page.url,
            "title": await page.title(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="browser_fill",
    description="Fill a form field with a value. Specify the field by CSS selector or label text.",
    risk="write",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector of the input field"},
            "value": {"type": "string", "description": "Value to fill in the field"},
            "label": {"type": "string", "description": "Label text to find the field (alternative to selector)"}
        },
        "required": ["value"]
    }
)
async def browser_fill(value: str, selector: str = "", label: str = "") -> dict:
    page = await _browser_mgr.get_page()
    try:
        if label and not selector:
            el = page.get_by_label(label)
            await el.fill(value, timeout=10000)
        elif selector:
            await page.fill(selector, value, timeout=10000)
        else:
            return {"success": False, "error": "Must provide either 'selector' or 'label'"}

        return {"success": True, "selector": selector or label, "value": value}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="browser_screenshot",
    description="Take a screenshot of the current page. Returns a base64-encoded PNG image path for evidence.",
    risk="read",
    parameters={
        "type": "object",
        "properties": {
            "full_page": {"type": "boolean", "description": "Whether to capture the full scrollable page"}
        },
        "required": []
    }
)
async def browser_screenshot(full_page: bool = False) -> dict:
    page = await _browser_mgr.get_page()
    try:
        screenshot_bytes = await page.screenshot(full_page=full_page)
        b64 = base64.b64encode(screenshot_bytes).decode()
        return {
            "success": True,
            "url": page.url,
            "title": await page.title(),
            "screenshot_base64": b64[:100] + "...",  # Truncated for LLM
            "screenshot_full_base64": b64,  # Full for evidence storage
            "size_bytes": len(screenshot_bytes),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def close_browser():
    """Close the browser - call on shutdown."""
    await _browser_mgr.close()
