"""
ALAS Web Browsing Agent — Playwright integration for dynamic web interaction (Phase 4).

Allows ALAS to navigate dynamic websites, click buttons, fill forms, and extract text.
Maintains session state via cookies/storage across tool calls.
"""
import os
import logging
from typing import Optional
from pathlib import Path

from backend.app.config import get_settings

logger = logging.getLogger("alas.tools.browser")

def get_state_path() -> str:
    """Get the path to store browser session state (cookies/local storage)."""
    settings = get_settings()
    data_dir = Path(settings.chroma_persist_dir).parent / "browser"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "state.json")

def execute_browser_action(url: str, action: str, selector: str = "", text: str = "") -> str:
    """
    Execute a browser action using Playwright.
    Because the browser closes between calls, ALWAYS provide the URL so it can navigate there first.
    
    Args:
        url: The full URL to act upon.
        action: 'navigate', 'click', 'fill', 'extract'.
        selector: CSS selector for click/fill.
        text: Text to fill in a form.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "Error: Playwright is not installed. Run: pip install playwright && playwright install chromium"

    state_path = get_state_path()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # Load state if exists to maintain sessions/logins
            if os.path.exists(state_path):
                context = browser.new_context(
                    storage_state=state_path,
                    viewport={'width': 1280, 'height': 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ALASBot/1.0"
                )
            else:
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ALASBot/1.0"
                )
                
            page = context.new_page()
            
            # 1. Always navigate to the requested URL first to restore context
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
            except Exception as e:
                logger.warning(f"Timeout or error navigating to {url}: {e}")
                
            result = ""
            
            # 2. Perform the requested action
            if action == "navigate":
                title = page.title()
                content = page.evaluate("document.body.innerText")
                snippet = content[:800].replace('\n', ' ')
                result = f"Navigated to {url}.\nTitle: {title}\nContent snippet:\n{snippet}..."
                
            elif action == "click":
                if not selector:
                    return "Error: selector is required for click action."
                page.click(selector, timeout=5000)
                # Wait a moment for dynamic content or navigation
                page.wait_for_timeout(2000)
                new_url = page.url
                result = f"Clicked '{selector}'.\nCurrent URL is now: {new_url}"
                
            elif action == "fill":
                if not selector:
                    return "Error: selector is required for fill action."
                page.fill(selector, text, timeout=5000)
                result = f"Filled '{selector}' with provided text."
                
            elif action == "extract":
                content = page.evaluate("document.body.innerText")
                result = content[:4000] if len(content) > 4000 else content
                
            else:
                result = f"Unknown browser action: {action}"
                
            # Save state for the next call
            context.storage_state(path=state_path)
            browser.close()
            
            return result
            
    except Exception as e:
        logger.error(f"Browser agent error: {e}", exc_info=True)
        return f"Browser action '{action}' failed: {e}"
