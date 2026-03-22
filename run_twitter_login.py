"""One-shot local Twitter login via Camoufox. Run from local machine (not server)."""

import json
import sys
import time
from pathlib import Path

from camoufox.sync_api import NewBrowser
from playwright.sync_api import sync_playwright

# Load credentials from .env
from config import settings

COOKIES_FILE = Path(settings.twitter_cookies_file)


def main() -> None:
    if not settings.twitter_username or not settings.twitter_password:
        print("ERROR: TWITTER_USERNAME and TWITTER_PASSWORD must be set in .env")
        sys.exit(1)

    print(f"Logging in as @{settings.twitter_username}...")

    with sync_playwright() as pw:
        browser = NewBrowser(pw, headless="virtual", humanize=True, os="linux")
        try:
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()

            print("Loading login page...")
            page.goto(
                "https://x.com/i/flow/login", wait_until="networkidle", timeout=60000
            )
            time.sleep(3)

            page.screenshot(path="data/twitter_debug_1_loaded.png")
            print(f"  URL: {page.url}")
            print(f"  Title: {page.title()}")

            # Username
            print("Entering username...")
            username_input = page.locator('input[autocomplete="username"]')
            username_input.wait_for(state="visible", timeout=30000)
            username_input.fill(settings.twitter_username)
            # Click "Next" button instead of Enter
            next_btn = page.locator(
                'button:has-text("Next"), [role="button"]:has-text("Next")'
            )
            if next_btn.is_visible():
                next_btn.click()
            else:
                page.keyboard.press("Enter")
            time.sleep(3)

            page.screenshot(path="data/twitter_debug_1b_after_username.png")
            print(f"  After username URL: {page.url}")

            # Email/phone verification (Twitter may ask for this)
            try:
                # Try multiple selectors for the verification input
                verify_input = page.locator(
                    'input[data-testid="ocfEnterTextTextInput"], '
                    'input[name="text"], '
                    'input[autocomplete="on"]'
                )
                verify_input.wait_for(state="visible", timeout=5000)
                if verify_input.is_visible():
                    print("Entering email verification...")
                    verify_input.fill(settings.twitter_email)
                    page.keyboard.press("Enter")
                    time.sleep(3)
                    page.screenshot(path="data/twitter_debug_1c_after_email.png")
            except Exception:
                print("  (no email step)")

            # Password
            print("Entering password...")
            password_input = page.locator('input[type="password"]')
            password_input.wait_for(state="visible", timeout=20000)
            password_input.fill(settings.twitter_password)
            page.keyboard.press("Enter")
            time.sleep(5)

            page.screenshot(path="data/twitter_debug_2_after_login.png")
            print(f"  After login URL: {page.url}")

            # Extract cookies
            browser_cookies = context.cookies("https://x.com")
            cookies = {c["name"]: c["value"] for c in browser_cookies}

            if "auth_token" in cookies and "ct0" in cookies:
                COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)
                COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
                print(f"\nSUCCESS! {len(cookies)} cookies saved to {COOKIES_FILE}")
                print("Now copy cookies to your server's data/ directory.")
            else:
                print(f"\nFAILED: auth cookies missing. Got: {list(cookies.keys())}")
                page.screenshot(path="data/twitter_debug_3_failed.png")
                sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
