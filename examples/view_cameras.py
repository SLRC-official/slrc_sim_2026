#!/usr/bin/env python3
"""View robot cameras. Ares: --api-url http://0.0.0.0:8000. Hostile: --api-url http://0.0.0.0:8001 (floor only)."""

import cv2
import numpy as np
import requests
import argparse


def fetch_frame(api_url: str, cam_id: str):
    try:
        r = requests.get(f"{api_url}/camera/{cam_id}/frame", timeout=2)
        if r.status_code == 200:
            return cv2.imdecode(np.frombuffer(r.content, dtype=np.uint8), cv2.IMREAD_COLOR)
    except requests.RequestException:
        pass
    return None


def main():
    ap = argparse.ArgumentParser(description="View SLRC robot cameras")
    ap.add_argument('--api-url', default='http://0.0.0.0:8000', help='API URL')
    args = ap.parse_args()

    cameras = ['front_left', 'front_right', 'floor']
    print(f"Connecting to {args.api_url}. Press 'q' to quit.")
    placeholder = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.putText(placeholder, "Waiting...", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

    try:
        while True:
            for cam_id in cameras:
                frame = fetch_frame(args.api_url, cam_id)
                if frame is not None:
                    cv2.putText(frame, cam_id, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.imshow(f"SLRC - {cam_id}", frame)
                else:
                    cv2.imshow(f"SLRC - {cam_id}", placeholder)
            if cv2.waitKey(100) & 0xFF in (ord('q'), 27):
                break
    finally:
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
