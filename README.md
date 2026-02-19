# SLRC 2026 Simulation – Contestant Guide

Run the Tron simulation (Gazebo arena + Ares and Hostile robots) in Docker and control it from your machine via a REST API.

## Requirements

- **OS**: Ubuntu 20 or higher / Mac (haven't tested)
- **Other**: Docker, and for running the test/controller scripts: Python 3 and `requests` (e.g. `pip install requests`). For the Gazebo window to appear you need a display (on Linux/Mac: X11/Wayland display systems).

## Run the simulation

From the workspace folder (`slrc_ws`):

**1. Build the image (once, or after updates)**  
```bash
./scripts/build_container.sh
```

**2. Start the simulation**  
```bash
./scripts/run_container.sh
```

- A Gazebo window opens with the arena and two robots (Ares = red, Hostile = yellow/green).
- The API starts inside the container. Leave this terminal open.
- When you see logs like `Uvicorn running on http://0.0.0.0:8000`, the API is ready.

**3. Use the API from your machine**

- **Team API (control Ares)**: `http://localhost:8000`
- **Hostile API**: `http://localhost:8001`

Example: test that the API and basic commands work:
```bash
python3 src/slrc_sim_bridge/test_api.py
```

Run the hostile controller (predefined path):
```bash
python3 src/slrc_sim_bridge/scripts/hostile_controller.py
```

Can also send HTTP requests from your own code to `localhost:8000` (or 8001) for velocity commands, odometry, camera images, and arena metadata (Start Location etc). Use the test_api as example for now

## Troubleshooting

| Problem | What to do |
|--------|------------|
| **No Gazebo window** | Allow display access: run `xhost +local:docker` in a terminal, then start the container again. On Wayland, you may need to use an X server (e.g. Xwayland). |
| **“Connection refused” to the API** | Wait until the container logs show “Uvicorn running on http://0.0.0.0:8000”. If it still fails, ensure you didn’t change the container’s network (the run script uses the host network so the API is on localhost). |
| **Robots don’t move / odom or cameras return errors** | Use the default run: `./scripts/run_container.sh` without changing the command. The image is set up so the sim and API run together correctly. |

## Quick reference

| Step | Command |
|------|--------|
| Build (once) | `./scripts/build_container.sh` |
| Start sim + API | `./scripts/run_container.sh` |
| Test API | `python3 src/slrc_sim_bridge/test_api.py` |
| Hostile controller | `python3 src/slrc_sim_bridge/scripts/hostile_controller.py` |

API base URLs: **http://localhost:8000** (team/Ares), **http://localhost:8001** (hostile).
