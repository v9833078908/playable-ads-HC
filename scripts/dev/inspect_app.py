#!/usr/bin/env python3
"""Inspect the Streamlit app state"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Loading app...")
    page.goto('http://localhost:8502')
    page.wait_for_load_state('networkidle')
    time.sleep(3)  # Wait for Streamlit to fully render

    # Take screenshot
    screenshot_path = '/tmp/streamlit_state.png'
    page.screenshot(path=screenshot_path, full_page=True)
    print(f"Screenshot saved to: {screenshot_path}")

    # Get page title
    title = page.title()
    print(f"Page title: {title}")

    # Check for main content
    content = page.content()

    # Look for key elements
    if 'Snail Bob' in content:
        print("✓ Found 'Snail Bob' in page")

    if 'Scene' in content or 'scene' in content:
        print("✓ Found 'Scene' in page")

    # Check for buttons
    buttons = page.locator('button').all()
    print(f"\nFound {len(buttons)} buttons:")
    for i, btn in enumerate(buttons[:10]):
        try:
            text = btn.inner_text(timeout=1000)
            if text.strip():
                print(f"  {i+1}. {text.strip()}")
        except:
            pass

    # Check for any error messages
    if 'Error' in content or 'error' in content:
        print("\n⚠️ Found 'Error' in page")

    # Check for messages/chat
    messages = page.locator('[data-testid="stChatMessage"]').all()
    if messages:
        print(f"\n✓ Found {len(messages)} chat messages")

    browser.close()
    print("\nDone! Check screenshot at /tmp/streamlit_state.png")
