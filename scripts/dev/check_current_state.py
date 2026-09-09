#!/usr/bin/env python3
"""Check current state of the app"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto('http://localhost:8502')
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    # Take screenshot
    page.screenshot(path='/tmp/current_state.png', full_page=True)
    print("Screenshot: /tmp/current_state.png")

    # Get content
    content = page.content()

    # Check step
    print("\n=== PAGE STATE ===")
    if 'Browse files' in content and 'Start Analysis' in content:
        print("❌ Still on UPLOAD page")
    elif 'Scene' in content or 'question' in content.lower():
        print("✅ On SCENARIO BUILDING page")
    elif 'Generate' in content:
        print("✅ On GENERATION page")
    else:
        print("❓ Unknown page")

    # Check for chat messages
    messages = page.locator('[data-testid="stChatMessage"]').all()
    print(f"\nChat messages: {len(messages)}")
    if messages:
        for i, msg in enumerate(messages[:3]):
            text = msg.inner_text()[:150]
            print(f"  Message {i+1}: {text}...")

    # Check for errors
    errors = page.locator('[data-testid="stException"]').all()
    if errors:
        print(f"\n⚠️ Errors found: {len(errors)}")
        for err in errors:
            print(f"  {err.inner_text()}")

    # Check for buttons
    buttons = page.locator('button').all()
    button_texts = []
    for btn in buttons[:10]:
        try:
            text = btn.inner_text(timeout=500)
            if text.strip():
                button_texts.append(text.strip())
        except:
            pass

    print(f"\nButtons: {button_texts}")

    browser.close()
