"""Extract Twitter cookies from HAR file and save for twikit."""

import json
import sys
from pathlib import Path


def main() -> None:
    har_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not har_path:
        print("Usage: python extract_cookies.py <path_to_har_file>")
        sys.exit(1)

    har = json.loads(Path(har_path).read_text())
    entries = har["log"]["entries"]

    cookies_raw = entries[0]["request"]["cookies"]
    cookies = {c["name"]: c["value"] for c in cookies_raw}

    print(f"Total cookies: {len(cookies)}")
    print(f"auth_token: {'YES' if 'auth_token' in cookies else 'NO'}")
    print(f"ct0: {'YES' if 'ct0' in cookies else 'NO'}")

    if "auth_token" not in cookies or "ct0" not in cookies:
        print("ERROR: Missing required cookies!")
        sys.exit(1)

    out = Path("data/twitter_cookies.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(cookies, indent=2))
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
