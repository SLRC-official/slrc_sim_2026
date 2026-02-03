# Acceptance Test Plan

## 1. Environment Setup
- [ ] Launch Simulation: `ros2 launch slrc_sim_bridge contest_launch.py team_name:=test_team`
- [ ] Verify Gazebo window opens and robot marks spawn.
- [ ] Verify API is reachable: `curl http://localhost:8000/` -> returns `{"status": "running", "team": "test_team"}`

## 2. Locomotion Limits & Control
- [ ] **Velocity Command**:
  - Send `POST /set_velocity` `{"vx": 0.5, "vy": 0, "omega": 0}`.
  - Observe robot moves forward in Gazebo.
  - Send `{"vx": 0, ...}` to stop.
- [ ] **Relative Move**:
  - Send `POST /move_relative` `{"dx": 1.0, "dy": 0, "dtheta": 0}`.
  - Verify robot moves approx 1.0m and stops.
  - Verify `{"status": "started"}` response.
  - Verify status changes to idle or robot stops after completion.

## 3. Sensors
- [ ] **Odometry**:
  - Move robot.
  - Call `GET /odometry`.
  - Verify values change consistent with movement.
- [ ] **Cameras**:
  - Open `http://localhost:8000/camera/front_left/stream` in browser.
  - Open `http://localhost:8000/camera/front_right/stream`.
  - Open `http://localhost:8000/camera/floor/stream`.
  - Verify images are updating and correctly oriented.

## 4. Utilities
- [ ] **LED**:
  - Send `POST /utility/set_led` `{"state": "on", "color": "blue"}`.
  - Verify topic `/led_cmd` (via `ros2 topic echo /test_team/led_cmd`).
- [ ] **Path Marker**:
  - Send `POST /utility/mark_path` `{"points": [[0,0], [1,0]], "type": "polyline"}`.
  - Verify Marker in RViz (if open) on topic `/visualization_marker` (namespaced?).
  
## 5. Safety
- [ ] **Watchdog**:
  - Send velocity command.
  - Disconnect/Stop sending commands.
  - Verify robot stops after 1.0s (default timeout).
- [ ] **Isolation** (Multi-team):
  - Launch Team 1 and Team 2 (different ports/namespaces).
  - Send command to Team 1.
  - Verify Team 2 does NOT move.
