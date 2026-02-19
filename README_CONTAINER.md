# SLRC 2026 Simulation - Container Setup

This guide explains how to run the simulation with Gazebo on the host and the Bridge/API stack in a Docker container.

## Prerequisites
- **Host Machine**: Ubuntu 22.04 with ROS 2 Humble & Gazebo Ignition/Sim Fortress.
- **Docker**: Installed and running.

## 1. Setup Host Environment
Build the workspace on the host to ensure Gazebo assets are available.
```bash
cd ~/slrc_ws
colcon build --packages-select slrc_tron_sim slrc_sim_bridge
source install/setup.bash
```

## 2. Start Host Simulation
Use the same ROS domain as the container so host and container see the same ROS 2 topics:
```bash
export ROS_DOMAIN_ID=10
ros2 launch slrc_sim_bridge host_sim.launch.py
```
- The launch file sets `IGN_PARTITION=slrc_sim` so Gazebo and the container bridge use the same Ignition Transport partition.
- **Verify**: Gazebo opens, showing the arena and two robots (Red and Yellow).

## 3. Build & Run Bridge Container

### Build Container (First time or after updates)
```bash
cd ~/slrc_ws
./scripts/build_container.sh
```

### Run Container
```bash
./scripts/run_container.sh
```
- **Verify**: The container starts and logs show "Starting API Service on port 8000" and "8001".

## 4. Run Controller
In a third terminal (on the host), run the hostile controller script. It connects to the API exposed by the container.
```bash
source install/setup.bash
python3 src/slrc_sim_bridge/scripts/hostile_controller.py
```

## Troubleshooting
- **Network Issues**: If the controller cannot connect, ensure you are using `--net=host` (default in `run_container.sh`).
- **ROS 2 (DDS)**: Host and container must use the same `ROS_DOMAIN_ID`. The container uses `10`; run `export ROS_DOMAIN_ID=10` on the host before launching `host_sim.launch.py` and before running `ros2 topic list` or the controller.
- **Gazebo–Bridge (Ignition Transport)**: The bridge in the container and Gazebo on the host must use the same **Ignition Transport partition**. `host_sim.launch.py` sets `IGN_PARTITION=slrc_sim`, and `run_container.sh` passes `IGN_PARTITION=slrc_sim` into the container. If you override `IGN_PARTITION` on the host, set the same value when running the container (e.g. `IGN_PARTITION=slrc_sim ./scripts/run_container.sh`). If partition differs, you get no odom/cameras (503) and robots do not move.
