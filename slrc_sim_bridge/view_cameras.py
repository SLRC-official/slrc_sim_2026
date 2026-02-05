#!/usr/bin/env python3
"""
Camera Viewer - View all three robot cameras in OpenCV windows

Run this while the simulation is active to see the camera feeds.
Press 'q' to quit.

Usage:
    python3 view_cameras.py [--api-url http://localhost:8000]
"""

import cv2
import numpy as np
import requests
import argparse
import time


def fetch_frame(api_url: str, cam_id: str):
    """Fetch a single JPEG frame from the API."""
    url = f"{api_url}/camera/{cam_id}/frame"
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            img = cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR)
            return img
        elif response.status_code == 503:
            return None  # No frame yet
        else:
            print(f"[{cam_id}] Error: HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException:
        return None


def main():
    parser = argparse.ArgumentParser(description="View SLRC robot cameras")
    parser.add_argument('--api-url', default='http://localhost:8000',
                        help='API server URL (default: http://localhost:8000)')
    args = parser.parse_args()
    
    api_url = args.api_url
    cameras = ['front_left', 'front_right', 'floor']
    
    print(f"Connecting to API at {api_url}...")
    print("Camera windows will open. Press 'q' to quit.")
    print("Waiting for camera frames...")
    
    # Create placeholder images
    placeholder = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.putText(placeholder, "Waiting for frame...", (30, 120), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
    
    try:
        while True:
            any_frame = False
            
            for cam_id in cameras:
                frame = fetch_frame(api_url, cam_id)
                
                if frame is not None:
                    any_frame = True
                    # Add label
                    labeled = frame.copy()
                    label = cam_id.replace('_', ' ').title()
                    cv2.putText(labeled, label, (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.imshow(f"SLRC - {cam_id}", labeled)
                else:
                    # Show placeholder
                    p = placeholder.copy()
                    cv2.putText(p, cam_id, (10, 30), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 1)
                    cv2.imshow(f"SLRC - {cam_id}", p)
            
            # Check for quit key
            key = cv2.waitKey(100) & 0xFF
            if key == ord('q') or key == 27:  # q or ESC
                break
    
    except KeyboardInterrupt:
        print("\nInterrupted")
    
    finally:
        cv2.destroyAllWindows()
        print("Camera viewer closed.")


if __name__ == '__main__':
    main()
