#!/bin/bash
set -e

export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-10}
# Ignition Transport: must match host_sim.launch.py so ros_gz_bridge and Gazebo communicate
export IGN_PARTITION=${IGN_PARTITION:-slrc_sim}
source /opt/ros/humble/setup.bash
source /root/ws/install/setup.bash

exec "$@"
