#!/bin/bash
# Run the SLRC simulation container (Gazebo + bridge + API in one launch).

set -e
cd "$(dirname "$0")/.."

CONTAINER_NAME="${SLRC_CONTAINER_NAME:-slrc_sim_container}"
IMAGE_NAME="${SLRC_IMAGE_NAME:-slrc_bridge}"

export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-10}
export IGN_PARTITION=${IGN_PARTITION:-slrc_sim}

# X11 display forwarding so Gazebo GUI appears on host
DISPLAY="${DISPLAY:-:0}"
xhost +local:docker 2>/dev/null || true

echo "Starting container '$CONTAINER_NAME' (image: $IMAGE_NAME)."
echo "  - Gazebo + spawn + bridge + API start together (single launch, same partition)."
echo "  - Once up, use test_api.py or hostile_controller.py on the host (localhost:8000 / 8001)."
echo ""

docker run --rm \
    --net=host \
    --ipc=host \
    --pid=host \
    -e DISPLAY="$DISPLAY" \
    -e ROS_DOMAIN_ID \
    -e IGN_PARTITION \
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
    --name "$CONTAINER_NAME" \
    "$IMAGE_NAME"
