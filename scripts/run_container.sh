#!/bin/bash

# Run the container
echo "Running container..."

# Set ROS Domain ID to 10 as requested
export ROS_DOMAIN_ID=10

# Ignition Transport partition: must match host_sim.launch.py so bridge and Gazebo see each other
export IGN_PARTITION=${IGN_PARTITION:-slrc_sim}

docker run -it --rm \
    --net=host \
    --ipc=host \
    --pid=host \
    -e ROS_DOMAIN_ID=10 \
    -e IGN_PARTITION \
    --name slrc_bridge_container \
    slrc_bridge
