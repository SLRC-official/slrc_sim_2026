#!/usr/bin/env bash
# Load the built AprilTag Python extension without installing system-wide.
#
# 1. Edit APRILTAG_ROOT below if your apriltag/ directory is not next to april_tag/.
# 2. From bash:   source /path/to/source_apriltag_env.sh
# 3. Run Python from any directory; imports use the extension in apriltag/build/.
#
# The shared module file is named like: apriltag.cpython-<PY>-<PLATFORM>.so
# (see README.md). This script only needs the *directory* that contains it.

# Root of the AprilTag clone (contains apriltag/build/)
: "${APRILTAG_ROOT:=$(cd "$(dirname "${BASH_SOURCE[0]}")/../apriltag" && pwd)}"

BUILD="${APRILTAG_ROOT}/build"
if [[ ! -d "${BUILD}" ]]; then
  echo "error: build directory not found: ${BUILD}" >&2
  echo "Run CMake and make in apriltag/ first." >&2
  return 1 2>/dev/null || exit 1
fi

export PYTHONPATH="${BUILD}${PYTHONPATH:+:${PYTHONPATH}}"
export LD_LIBRARY_PATH="${BUILD}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"

echo "APRILTAG_ROOT=${APRILTAG_ROOT}"
echo "PYTHONPATH (prepended) ${BUILD}"
echo "LD_LIBRARY_PATH (prepended) ${BUILD}"
