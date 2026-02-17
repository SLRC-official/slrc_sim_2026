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
DIRECTION_SWITCH_PROB = 0.10  # Probability to switch direction after a segment
PatrolSpeed = 0.5

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
        # Heuristic wait: dist/0.5 + rot/1.0 + buffer
        est_time = abs(distance)/0.5 + abs(rotation)/1.0
        time.sleep(est_time)
        
        # Poll 409 until we can move again (means idle)
        # Actually checking if we can post again is a good check
        while True:
            # We can check simple health or just try to start next move? 
            # Better: check if we are moving? API doesn't expose 'is_moving' directly 
            # but move_relative returns 409 if moving.
             # So we can't 'check' without side effects unless we try a 0 move.
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

    # Find nearest point index
    pose = get_odometry()
    if not pose:
        return
    
    curr_x = pose['x']
    curr_y = pose['y']
    
    min_dist = float('inf')
    curr_idx = 0
    
    for i, pt in enumerate(path_points):
        d = math.hypot(pt['x'] - curr_x, pt['y'] - curr_y)
        if d < min_dist:
            min_dist = d
            curr_idx = i
            
    print(f"Starting at index {curr_idx}")
    
    direction = 1 # 1 for forward list, -1 for backward
    
    while True:
        # Check random reversal
        if random.random() < DIRECTION_SWITCH_PROB:
            print(">>> SWITCHING DIRECTION <<<")
            direction *= -1
            
        # Determine next index
        next_idx = (curr_idx + direction) % len(path_points)
        target = path_points[next_idx]
        
        # Get current pose
        pose = get_odometry()
        if not pose:
            time.sleep(1)
            continue
            
        curr_x = pose['x']
        curr_y = pose['y']
        curr_yaw = pose['yaw']
        
        # Calculate moves
        dx = target['x'] - curr_x
        dy = target['y'] - curr_y
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
