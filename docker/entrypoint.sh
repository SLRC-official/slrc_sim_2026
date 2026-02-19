#!/bin/bash
set -e

export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-10}
# Ignition Transport: same partition for Gazebo and ros_gz_bridge (container_full.launch.py)
export IGN_PARTITION=${IGN_PARTITION:-slrc_sim}
source /opt/ros/humble/setup.bash
source /root/ws/install/setup.bash

exec "$@"
