#!/usr/bin/env python3
"""
Hostile Controller Script - SLRC 2026
Controls the hostile robot via HTTP API (Port 8001).

Usage:
  python3 hostile_controller.py

Behavior:
  - Fetches loop path from API
  - Follows path using move_relative commands
  - Randomly reverses direction
"""

import math
import time
import random
import requests
import sys

# Configuration
API_URL = "http://localhost:8001"
MOVES_URL = f"{API_URL}/move_relative"
ODOM_URL = f"{API_URL}/odometry"
LOOP_URL = f"{API_URL}/arena/hostile_loop"
STOP_URL = f"{API_URL}/stop"

# Hostile behavior params
DIRECTION_SWITCH_PROB = 0.01  # Probability to switch direction after a segment
PatrolSpeed = 1

def normalize_angle(angle):
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle

def get_odometry():
    try:
        resp = requests.get(ODOM_URL, timeout=1)
        resp.raise_for_status()
        return resp.json()['pose']
    except Exception as e:
        print(f"Error getting odometry: {e}")
        return None

def wait_for_api():
    print(f"Waiting for API at {API_URL}...")
    while True:
        try:
            requests.get(f"{API_URL}/health", timeout=1)
            print("API is online.")
            return
        except requests.RequestException:
            time.sleep(1)

def move_robot(distance, rotation):
    """Send move command and wait for completion."""
    payload = {"distance": float(distance), "rotation": float(rotation)}
    try:
        # Retry loop for 409 Conflict (Busy)
        while True:
            resp = requests.post(MOVES_URL, json=payload, timeout=1)
            if resp.status_code == 200:
                break
            elif resp.status_code == 409:
                time.sleep(0.1)
                continue
            else:
                resp.raise_for_status()
                break
        
        # Wait for move to finish
        est_time = abs(distance)/PatrolSpeed + abs(rotation)/PatrolSpeed
        time.sleep(est_time)
        
        # Poll 409 until we can move again (means idle)
        # Actually checking if we can post again is a good check
        while True:
            dummy = requests.post(MOVES_URL, json={"distance": 0.0, "rotation": 0.0}, timeout=1)
            if dummy.status_code == 200:
                break
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Move failed: {e}")

def main():
    wait_for_api()

    # Get Loop Path
    try:
        resp = requests.get(LOOP_URL)
        resp.raise_for_status()
        data = resp.json()
        path_points = data['world_coordinates'] # List of {x, y}
        if not path_points:
            print("No path found!")
            return
    except Exception as e:
        print(f"Failed to get path: {e}")
        return

    print(f"Loaded path with {len(path_points)} points.")

    # We assume we always start at index 0
    curr_idx = 0
    print(f"Starting at index {curr_idx}")
    
    # The world coordinates of the 0-th index
    spawn_wx = path_points[0]['x']
    spawn_wy = path_points[0]['y']

    direction = 1 # 1 for forward list, -1 for backward
    
    print("Waiting for initial odometry...")
    while True:
        pose = get_odometry()
        if pose:
            break
        time.sleep(1)

    while True:
        # Check random reversal
        if random.random() < DIRECTION_SWITCH_PROB:
            print(">>> SWITCHING DIRECTION <<<")
            direction *= -1
            
        # Determine next index
        next_idx = (curr_idx + direction) % len(path_points)
        target_world = path_points[next_idx]

        # Convert target world coordinate to local odometry frame
        target_local_x = target_world['x'] - spawn_wx
        target_local_y = target_world['y'] - spawn_wy
        
        # Get current pose (in local odometry frame)
        pose = get_odometry()
        if not pose:
            time.sleep(1)
            continue
            
        curr_x = pose['x']
        curr_y = pose['y']
        curr_yaw = pose['yaw']
        
        # Calculate moves relative to current local pose
        dx = target_local_x - curr_x
        dy = target_local_y - curr_y
        dist = math.hypot(dx, dy)
        target_yaw = math.atan2(dy, dx)
        
        yaw_diff = normalize_angle(target_yaw - curr_yaw)
        
        print(f"Moving to {next_idx}: Dist={dist:.2f}, Turn={math.degrees(yaw_diff):.1f}")
        
        # Turn first
        if abs(yaw_diff) > 0.05:
            move_robot(0.0, yaw_diff)
            
        # Move forward
        if dist > 0.05:
            move_robot(dist, 0.0)
            
        curr_idx = next_idx
        time.sleep(0.1)

if __name__ == "__main__":
    main()
