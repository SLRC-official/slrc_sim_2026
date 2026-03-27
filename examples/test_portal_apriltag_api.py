#!/usr/bin/env python3
"""Example: portal + AprilTag HTTP API on the Ares service (port 8000).

Requires simulation running with the API. Run:
  python3 examples/test_portal_apriltag_api.py

Endpoints used:
  GET  /get_num_boxes_portal  -> {"count", "trigger"}
  POST /april_tag             -> {"raw", "order", "x", "y"}
  GET  /get_april_tag         -> {"data": [...]}  (optional verify)
"""

import argparse
import sys
import time

import requests

BASE_URL = "http://0.0.0.0:8000"


def wait_for_api(base: str, timeout_s: float = 60.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = requests.get(f"{base}/health", timeout=2)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.5)
    return False


def get_portal_settings(base: str) -> dict | None:
    """Read portal box count and trigger flag."""
    try:
        r = requests.get(f"{base}/get_num_boxes_portal", timeout=3)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"GET /get_num_boxes_portal failed: {e}", file=sys.stderr)
        return None


def submit_april_tag(base: str, raw: str, order: int, x: int, y: int) -> dict | None:
    """Post a single tag reading to the server (append to cache)."""
    payload = {"raw": raw, "order": order, "x": x, "y": y}
    try:
        r = requests.post(f"{base}/april_tag", json=payload, timeout=3)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"POST /april_tag failed: {e}", file=sys.stderr)
        return None


def list_april_tags(base: str) -> list | None:
    """Fetch all cached tag reports (useful for debugging)."""
    try:
        r = requests.get(f"{base}/get_april_tag", timeout=3)
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])
    except requests.RequestException as e:
        print(f"GET /get_april_tag failed: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Portal & AprilTag API example")
    parser.add_argument(
        "--api-url",
        default=BASE_URL,
        help=f"API base URL (default: {BASE_URL})",
    )
    args = parser.parse_args()
    base = args.api_url.rstrip("/")

    print("Waiting for API (/health)...")
    if not wait_for_api(base):
        print("API not reachable; start the simulation first.", file=sys.stderr)
        sys.exit(1)

    # --- Box count (portal settings) ---
    print("\n--- Portal settings (box count + trigger) ---")
    portal = get_portal_settings(base)
    if portal is not None:
        count = portal.get("count")
        trigger = portal.get("trigger")
        print(f"  count (number of boxes / slider value): {count}")
        print(f"  trigger: {trigger}")
    else:
        sys.exit(1)

    # --- Submit sample AprilTag readings ---
    print("\n--- Submit sample AprilTag reports (POST /april_tag) ---")
    samples = [
        {"raw": "05194", "order": 1, "x": 23, "y": 10},
        {"raw": "10405", "order": 2, "x": 12, "y": 8},
    ]
    for s in samples:
        resp = submit_april_tag(base, s["raw"], s["order"], s["x"], s["y"])
        print(f"  posted raw={s['raw']!r} order={s['order']} x={s['x']} y={s['y']} -> {resp}")

    stored = list_april_tags(base)
    if stored is not None:
        print(f"\n--- Cached tags on server ({len(stored)} row(s)) ---")
        for row in stored:
            print(f"  {row}")

    # Show portal again (unchanged unless something else updated it)
    print("\n--- Portal settings after posts ---")
    portal2 = get_portal_settings(base)
    if portal2 is not None:
        print(f"  count={portal2.get('count')}  trigger={portal2.get('trigger')}")

    print("\nDone.")
    print("Tip: optional endpoints — POST /set_num_boxes_portal with JSON count/trigger,")
    print("      GET /get_april_tag, POST /reset_april_tag with pass slrc_is_the_best.")


if __name__ == "__main__":
    main()
