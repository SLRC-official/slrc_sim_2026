#!/usr/bin/env bash

source ~/venvs/ros2/bin/activate

WS=~/slrc_ws

# scikit-build-core (in /usr/local) registers setuptools entry points that
# need typing-extensions, exceptiongroup, etc. which live in ~/.local.
# Colcon spawns /usr/bin/python3 subprocesses that may not see user
# site-packages, so we explicitly add it to PYTHONPATH.
export PYTHONPATH="$HOME/.local/lib/python3.10/site-packages${PYTHONPATH:+:$PYTHONPATH}"

echo ">>> Cleaning build, install, log in $WS"
rm -rf "$WS/build" "$WS/install" "$WS/log"

echo ">>> Sourcing base ROS (adjust distro if needed)"
source /opt/ros/humble/setup.sh

echo ">>> Building workspace"
cd "$WS"
# Omit --symlink-install: colcon passes "setup.py develop --editable", which
# needs setuptools>=64 on the same interpreter as colcon (usually
# /usr/bin/python3). Stock Ubuntu setuptools is older and errors with:
# "option --editable not recognized". Re-add --symlink-install after
# `python3 -m pip install --user "setuptools>=64"` if you need live edits
# without rebuild.
colcon build

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

api_node="$WS/install/slrc_sim_bridge/lib/slrc_sim_bridge/api_node"
if [[ -f "$api_node" ]]; then
    echo ">>> Patching api_node shebang to use venv python..."
    sed -i '1s|^#!.*python.*$|#!/home/kirangunathilaka/venvs/ros2/bin/python|' "$api_node"
    echo ">>> Patch applied."
else
    echo ">>> Skipping api_node shebang patch (install tree missing or build failed)."
fi