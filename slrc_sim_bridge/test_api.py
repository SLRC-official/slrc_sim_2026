#!/usr/bin/env python3
"""
API Test Script for SLRC 2026 Simulation

Tests the robot API endpoints.
"""

import requests
import time

BASE_URL = "http://localhost:8000"


def test_api():
    print("=" * 50)
    print("SLRC 2026 API Test")
    print("=" * 50)

    print("\n>>> Testing Root Endpoint...")
    try:
        r = requests.get(f"{BASE_URL}/")
        print(f"Root: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Root Failed: {e}")
        return

    print("\n>>> Testing Health Endpoint...")
    try:
        r = requests.get(f"{BASE_URL}/health")
        print(f"Health: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Health Failed: {e}")

    print("\n>>> Testing Odometry (Initial)...")
    try:
        r = requests.get(f"{BASE_URL}/odometry")
        print(f"Odom: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Odom Failed: {e}")

    print("\n>>> Testing Velocity Command (Forward)...")
    try:
        r = requests.post(f"{BASE_URL}/set_velocity", json={"velocity": 1, "omega": 0.0})
        print(f"Set Vel: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Set Vel Failed: {e}")

    print("Sleeping 2s to let robot move...")
    time.sleep(2)


    print("\n>>> Stopping Robot...")
    requests.post(f"{BASE_URL}/stop")

    print("\n>>> Testing Relative Move (Trapezoidal)...")
    try:
        # Rotate 90 degrees (pi/2)
        r = requests.post(f"{BASE_URL}/move_relative", json={"distance": 0.0, "rotation": 3.14})
        print(f"Move Rel: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Move Rel Failed: {e}")
    
    print("Sleeping 3s for rotation to complete...")
    time.sleep(10)

    print("\n>>> Testing Velocity Command (Forward)...")
    try:
        r = requests.post(f"{BASE_URL}/set_velocity", json={"velocity": 1, "omega": 0.0})
        print(f"Set Vel: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Set Vel Failed: {e}")

    print("Sleeping 2s to let robot move...")
    time.sleep(2)




    print("\n>>> Testing Relative Move (Forward 0.5m)...")
    try:
        r = requests.post(f"{BASE_URL}/move_relative", json={"distance": 1.2, "rotation": 0.0})
        print(f"Move Rel: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Move Rel Failed: {e}")
    
    print("Sleeping 3s for move to complete...")
    time.sleep(3)

    print("\n>>> Testing Odometry (After Move)...")
    try:
        r = requests.get(f"{BASE_URL}/odometry")
        print(f"Odom: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Odom Failed: {e}")

    print("\n>>> Testing Arena Metadata...")
    try:
        r = requests.get(f"{BASE_URL}/arena/metadata")
        print(f"Arena: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Arena Failed: {e}")

    print("\n>>> Testing Hostile Position...")
    try:
        r = requests.get(f"{BASE_URL}/hostile/position")
        print(f"Hostile: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Hostile Failed: {e}")

    print("\n>>> Testing Camera Availability...")
    for cam in ['front_left', 'front_right', 'floor']:
        try:
            r = requests.get(f"{BASE_URL}/camera/{cam}/frame", timeout=2)
            print(f"Camera {cam}: {r.status_code} ({len(r.content)} bytes)")
        except Exception as e:
            print(f"Camera {cam} Failed: {e}")

    print("\n>>> Stopping Robot...")
    requests.post(f"{BASE_URL}/stop")

    print("\n" + "=" * 50)
    print("API Test Complete")
    print("=" * 50)


if __name__ == "__main__":
    test_api()
