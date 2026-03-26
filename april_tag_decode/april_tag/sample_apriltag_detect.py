#!/usr/bin/env python3
"""
Minimal example: import the official apriltag extension from apriltag/build and run detection.

Before running, either:
  - source the env helper (see README.md), or
  - export PYTHONPATH and LD_LIBRARY_PATH to your apriltag/build directory, or
  - set APRILTAG_BUILD to that directory (this script prepends it to sys.path).

Then from any working directory:
  python3 sample_apriltag_detect.py [image.png]
"""

from __future__ import annotations

import os
import sys


def _ensure_apriltag_on_path() -> None:
    """Allow running without shell exports if APRILTAG_BUILD is set."""
    build_dir = os.environ.get("APRILTAG_BUILD", "").strip()
    if build_dir and os.path.isdir(build_dir):
        abs_build = os.path.abspath(build_dir)
        if abs_build not in sys.path:
            sys.path.insert(0, abs_build)


def main() -> int:
    _ensure_apriltag_on_path()

    try:
        import numpy as np
        from apriltag import apriltag
    except ImportError as e:
        print(
            "Could not import apriltag:",
            e,
            file=sys.stderr,
        )
        print(
            "\nFix: build apriltag (cmake + make), then either:\n"
            "  export PYTHONPATH=\"/path/to/apriltag/build:$PYTHONPATH\"\n"
            "  export LD_LIBRARY_PATH=\"/path/to/apriltag/build:$LD_LIBRARY_PATH\"\n"
            "or set APRILTAG_BUILD=/path/to/apriltag/build and run this script again.\n"
            "See README.md for full steps.",
            file=sys.stderr,
        )
        return 1

    # Synthetic 8-bit grayscale image if no file given (detector still runs; may find nothing).
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        try:
            import cv2
        except ImportError:
            print("Install OpenCV to load images: pip install opencv-python", file=sys.stderr)
            return 1
        gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            print(f"Could not read image: {path}", file=sys.stderr)
            return 1
    else:
        gray = np.zeros((480, 640), dtype=np.uint8)

    detector = apriltag(
        "tagStandard52h13",
        threads=2,
        maxhamming=1,
        decimate=2.0,
        blur=0.0,
        refine_edges=True,
    )

    dets = detector.detect(gray)
    print(f"Detections: {len(dets)}")
    for d in dets:
        print(
            f"  id={d['id']} hamming={d['hamming']} "
            f"margin={d['margin']:.3f} center={d['center']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
