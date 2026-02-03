#!/usr/bin/env bash

source ~/venvs/ros2/bin/activate

export PYTHONNOUSERSITE=1
WS=~/slrc_ws

echo ">>> Cleaning build, install, log in $WS"
rm -rf "$WS/build" "$WS/install" "$WS/log"

echo ">>> Sourcing base ROS (adjust distro if needed)"
source /opt/ros/humble/setup.sh

echo ">>> Building workspace (symlink install)"
cd "$WS"
colcon build --symlink-install

echo ">>> Sourcing workspace overlay"
source "$WS/install/setup.sh"

echo ">>> Setting Gazebo model path"
PREFIX=$(ros2 pkg prefix slrc_tron_sim)
export GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH:$PREFIX/share

echo ">>> Gazebo path now:"
echo "$GZ_SIM_RESOURCE_PATH"

echo ">>> Done. You're now in: $WS"

export GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH:$(ros2 pkg prefix slrc_tron_sim)/share
export IGN_GAZEBO_RESOURCE_PATH=$IGN_GAZEBO_RESOURCE_PATH:$(ros2 pkg prefix slrc_tron_sim)/share