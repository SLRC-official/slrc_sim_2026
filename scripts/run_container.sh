#!/bin/bash
set -e
cd "$(dirname "$0")/.."

CONTAINER_NAME="${SLRC_CONTAINER_NAME:-slrc_sim_container}"
IMAGE_NAME="${SLRC_IMAGE_NAME:-slrc_bridge}"

export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-10}
export IGN_PARTITION=${IGN_PARTITION:-slrc_sim}

# Allow Docker to open GUI windows (Gazebo). Required for display to work.
xhost +local:docker 2>/dev/null || true

echo "Starting container '$CONTAINER_NAME'..."
echo "  API: localhost:8000 | Hostile: python3 utils/hostile_controller.py"
echo ""

docker run --rm \
    --net=host \
    --ipc=host \
    --pid=host \
    -e ROS_DOMAIN_ID \
    -e IGN_PARTITION \
    -e DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    --name "$CONTAINER_NAME" \
    "$IMAGE_NAME"
