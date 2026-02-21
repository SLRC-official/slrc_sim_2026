#!/bin/bash
# Run the SLRC simulation container (Gazebo + bridge + API in one launch).

set -e
cd "$(dirname "$0")/.."

CONTAINER_NAME="${SLRC_CONTAINER_NAME:-slrc_sim_container}"
IMAGE_NAME="${SLRC_IMAGE_NAME:-slrc_bridge}"

export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-10}
export IGN_PARTITION=${IGN_PARTITION:-slrc_sim}

echo "Starting container '$CONTAINER_NAME' (image: $IMAGE_NAME)."
echo "  - Gazebo + spawn + bridge + API (single launch, same partition)."
echo "  - API: test_api.py, hostile_controller.py, view_cameras.py (localhost:8000 / 8001)."
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
