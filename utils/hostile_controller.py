#!/usr/bin/env python3
"""Organizer's hostile robot controller. Same implementation used on competition day."""

import math
import time
import random
import requests
import numpy as np
import cv2

API_URL = "http://0.0.0.0:8001"
VELOCITY_URL = f"{API_URL}/set_velocity"
CAMERA_URL = f"{API_URL}/camera/floor/frame"
HEALTH_URL = f"{API_URL}/health"
STOP_URL = f"{API_URL}/stop"

CRUISE_SPEED = 0.6
STEER_KP = 0.005
STEER_KD = 0.002
MAX_ANGULAR_VEL = 3.0
TURN_SPEED = 2.0
REVERSAL_PROB = 0.002

YELLOW_H_LOW, YELLOW_H_HIGH = 20, 40
YELLOW_S_LOW, YELLOW_S_HIGH = 80, 255
YELLOW_V_LOW, YELLOW_V_HIGH = 150, 255
ROI_TOP_FRACTION = 0.5
LOOP_DT = 1.0 / 30
MIN_AREA = 500
MAX_LOST_FRAMES = 30

def wait_for_api():
    print("[Hostile] Waiting for API at 0.0.0.0:8001...")
    while True:
        try:
            if requests.get(HEALTH_URL, timeout=2).status_code == 200:
                print("[Hostile] API OK, connecting to camera...")
                return
        except requests.RequestException as e:
            print(f"[Hostile] API not reachable yet ({e}). Retrying in 1s...")
        time.sleep(1)


def wait_for_camera():
    while True:
        try:
            r = requests.get(CAMERA_URL, timeout=2)
            if r.status_code == 200 and len(r.content) > 100:
                print("[Hostile] Camera ready. Starting line follower.")
                return
        except requests.RequestException as e:
            print(f"[Hostile] Camera not ready ({e}). Retrying...")
        time.sleep(1)


def get_frame():
    try:
        r = requests.get(CAMERA_URL, timeout=1)
        if r.status_code == 200:
            return cv2.imdecode(np.frombuffer(r.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        pass
    return None


def detect_line(frame):
    h, w = frame.shape[:2]
    roi = frame[int(h * ROI_TOP_FRACTION):, :]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([YELLOW_H_LOW, YELLOW_S_LOW, YELLOW_V_LOW]),
                      np.array([YELLOW_H_HIGH, YELLOW_S_HIGH, YELLOW_V_HIGH]))
    m = cv2.moments(mask)
    area = m['m00']
    if area < MIN_AREA:
        return False, 0.0, 0.0
    cx = m['m10'] / area
    return True, cx - w / 2.0, area


def set_velocity(v, w):
    try:
        requests.post(VELOCITY_URL, json={"velocity": float(v), "omega": float(w)}, timeout=0.5)
    except Exception:
        pass


def execute_180():
    turn_dir = random.choice([-1.0, 1.0])
    direction = "left" if turn_dir < 0 else "right"
    print(f"[Hostile] Reversing 180° (turning {direction})...")
    set_velocity(0, 0)
    time.sleep(0.3)
    turn_duration = math.pi / TURN_SPEED
    start = time.time()
    while (time.time() - start) < turn_duration:
        set_velocity(0, turn_dir * TURN_SPEED)
        time.sleep(LOOP_DT)
    set_velocity(0, 0)
    time.sleep(0.3)
    print("[Hostile] Reversal done, resuming line follow.")


def main():
    wait_for_api()
    wait_for_camera()

    prev_error = 0.0
    lost_count = 0

    while True:
        loop_start = time.time()
        if random.random() < REVERSAL_PROB:
            execute_180()
            prev_error = 0.0
            lost_count = 0
            continue

        frame = get_frame()
        if frame is None:
            time.sleep(LOOP_DT)
            continue

        found, error, _ = detect_line(frame)
        if found:
            if lost_count > 0:
                print("[Hostile] Line found again.")
            lost_count = 0
            d_error = (error - prev_error) / LOOP_DT
            omega = -(STEER_KP * error + STEER_KD * d_error)
            omega = max(-MAX_ANGULAR_VEL, min(MAX_ANGULAR_VEL, omega))
            speed_factor = max(0.3, 1.0 - abs(omega) / MAX_ANGULAR_VEL)
            set_velocity(CRUISE_SPEED * speed_factor, omega)
            prev_error = error
        else:
            lost_count += 1
            if lost_count < MAX_LOST_FRAMES:
                if lost_count == 1:
                    print("[Hostile] Line lost, recovering...")
                recover_dir = -1.0 if prev_error >= 0 else 1.0
                set_velocity(0.1, recover_dir * 1.0)
            else:
                if lost_count == MAX_LOST_FRAMES:
                    print("[Hostile] Line still lost, searching (spinning)...")
                set_velocity(0, 1.5)

        elapsed = time.time() - loop_start
        if LOOP_DT - elapsed > 0:
            time.sleep(LOOP_DT - elapsed)


if __name__ == "__main__":
    main()
