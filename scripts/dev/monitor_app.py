#!/usr/bin/env python3
"""Monitor Streamlit app with Playwright - continuous monitoring"""

from playwright.sync_api import sync_playwright
import time
import sys

def monitor_app():
    """Continuously monitor the app and report state changes"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("🔍 Starting monitoring...")
        print("📍 URL: http://localhost:8502")
        print("-" * 60)

        page.goto('http://localhost:8502')
        page.wait_for_load_state('networkidle')
        time.sleep(2)

        last_state = None
        screenshot_count = 0

        while True:
            try:
                # Take screenshot
                screenshot_count += 1
                screenshot_path = f'/tmp/monitor_{screenshot_count}.png'
                page.screenshot(path=screenshot_path)

                # Get current state
                content = page.content()

                # Detect step
                current_step = "unknown"
                if 'Upload PDF' in content or 'Browse files' in content:
                    if 'Start Analysis' in content:
                        current_step = "upload"
                    else:
                        current_step = "upload_incomplete"
                elif 'Scene' in content and 'question' in content.lower():
                    current_step = "scenario_building"
                elif 'Generate' in content:
                    current_step = "ready_to_generate"
                elif 'Download' in content and 'HTML' in content:
                    current_step = "completed"

                # Count buttons
                buttons = page.locator('button').all()
                button_texts = []
                for btn in buttons[:10]:
                    try:
                        text = btn.inner_text(timeout=500)
                        if text.strip():
                            button_texts.append(text.strip())
                    except:
                        pass

                # Check for errors
                errors = page.locator('[data-testid="stException"]').all()
                alerts = page.locator('.stAlert').all()

                # Check for chat messages
                messages = page.locator('[data-testid="stChatMessage"]').all()

                # Build state summary
                state = {
                    'step': current_step,
                    'buttons': len(button_texts),
                    'errors': len(errors),
                    'alerts': len(alerts),
                    'messages': len(messages)
                }

                # Report if state changed
                if state != last_state:
                    timestamp = time.strftime('%H:%M:%S')
                    print(f"\n[{timestamp}] 🔄 STATE CHANGE:")
                    print(f"  Step: {state['step']}")
                    print(f"  Buttons: {state['buttons']} - {button_texts[:5]}")
                    print(f"  Messages: {state['messages']}")
                    if state['errors'] > 0:
                        print(f"  ⚠️ Errors: {state['errors']}")
                        for err in errors:
                            print(f"    - {err.inner_text()[:100]}")
                    if state['alerts'] > 0:
                        print(f"  📢 Alerts: {state['alerts']}")
                    print(f"  Screenshot: {screenshot_path}")
                    print("-" * 60)

                    last_state = state.copy()

                # Wait before next check
                time.sleep(2)

            except KeyboardInterrupt:
                print("\n\n✋ Monitoring stopped by user")
                break
            except Exception as e:
                print(f"\n⚠️ Error during monitoring: {e}")
                time.sleep(2)
                # Try to reload
                try:
                    page.reload()
                    page.wait_for_load_state('networkidle')
                except:
                    pass

        browser.close()
        print("\n👋 Monitoring ended")

if __name__ == "__main__":
    try:
        monitor_app()
    except KeyboardInterrupt:
        print("\n\n✋ Stopped")
        sys.exit(0)
