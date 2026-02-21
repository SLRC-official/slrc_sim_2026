#!/bin/bash
set -e

export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-10}
export IGN_PARTITION=${IGN_PARTITION:-slrc_sim}

# If host DISPLAY causes GL/EGL failures, use Xvfb virtual display instead.
# Set USE_XVFB=1 or leave DISPLAY unset to force Xvfb (VNC on port 5900 for viewing).
# CPU-only rendering via Mesa llvmpipe - no GPU needed.
if [ "${USE_XVFB}" = "1" ] || [ -z "${DISPLAY}" ] || [ "${DISPLAY}" = " " ]; then
    export GALLIUM_DRIVER=llvmpipe
    Xvfb :99 -screen 0 1280x720x24 &
    XVFB_PID=$!
    export DISPLAY=:99
    # Optional: x11vnc to view the GUI (connect with vncviewer localhost:5900)
    if command -v x11vnc &>/dev/null; then
        x11vnc -display :99 -nopw -forever -xkb -rfbport 5900 &
    fi
fi

source /opt/ros/humble/setup.bash
source /root/ws/install/setup.bash

exec "$@"
