"""Twitter login via Camoufox → export cookies for twikit.

Runs as a separate subprocess to avoid asyncio conflicts with uvicorn.
"""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

TWIKIT_COOKIES_FILE = Path(settings.twitter_cookies_file)

# Standalone login script (executed as subprocess)
_LOGIN_SCRIPT = """
import json
import sys
import time

username = sys.argv[1]
email = sys.argv[2]
password = sys.argv[3]
cookies_file = sys.argv[4]

from camoufox.sync_api import NewBrowser
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = NewBrowser(pw, headless="virtual", humanize=True, os="windows")
    try:
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        page.goto("https://x.com/i/flow/login", wait_until="networkidle", timeout=60000)
        time.sleep(3)

        # Debug screenshot
        page.screenshot(path="data/twitter_page_loaded.png")
        print(f"Page URL after load: {page.url}", file=sys.stderr)
        print(f"Page title: {page.title()}", file=sys.stderr)

        # Username
        username_input = page.locator('input[autocomplete="username"]')
        username_input.wait_for(state="visible", timeout=30000)
        username_input.fill(username)
        page.keyboard.press("Enter")
        time.sleep(2)

        # Email verification (optional step)
        try:
            email_input = page.locator('input[data-testid="ocfEnterTextTextInput"]')
            email_input.wait_for(state="visible", timeout=3000)
            if email_input.is_visible():
                email_input.fill(email)
                page.keyboard.press("Enter")
                time.sleep(2)
        except Exception:
            pass

        # Password
        password_input = page.locator('input[type="password"]')
        password_input.wait_for(state="visible", timeout=15000)
        password_input.fill(password)
        page.keyboard.press("Enter")
        time.sleep(3)

        # Wait for home
        try:
            page.wait_for_url("**/home**", timeout=15000)
        except Exception:
            url = page.url
            if "login" in url or "flow" in url:
                try:
                    page.screenshot(path="data/twitter_login_debug.png")
                except Exception:
                    pass
                print(json.dumps({"error": f"Login failed, stuck at: {url}"}))
                sys.exit(1)

        # Extract cookies
        browser_cookies = context.cookies("https://x.com")
        cookies = {c["name"]: c["value"] for c in browser_cookies}

        if "auth_token" not in cookies or "ct0" not in cookies:
            print(json.dumps({"error": f"Auth cookies missing. Keys: {list(cookies.keys())}"}))
            sys.exit(1)

        from pathlib import Path
        Path(cookies_file).parent.mkdir(parents=True, exist_ok=True)
        Path(cookies_file).write_text(json.dumps(cookies, indent=2))
        print(json.dumps({"ok": True, "cookies_count": len(cookies)}))

    finally:
        browser.close()
"""


def _run_login_subprocess() -> bool:
    """Run Camoufox login as separate Python process."""
    logger.info(
        "Starting Camoufox login subprocess for @%s...", settings.twitter_username
    )

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                _LOGIN_SCRIPT,
                settings.twitter_username,
                settings.twitter_email,
                settings.twitter_password,
                str(TWIKIT_COOKIES_FILE),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            stderr = result.stderr[:500] if result.stderr else ""
            stdout = result.stdout[:500] if result.stdout else ""
            logger.error(
                "Login subprocess failed (rc=%d): %s %s",
                result.returncode,
                stderr,
                stdout,
            )
            return False

        output = result.stdout.strip()
        if not output:
            logger.error("Login subprocess returned empty output")
            return False

        data = json.loads(output.split("\n")[-1])
        if data.get("ok"):
            logger.info(
                "Twitter login successful! %d cookies saved",
                data.get("cookies_count", 0),
            )
            return True

        logger.error("Login failed: %s", data.get("error", "unknown"))
        return False

    except subprocess.TimeoutExpired:
        logger.error("Login subprocess timed out (120s)")
        return False
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Login subprocess error: %s", exc)
        return False


async def login_and_save_cookies() -> bool:
    """Async wrapper: runs login subprocess in executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_login_subprocess)


async def ensure_valid_cookies() -> bool:
    """Check if cookies exist and valid, re-login if needed."""
    if TWIKIT_COOKIES_FILE.exists():
        try:
            cookies = json.loads(TWIKIT_COOKIES_FILE.read_text(encoding="utf-8"))
            if "auth_token" in cookies and "ct0" in cookies:
                logger.debug("Twitter cookies exist with auth_token + ct0")
                return True
        except (json.JSONDecodeError, KeyError):
            pass

    if not settings.twitter_username or not settings.twitter_password:
        logger.info("Twitter credentials not configured, can't auto-login")
        return False

    logger.info("No valid Twitter cookies, performing Camoufox login...")
    return await login_and_save_cookies()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Login result: {_run_login_subprocess()}")
