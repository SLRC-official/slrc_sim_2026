
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print(">>> Testing API Connectivity...")
    try:
        r = requests.get(f"{BASE_URL}/")
        print(f"Root: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print("\n>>> Testing Odometry (Initial)...")
    try:
        r = requests.get(f"{BASE_URL}/odometry")
        print(f"Odom: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Odom Failed: {e}")

    print("\n>>> Testing Velocity Command (Forward)...")
    try:
        r = requests.post(f"{BASE_URL}/set_velocity", json={"vx": 5, "vy": 0.0, "omega": 0.0})
        print(f"Set Vel: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Set Vel Failed: {e}")

    print("Sleeping 2s to let robot move...")
    time.sleep(2)

    try:
        r = requests.post(f"{BASE_URL}/set_velocity", json={"vx": 0, "vy": 5.0, "omega": 0.0})
        print(f"Set Vel: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Set Vel Failed: {e}")

    print("Sleeping 2s to let robot move...")
    time.sleep(2)


    try:
        r = requests.post(f"{BASE_URL}/set_velocity", json={"vx": 0, "vy": 0.0, "omega": 5.0})
        print(f"Set Vel: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Set Vel Failed: {e}")

    print("Sleeping 2s to let robot move...")
    time.sleep(2)

    print("\n>>> Testing Odometry (After Move)...")
    try:
        r = requests.get(f"{BASE_URL}/odometry")
        print(f"Odom: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Odom Failed: {e}")

    print("\n>>> Stopping Robot...")
    requests.post(f"{BASE_URL}/set_velocity", json={"vx": 0.0, "vy": 0.0, "omega": 0.0})

    print("\n>>> Testing Relative Move (Trapezoidal)...")
    try:
        # Move 1 meter forward
        r = requests.post(f"{BASE_URL}/move_relative", json={"dx": 1.0, "dy": 0.0, "dtheta": 0.0})
        print(f"Move Rel: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Move Rel Failed: {e}")

    print("\n>>> Testing Camera Stream Availability...")
    cam_url = f"{BASE_URL}/camera/front_left/stream"
    try:
        # Just check headers or read a chunk
        with requests.get(cam_url, stream=True, timeout=2) as r:
            print(f"Camera Stream Status: {r.status_code}")
            print(f"Content-Type: {r.headers.get('Content-Type')}")
            # Ensure it's active
            chunk = next(r.iter_content(chunk_size=1024))
            print(f"Received chunk of size: {len(chunk)} bytes")
    except Exception as e:
        print(f"Camera Stream Failed (Expected if GZ not rendering or no image yet): {e}")

    print("\n>>> Testing Utility: LED...")
    try:
        r = requests.post(f"{BASE_URL}/utility/set_led", json={"state": "on", "color": "blue"})
        print(f"LED: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"LED Failed: {e}")
        
    print("\n>>> Testing Utility: Mark Path...")
    try:
        r = requests.post(f"{BASE_URL}/utility/mark_path", json={"points": [[0,0], [1,0]], "type": "polyline"})
        print(f"Marker: {r.status_code} {r.json()}")
    except Exception as e:
        print(f"Marker Failed: {e}")

if __name__ == "__main__":
    test_api()
