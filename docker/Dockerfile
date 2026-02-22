FROM ros:humble-ros-base

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]

# ROS + Gazebo Sim + Bridge
RUN apt-get update && apt-get install -y \
    ros-humble-ros-gz-sim \
    ros-humble-ros-gz-bridge \
    ros-humble-robot-state-publisher \
    python3-pip \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
    fastapi \
    uvicorn \
    pyyaml \
    opencv-python-headless \
    requests

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

CMD ["ros2", "launch", "slrc_sim_bridge", "container_full.launch.py"]
