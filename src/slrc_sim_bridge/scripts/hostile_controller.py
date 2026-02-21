#!/usr/bin/env python3
"""
Hostile Controller Script - SLRC 2026
Camera-based yellow line follower with random 180° reversals.

Usage:
  python3 hostile_controller.py

Behavior:
  - Follows the yellow line on the arena using floor camera
  - Uses PD control to steer toward the line centroid
  - Randomly performs 180° direction reversals
  - No arena path knowledge needed — just start on the yellow line
"""

import math
import time
import random
import requests
import numpy as np
import cv2
import io

# Configuration
API_URL = "http://localhost:8001"
VELOCITY_URL = f"{API_URL}/set_velocity"
CAMERA_URL = f"{API_URL}/camera/floor/frame"
HEALTH_URL = f"{API_URL}/health"
STOP_URL = f"{API_URL}/stop"

# Line-following parameters (mirrors HostileConfig)
CRUISE_SPEED = 0.6       # m/s forward speed
STEER_KP = 0.005         # Proportional gain
STEER_KD = 0.002         # Derivative gain
MAX_ANGULAR_VEL = 3.0    # rad/s clamp
TURN_SPEED = 2.0         # rad/s for 180° turns
REVERSAL_PROB = 0.002    # Per-cycle probability of reversal

# HSV thresholds for yellow line detection
YELLOW_H_LOW = 20
YELLOW_H_HIGH = 40
YELLOW_S_LOW = 80
YELLOW_S_HIGH = 255
YELLOW_V_LOW = 150
YELLOW_V_HIGH = 255

# Control loop rate
LOOP_RATE = 30  # Hz
LOOP_DT = 1.0 / LOOP_RATE

# Image ROI: only look at bottom portion of image for line detection
ROI_TOP_FRACTION = 0.5  # Use bottom 50% of image


def wait_for_api():
    """Wait for the hostile API to come online."""
    print(f"Waiting for API at {API_URL}...")
    while True:
        try:
            resp = requests.get(HEALTH_URL, timeout=2)
            if resp.status_code == 200:
                print("API is online.")
                return
        except requests.RequestException:
            pass
        time.sleep(1)


def wait_for_camera():
    """Wait until the floor camera starts providing frames."""
    print("Waiting for floor camera...")
    while True:
        try:
            resp = requests.get(CAMERA_URL, timeout=2)
            if resp.status_code == 200 and len(resp.content) > 100:
                print("Floor camera is active.")
                return
        except requests.RequestException:
            pass
        time.sleep(1)


def get_camera_frame():
    """Fetch a single JPEG frame from the floor camera and decode it."""
    try:
        resp = requests.get(CAMERA_URL, timeout=1)
        if resp.status_code != 200:
            return None
        img_array = np.frombuffer(resp.content, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        return None


def detect_yellow_line(frame):
    """
    Detect the yellow line in the camera frame.
    Returns (found, error, area) where:
      - found: True if yellow line was detected
      - error: horizontal offset of line centroid from image center (pixels)
               Positive = line is to the right, negative = to the left
      - area: total area of detected yellow pixels
    """
    h, w = frame.shape[:2]

    # Crop to bottom ROI
    roi_top = int(h * ROI_TOP_FRACTION)
    roi = frame[roi_top:, :]

    # Convert to HSV
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Threshold for yellow
    lower = np.array([YELLOW_H_LOW, YELLOW_S_LOW, YELLOW_V_LOW])
    upper = np.array([YELLOW_H_HIGH, YELLOW_S_HIGH, YELLOW_V_HIGH])
    mask = cv2.inRange(hsv, lower, upper)

    # Find moments to get centroid
    moments = cv2.moments(mask)
    area = moments['m00']

    if area < 500:  # Minimum area threshold
        return False, 0.0, 0.0

    cx = moments['m10'] / area
    # Error from center of image
    error = cx - (w / 2.0)

    return True, error, area


def set_velocity(velocity, omega):
    """Send velocity command via API."""
    payload = {"velocity": float(velocity), "omega": float(omega)}
    try:
        requests.post(VELOCITY_URL, json=payload, timeout=0.5)
    except Exception:
        pass


def stop_robot():
    """Emergency stop."""
    try:
        requests.post(STOP_URL, timeout=0.5)
    except Exception:
        pass


def execute_180_turn():
    """Execute a 180° turn in place."""
    print(">>> EXECUTING 180° REVERSAL <<<")

    # Stop first
    set_velocity(0.0, 0.0)
    time.sleep(0.3)

    # Calculate turn duration: pi radians at TURN_SPEED rad/s
    turn_duration = math.pi / TURN_SPEED

    # Pick random direction for the turn
    turn_dir = random.choice([-1, 1])

    # Execute the turn
    start_time = time.time()
    while (time.time() - start_time) < turn_duration:
        set_velocity(0.0, turn_dir * TURN_SPEED)
        time.sleep(LOOP_DT)

    # Stop after turn
    set_velocity(0.0, 0.0)
    time.sleep(0.3)
    print(">>> REVERSAL COMPLETE <<<")


def main():
    print("=" * 50)
    print("  HOSTILE CONTROLLER - Yellow Line Follower")
    print("=" * 50)

    wait_for_api()
    wait_for_camera()

    print("Starting line-following loop...")

    prev_error = 0.0
    lost_line_count = 0
    MAX_LOST_FRAMES = 30  # Stop after losing line for 1 second

    while True:
        loop_start = time.time()

        # Check for random 180° reversal
        if random.random() < REVERSAL_PROB:
            execute_180_turn()
            prev_error = 0.0
            lost_line_count = 0
            continue

        # Get camera frame
        frame = get_camera_frame()
        if frame is None:
            time.sleep(LOOP_DT)
            continue

        # Detect yellow line
        found, error, area = detect_yellow_line(frame)

        if found:
            lost_line_count = 0

            # PD control for steering
            d_error = (error - prev_error) / LOOP_DT
            omega = -(STEER_KP * error + STEER_KD * d_error)

            # Clamp angular velocity
            omega = max(-MAX_ANGULAR_VEL, min(MAX_ANGULAR_VEL, omega))

            # Reduce speed when turning sharply
            speed_factor = max(0.3, 1.0 - abs(omega) / MAX_ANGULAR_VEL)
            velocity = CRUISE_SPEED * speed_factor

            set_velocity(velocity, omega)
            prev_error = error

        else:
            lost_line_count += 1

            if lost_line_count < MAX_LOST_FRAMES:
                # Try to recover: spin slowly in the direction of last known error
                recover_dir = -1.0 if prev_error >= 0 else 1.0
                set_velocity(0.1, recover_dir * 1.0)
            else:
                # Lost line for too long, stop and spin to search
                set_velocity(0.0, 1.5)

        # Maintain loop rate
        elapsed = time.time() - loop_start
        sleep_time = LOOP_DT - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)


if __name__ == "__main__":
    main()
