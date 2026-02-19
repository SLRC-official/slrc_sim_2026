FROM ros:humble-ros-base

# Env setup
ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]

# Install dependencies
RUN apt-get update && apt-get install -y \
    ros-humble-ros-gz-bridge \
    python3-pip \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
RUN pip3 install \
    fastapi \
    uvicorn \
    pyyaml \
    opencv-python-headless \
    requests

# Create workspace
WORKDIR /root/ws/src
COPY src/slrc_sim_bridge /root/ws/src/slrc_sim_bridge


WORKDIR /root/ws

# Build
RUN source /opt/ros/humble/setup.bash && \
    colcon build && \
    source install/setup.bash

# Entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

CMD ["ros2", "launch", "slrc_sim_bridge", "container_bridge.launch.py"]
