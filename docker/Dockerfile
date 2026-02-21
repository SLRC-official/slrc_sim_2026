# SLRC 2026: Full simulation + bridge in one container
# Gazebo + spawn at startup; bridge + API via docker exec
FROM ros:humble-ros-base

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]

# ROS + Gazebo Sim + Bridge + GUI (Xvfb for virtual display when host GL fails)
RUN apt-get update && apt-get install -y \
    ros-humble-ros-gz-sim \
    ros-humble-ros-gz-bridge \
    ros-humble-robot-state-publisher \
    python3-pip \
    libopencv-dev \
    libgl1-mesa-glx \
    libegl1-mesa \
    libxcb-xinerama0 \
    xvfb \
    x11vnc \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
    fastapi \
    uvicorn \
    pyyaml \
    opencv-python-headless \
    requests

# Workspace: both sim assets and bridge
WORKDIR /root/ws/src
COPY src/slrc_tron_sim /root/ws/src/slrc_tron_sim
COPY src/slrc_sim_bridge /root/ws/src/slrc_sim_bridge

WORKDIR /root/ws
RUN source /opt/ros/humble/setup.bash && \
    colcon build && \
    source install/setup.bash

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Single launch: Gazebo + spawn + bridge + API (same IGN_PARTITION so they communicate)
CMD ["ros2", "launch", "slrc_sim_bridge", "container_full.launch.py"]
