#!/usr/bin/env python3
"""Test Ares API endpoints. Requires simulation running. Run: python3 examples/test_api.py"""

import json
import requests
import time

BASE_URL = "http://localhost:8000"
NUM_SAMPLES = 4


def timed_get(path: str, timeout: float = 3):
    url = f"{BASE_URL}{path}"
    t0 = time.perf_counter()
    try:
        r = requests.get(url, timeout=timeout)
        elapsed = time.perf_counter() - t0
        data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else None
        return (data, r.status_code, elapsed)
    except Exception:
        return (None, -1, time.perf_counter() - t0)


def timed_post(path: str, payload: dict, timeout: float = 5):
    url = f"{BASE_URL}{path}"
    t0 = time.perf_counter()
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        elapsed = time.perf_counter() - t0
        data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else None
        return (data, r.status_code, elapsed)
    except Exception:
        return (None, -1, time.perf_counter() - t0)


def sample_sensors(phase: str):
    print(f"\n  [{phase}] Sample data:")
    for path, label in [("/odometry", "odom"), ("/imu", "imu"), ("/start_coordinate", "start")]:
        data, status, elapsed = timed_get(path, timeout=2)
        ms = elapsed * 1000
        out = data if status == 200 else (data.get("detail", "no data") if data else "no data")
        print(f"    {label:8} {ms:6.1f} ms  status={status}  {out}")


def main():
    print("=" * 60)
    print("SLRC 2026 API Test – Ares (localhost:8000)")
    print("=" * 60)

    sample_sensors("initial")

    print("\n>>> set_velocity(velocity=1, omega=0)")
    data, status, elapsed = timed_post("/set_velocity", {"velocity": 1.0, "omega": 0.0})
    print(f"    {elapsed*1000:.1f} ms  status={status}  {data}")
    time.sleep(2)
    sample_sensors("after forward 2s")

    print("\n>>> stop()")
    timed_post("/stop", {})
    sample_sensors("after stop")

    print("\n>>> move_relative(distance=0.5, rotation=1.57)")
    data, status, elapsed = timed_post("/move_relative", {"distance": 0.5, "rotation": 1.57})
    print(f"    {elapsed*1000:.1f} ms  status={status}  {data}")
    time.sleep(5)
    sample_sensors("after move_relative")

    print("\n>>> stop()")
    timed_post("/stop", {})
    sample_sensors("final")

    data, status, _ = timed_get("/arena/metadata")
    print("\n  [arena/metadata]:", data)
    print("=" * 60)


if __name__ == "__main__":
    main()
