#!/usr/bin/env python3
"""Extract error message from Streamlit app"""

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Loading app...")
    page.goto('http://localhost:8502')
    page.wait_for_load_state('networkidle')
    time.sleep(3)

    # Get full page content
    content = page.content()

    # Look for error messages
    errors = page.locator('[data-testid="stException"]').all()
    if errors:
        print(f"\n🔴 Found {len(errors)} error(s):\n")
        for i, error in enumerate(errors):
            print(f"Error {i+1}:")
            print(error.inner_text())
            print("-" * 60)

    # Look for alert messages
    alerts = page.locator('.stAlert').all()
    if alerts:
        print(f"\n⚠️ Found {len(alerts)} alert(s):\n")
        for i, alert in enumerate(alerts):
            print(f"Alert {i+1}:")
            print(alert.inner_text())
            print("-" * 60)

    # Check step/stage
    if 'step' in content:
        print("\n📍 Current step/stage info:")
        if 'upload' in content.lower():
            print("  - On upload page")
        if 'chat' in content.lower():
            print("  - On chat page")

    browser.close()
