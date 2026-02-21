#!/bin/bash
# Run the SLRC simulation container (Gazebo + bridge + API in one launch).

set -e
cd "$(dirname "$0")/.."

CONTAINER_NAME="${SLRC_CONTAINER_NAME:-slrc_sim_container}"
IMAGE_NAME="${SLRC_IMAGE_NAME:-slrc_bridge}"

export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-10}
export IGN_PARTITION=${IGN_PARTITION:-slrc_sim}

# Use Xvfb inside container when host display causes GL/EGL failures (cameras 503).
# To use host display instead, run: DISPLAY=:0 ./scripts/run_container.sh
# (may still hit "failed to create drawable" on some systems)
export USE_XVFB="${USE_XVFB:-1}"

# Optional: GPU for faster rendering. Requires nvidia-container-toolkit.
# If set, the container entrypoint could skip LIBGL_ALWAYS_SOFTWARE when GPU is present.
GPU_ARGS=()
if command -v nvidia-smi &>/dev/null && nvidia-smi -L &>/dev/null; then
    GPU_ARGS=(--gpus all)
fi

echo "Starting container '$CONTAINER_NAME' (image: $IMAGE_NAME)."
echo "  - Gazebo + spawn + bridge + API start together (single launch, same partition)."
echo "  - Using Xvfb for display (cameras + GUI). To view Gazebo: vncviewer localhost:5900"
echo "  - API: test_api.py, hostile_controller.py, view_cameras.py (localhost:8000 / 8001)."
echo ""

docker run --rm \
    --net=host \
    --ipc=host \
    --pid=host \
    -e USE_XVFB \
    -e ROS_DOMAIN_ID \
    -e IGN_PARTITION \
    -e DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    "${GPU_ARGS[@]}" \
    --name "$CONTAINER_NAME" \
    "$IMAGE_NAME"
