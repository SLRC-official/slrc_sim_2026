#!/usr/bin/env python3
"""
API Test Script for SLRC 2026 Simulation

Runs motion commands as-is; samples odom, IMU, and other data during execution
and reports request timings.

Requires: simulation (Gazebo) + ROS–Gazebo bridge running so ares/odom and
/ares/imu/data are published; hostile controller for /hostile/position.
Otherwise /odometry, /imu, /hostile/position return 503.
"""

import json
import requests
import time

BASE_URL = "http://localhost:8000"

# How many samples of odom/imu/etc to print during motion (small number)
NUM_SAMPLES = 4


def timed_get(path: str, timeout: float = 3):
    """GET path; return (data or None, status_code, elapsed_sec)."""
    url = f"{BASE_URL}{path}"
    t0 = time.perf_counter()
    try:
        r = requests.get(url, timeout=timeout)
        elapsed = time.perf_counter() - t0
        data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else None
        return (data, r.status_code, elapsed)
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return (None, -1, elapsed)


def timed_post(path: str, payload: dict, timeout: float = 5):
    """POST path with json payload; return (data or None, status_code, elapsed_sec)."""
    url = f"{BASE_URL}{path}"
    t0 = time.perf_counter()
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        elapsed = time.perf_counter() - t0
        data = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else None
        return (data, r.status_code, elapsed)
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return (None, -1, elapsed)


def sample_sensors(phase: str, n: int = NUM_SAMPLES):
    """Poll odom, imu, start_coordinate, hostile once each; print compact + timings."""
    print(f"\n  [{phase}] Sample data (request times in ms):")
    # Odometry
    data, status, elapsed = timed_get("/odometry")
    ms = elapsed * 1000
    if data and status == 200:
        p = data.get("pose", {})
        v = data.get("velocity", {})
        print(f"    odom  {ms:6.1f} ms  status={status}  x={p.get('x')} y={p.get('y')} yaw={p.get('yaw')}  v_lin={v.get('linear')} v_ang={v.get('angular')}")
    else:
        detail = (data.get("detail") if data else None) or "no data"
        print(f"    odom  {ms:6.1f} ms  status={status}  {detail}")
    # IMU
    data, status, elapsed = timed_get("/imu")
    ms = elapsed * 1000
    if data and status == 200:
        av = data.get("angular_velocity", {})
        la = data.get("linear_acceleration", {})
        print(f"    imu   {ms:6.1f} ms  status={status}  ang_z={av.get('z')}  acc_x={la.get('x')} acc_y={la.get('y')}")
    else:
        detail = (data.get("detail") if data else None) or "no data"
        print(f"    imu   {ms:6.1f} ms  status={status}  {detail}")
    # Start coordinate
    data, status, elapsed = timed_get("/start_coordinate")
    ms = elapsed * 1000
    if data:
        print(f"    start {ms:6.1f} ms  status={status}  x={data.get('x')} y={data.get('y')}")
    # Hostile (optional)
    data, status, elapsed = timed_get("/hostile/position", timeout=2)
    ms = elapsed * 1000
    if data and status == 200:
        print(f"    hostile {ms:5.1f} ms  status={status}  x={data.get('x')} y={data.get('y')} yaw={data.get('yaw')}")
    else:
        detail = (data.get("detail") if data else None) or "no data"
        print(f"    hostile {ms:5.1f} ms  status={status}  {detail}")


def test_api():
    print("=" * 60)
    print("SLRC 2026 API Test – motion runs as-is, sample odom/IMU + timings")
    print("=" * 60)

    t_start = time.time()

    # Initial sample
    sample_sensors("initial")

    # ----- Motion: forward -----
    print("\n>>> set_velocity(velocity=1, omega=0)")
    data, status, elapsed = timed_post("/set_velocity", {"velocity": 1.0, "omega": 0.0})
    print(f"    request took {elapsed*1000:.1f} ms  status={status}  {data}")
    print("Sleeping 2s...")
    time.sleep(2)
    sample_sensors("after forward 2s")

    # ----- Stop -----
    print("\n>>> stop()")
    data, status, elapsed = timed_post("/stop", {})
    print(f"    request took {elapsed*1000:.1f} ms  status={status}  {data}")
    sample_sensors("after stop")

    # ----- Move relative: rotate ~pi rad -----
    print("\n>>> move_relative(distance=0, rotation=3.14)")
    data, status, elapsed = timed_post("/move_relative", {"distance": 0.0, "rotation": 3.14})
    print(f"    request took {elapsed*1000:.1f} ms  status={status}  {data}")
    print("Sleeping 10s for rotation...")
    for i in range(2):
        time.sleep(5.0)
        sample_sensors(f"during rotation ({i+1}/2)")
    sample_sensors("after rotation")

    # ----- Forward again -----
    print("\n>>> set_velocity(velocity=1, omega=0)")
    data, status, elapsed = timed_post("/set_velocity", {"velocity": 1.0, "omega": 0.0})
    print(f"    request took {elapsed*1000:.1f} ms  status={status}  {data}")
    print("Sleeping 2s...")
    time.sleep(2)

    # ----- Move relative: forward 1.2 m -----
    print("\n>>> move_relative(distance=1.2, rotation=0)")
    data, status, elapsed = timed_post("/move_relative", {"distance": 1.2, "rotation": 0.0})
    print(f"    request took {elapsed*1000:.1f} ms  status={status}  {data}")
    print("Sleeping 3s for move...")
    time.sleep(3)
    sample_sensors("after move_relative 1.2m")

    # ----- Stop -----
    print("\n>>> stop()")
    data, status, elapsed = timed_post("/stop", {})
    print(f"    request took {elapsed*1000:.1f} ms  status={status}  {data}")

    # ----- Final sample + arena -----
    sample_sensors("final")
    print("\n  [arena] metadata:")
    data, status, elapsed = timed_get("/arena/metadata")
    print(f"    {elapsed*1000:.1f} ms  status={status}  {data}")

    t_total = time.time() - t_start
    print("\n" + "=" * 60)
    print(f"Done. Total time {t_total:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    test_api()
