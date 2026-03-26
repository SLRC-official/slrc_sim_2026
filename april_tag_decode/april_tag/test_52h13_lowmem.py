#!/usr/bin/env python3
"""
Video demo: tagStandard52h13 with maxhamming=1 — Python equivalent of test_52h13_lowmem.c.

Requires: numpy, apriltag (extension from AprilTag build), opencv-python or cv2.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Low-memory AprilTag tagStandard52h13 demo (Python)",
    )
    parser.add_argument(
        "source",
        nargs="?",
        default="0",
        help="Video file path, or '0' for default camera (default: %(default)s)",
    )
    args = parser.parse_args()

    try:
        import cv2
        from apriltag import apriltag
    except ImportError as e:
        print(
            "Missing dependency:",
            e,
            file=sys.stderr,
        )
        print(
            "Install OpenCV (e.g. apt install python3-opencv or pip install opencv-python), "
            "numpy, and build the apriltag Python module from apriltag/ (see README.md).",
            file=sys.stderr,
        )
        return 1

    source = args.source
    cap = cv2.VideoCapture(int(source) if source.isdigit() else source)
    if not cap.isOpened():
        print(f"Could not open video source: {source}", file=sys.stderr)
        return 1

    detector = apriltag(
        "tagStandard52h13",
        threads=3,
        maxhamming=1,
        decimate=10.0,
        blur=0.0,
        refine_edges=True,
    )

    win = "tagStandard52h13 low-mem test"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 640, 360)

    while True:
        ok, frame = cap.read()
        if not ok or frame is None or frame.size == 0:
            break

        if frame.ndim == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        dets = detector.detect(gray)
        display = frame.copy()

        for d in dets:
            pid = int(d["id"])
            hamming = int(d["hamming"])
            margin = float(d["margin"])
            print(f"id={pid}, hamming={hamming}, decision_margin={margin:.2f}")

            corners = d["lb-rb-rt-lt"]
            for j in range(4):
                p1 = (int(corners[j, 0]), int(corners[j, 1]))
                p2 = (int(corners[(j + 1) % 4, 0]), int(corners[(j + 1) % 4, 1]))
                cv2.line(display, p1, p2, (0, 255, 0), 2)

            cx, cy = int(d["center"][0]), int(d["center"][1])
            cv2.putText(
                display,
                f"ID={pid}",
                (cx, cy),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )

        cv2.putText(
            display,
            f"Detections: {len(dets)}",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 0, 0),
            2,
        )

        small = cv2.resize(display, (0, 0), fx=0.6, fy=0.6)
        cv2.imshow(win, small)
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
