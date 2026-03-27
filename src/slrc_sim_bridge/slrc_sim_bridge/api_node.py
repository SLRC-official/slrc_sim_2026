#!/usr/bin/env python3
"""SLRC 2026 API Service. REST API for robot control, odometry, cameras, arena metadata."""

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, Imu
from std_msgs.msg import String
from visualization_msgs.msg import Marker
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

import os
import re
import shutil
import subprocess
import tempfile
import threading
import uvicorn
import yaml
from pathlib import Path
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
import cv2
import numpy as np
import time
import math
from typing import Any, Dict, List, Optional, Tuple

from ament_index_python.packages import get_package_share_directory

from slrc_sim_bridge.utils.trajectory import TrapezoidalProfile
from slrc_sim_bridge.config import AresConfig, ArenaConfig, HostileConfig


class VelocityCommand(BaseModel):
    velocity: float
    omega: float = 0.0


class MoveRelativeCommand(BaseModel):
    distance: float
    rotation: float = 0.0


class LedCommand(BaseModel):
    state: str
    color: str


class SimpleLedCommand(BaseModel):
    state: int


class PathMarkerCommand(BaseModel):
    points: list
    type: str = "polyline"


class PortalSettingsUpdate(BaseModel):
    count: Optional[int] = None
    trigger: Optional[bool] = None


class PortalEspTrigger(BaseModel):
    trigger: bool


class AprilTagPayload(BaseModel):
    raw: str
    order: int
    x: int
    y: int


class ResetAprilTagsPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    password: str = Field(alias="pass")


class ApiServiceNode(Node):
    """REST + ROS node. LED sync uses Ignition Fortress `ign service` (ign_msgs.* types)."""

    _GZ_WORLD = 'slrc_arena_from_image'
    # sdformat merges fixed joints into one link; LED geometry ends up on base_footprint with
    # mangled visual names. Matches `ign sdf -p ares.urdf` (not raw URDF link led_link).
    _LED_LUMP_LINK = 'base_footprint'
    _LED_DOME_VISUAL_SDF = 'base_footprint_fixed_joint_lump__led_dome_vis_visual_2'

    def __init__(self):
        super().__init__('api_service')

        # Parameters
        self.declare_parameter('port', 8000)
        self.declare_parameter('start_x', 2.0)
        self.declare_parameter('start_y', 2.0)
        self.declare_parameter('watchdog_timeout', 1.0)
        self.declare_parameter('arena_config_file', '')
        self.declare_parameter('robot_name', 'ares')
        self.declare_parameter('led_lump_link', '')
        self.declare_parameter('led_dome_visual', '')

        self.api_port = self.get_parameter('port').value
        self.start_x = self.get_parameter('start_x').value
        self.start_y = self.get_parameter('start_y').value
        self.watchdog_timeout = self.get_parameter('watchdog_timeout').value
        self.robot_name = self.get_parameter('robot_name').value
        arena_config_path = self.get_parameter('arena_config_file').value

        self._led_lump_link = self._LED_LUMP_LINK
        self._led_dome_visual_sdf = self._LED_DOME_VISUAL_SDF
        if self.robot_name == 'ares':
            lump_ov = str(self.get_parameter('led_lump_link').value or '').strip()
            vis_ov = str(self.get_parameter('led_dome_visual').value or '').strip()
            if lump_ov and vis_ov:
                self._led_lump_link = lump_ov
                self._led_dome_visual_sdf = vis_ov
            else:
                r_link, r_vis = self._resolve_led_sdf_names_from_urdf()
                if r_link and r_vis:
                    self._led_lump_link = r_link
                    self._led_dome_visual_sdf = r_vis

        # Load arena configuration
        self.arena_config = self._load_arena_config(arena_config_path)

        self.get_logger().info(f"Starting API Service on port {self.api_port}")

        self.cmd_vel_pub = self.create_publisher(Twist, f'/{self.robot_name}/cmd_vel', 10)
        self.marker_pub = self.create_publisher(Marker, 'visualization_marker', 10)
        self.led_pub = self.create_publisher(String, 'led_cmd', 10)

        odom_topic = f'{self.robot_name}/odom'
        self.get_logger().info(f"Subscribing to odometry topic: '{odom_topic}'")
        self.create_subscription(Odometry, odom_topic, self.odom_callback, qos_profile_sensor_data)
        self.create_subscription(Image, f'{self.robot_name}/front_left/image_raw', self.cam_fl_callback, qos_profile_sensor_data)
        self.create_subscription(Image, f'{self.robot_name}/front_right/image_raw', self.cam_fr_callback, qos_profile_sensor_data)
        self.create_subscription(Image, f'{self.robot_name}/floor/image_raw', self.cam_floor_callback, qos_profile_sensor_data)
        self.create_subscription(Imu, f'{self.robot_name}/imu/data', self.imu_callback, qos_profile_sensor_data)
        self.hostile_position = None
        self.create_subscription(Odometry, '/hostile/odom', self.hostile_position_callback, 10)

        # State
        self.current_odom = None
        self.current_imu = None
        self.led_state = 0
        self.latest_frames = {
            'front_left': None,
            'front_right': None,
            'floor': None
        }

        # Movement Control
        self.active_move_thread = None
        self.stop_requested = False
        self.last_command_time = time.time()

        # Portal + AprilTag HTTP state (thread-safe; in-memory per API process)
        self._portal_apriltag_lock = threading.Lock()
        self._portal_settings: Dict[str, Any] = {"count": 0, "trigger": False}
        self._april_tags: List[Dict[str, Any]] = []

        # Watchdog Thread
        self.watchdog_thread = threading.Thread(target=self.watchdog_loop, daemon=True)
        self.watchdog_thread.start()

        # Initialize FastAPI
        self.app = FastAPI(
            title="SLRC 2026 Robot API",
            description=f"API for controlling the {self.robot_name} robot in the SLRC competition",
            version="1.0.0"
        )
        
        # CORS middleware for web clients
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self.setup_routes()

    def _load_arena_config(self, config_path: str) -> dict:
        """Load arena configuration from YAML file."""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                self.get_logger().warn(f"Failed to load arena config: {e}")
        
        # Return minimal default config based on Config class
        return {
            'arena': {
                'grid_size': ArenaConfig.GRID_SIZE,
                'cell_size': ArenaConfig.CELL_SIZE,
                'grid_span': ArenaConfig.GRID_SPAN
            },
            'locations': {
                'start_cell': [2, 24],
            }
        }

    def setup_routes(self):
        @self.app.get("/")
        async def root():
            """Health check and basic info."""
            return {
                "status": "running",
                "robot": self.robot_name,
                "team": self.get_namespace().strip('/'),
                "api_version": "1.0.0"
            }

        @self.app.get("/health")
        async def health():
            """Detailed health check."""
            return {
                "status": "healthy",
                "odom_available": self.current_odom is not None,
                "cameras": {k: v is not None for k, v in self.latest_frames.items()},
                "hostile_tracking": self.hostile_position is not None
            }

        # Motion Control Routes
        @self.app.post("/set_velocity")
        async def set_velocity(cmd: VelocityCommand):
            """Set robot velocity (differential drive) with limits."""
            self.stop_requested = True
            if self.active_move_thread and self.active_move_thread.is_alive():
                self.active_move_thread.join(timeout=0.1)

            # Clamp velocities
            if self.robot_name == 'hostile':
                max_v = HostileConfig.MAX_LINEAR_VEL
                max_w = HostileConfig.MAX_ANGULAR_VEL
            else:
                max_v = AresConfig.MAX_LINEAR_VEL
                max_w = AresConfig.MAX_ANGULAR_VEL

            v = max(-max_v, min(max_v, cmd.velocity))
            w = max(-max_w, min(max_w, cmd.omega))

            self.publish_cmd_vel(v, w)
            return {"status": "executed", "velocity": v, "omega": w}

        @self.app.post("/stop")
        async def stop():
            """Emergency stop - immediately stops the robot."""
            self.stop_requested = True
            self._publish_stop()
            return {"status": "stopped"}

        @self.app.post("/move_relative")
        async def move_relative(cmd: MoveRelativeCommand):
            """Execute a relative move using trapezoidal velocity profiles."""
            if self.active_move_thread and self.active_move_thread.is_alive():
                return JSONResponse(
                    status_code=409,
                    content={"error": "Move already in progress"}
                )

            self.stop_requested = False
            self.active_move_thread = threading.Thread(
                target=self.execute_move_relative, args=(cmd,)
            )
            self.active_move_thread.start()
            return {"status": "started", "distance": cmd.distance, "rotation": cmd.rotation}

        # Sensor Routes
        @self.app.get("/odometry")
        async def get_odometry():
            """Get current robot odometry (pose and velocity)."""
            if self.current_odom is None:
                self.get_logger().warn(f"Odometry requested but not available for {self.robot_name} (topic: {self.robot_name}/odom)")
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "No odometry data available. "
                        "Start the simulation and ROS–Gazebo bridge so they publish to "
                        f"topic '{self.robot_name}/odom'."
                    )
                )

            p = self.current_odom.pose.pose.position
            o = self.current_odom.pose.pose.orientation
            v = self.current_odom.twist.twist.linear
            w = self.current_odom.twist.twist.angular

            # Convert quaternion to yaw
            yaw = self._quaternion_to_yaw(o)

            return {
                "pose": {
                    "x": p.x, "y": p.y, "z": p.z,
                    "yaw": yaw,
                    "orientation": {"x": o.x, "y": o.y, "z": o.z, "w": o.w}
                },
                "velocity": {"linear": v.x, "angular": w.z}
            }

        @self.app.get("/imu")
        async def get_imu():
            """Get current IMU readings."""
            if self.current_imu is None:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "No IMU data available. "
                        "Start the simulation and ROS–Gazebo bridge so they publish to "
                        f"topic '/{self.robot_name}/imu/data'."
                    )
                )

            return {
                "angular_velocity": {
                    "x": self.current_imu.angular_velocity.x,
                    "y": self.current_imu.angular_velocity.y,
                    "z": self.current_imu.angular_velocity.z
                },
                "linear_acceleration": {
                    "x": self.current_imu.linear_acceleration.x,
                    "y": self.current_imu.linear_acceleration.y,
                    "z": self.current_imu.linear_acceleration.z
                }
            }

        # Camera Routes
        @self.app.get("/camera/{cam_id}/frame")
        async def camera_frame(cam_id: str):
            """Get a single JPEG frame from the specified camera."""
            if cam_id not in self.latest_frames:
                raise HTTPException(status_code=404, detail="Camera not found")

            frame = self.latest_frames.get(cam_id)
            if frame is None:
                raise HTTPException(status_code=503, detail="No frame available")

            return StreamingResponse(
                iter([frame]),
                media_type="image/jpeg"
            )

        @self.app.get("/camera/{cam_id}/stream")
        async def camera_stream(cam_id: str):
            """MJPEG stream from the specified camera."""
            if cam_id not in self.latest_frames:
                raise HTTPException(status_code=404, detail="Camera not found")
            return StreamingResponse(
                self.generate_mjpeg(cam_id),
                media_type="multipart/x-mixed-replace; boundary=frame"
            )

        # Arena Routes
        @self.app.get("/arena/metadata")
        async def get_arena_metadata():
            """Get arena configuration metadata."""
            arena = self.arena_config.get('arena', {})
            locations = self.arena_config.get('locations', {})
            
            return {
                "grid_size": arena.get('grid_size', ArenaConfig.GRID_SIZE),
                "cell_size": arena.get('cell_size', ArenaConfig.CELL_SIZE),
                "grid_span": arena.get('grid_span', ArenaConfig.GRID_SPAN),
                "start_cell": locations.get('start_cell', [2, 24]),
                "start_world": {"x": self.start_x, "y": self.start_y}
            }

        @self.app.get("/hostile/position")
        async def get_hostile_position():
            """Get current hostile robot position."""
            if self.hostile_position is None:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Hostile position not available. "
                        "Start the hostile controller so it publishes to topic '/hostile/odom'."
                    )
                )
            
            p = self.hostile_position.pose.pose.position
            o = self.hostile_position.pose.pose.orientation
            yaw = self._quaternion_to_yaw(o)
            
            return {
                "x": p.x,
                "y": p.y,
                "yaw": yaw,
                }

        @self.app.get("/start_coordinate")
        async def get_start_coordinate():
            """Get the ego robot start position in world coordinates."""
            return {"x": self.start_x, "y": self.start_y}

        # Utility Routes
        @self.app.post("/utility/set_led")
        async def set_led(cmd: LedCommand):
            """Set robot LED state and color."""
            msg = String()
            msg.data = f"{cmd.state}:{cmd.color}"
            self.led_pub.publish(msg)
            return {"status": "led_command_sent", "cmd": msg.data}

        @self.app.post("/led")
        async def set_led_state(cmd: SimpleLedCommand):
            """Turn LED on (1) or off (0)."""
            self.led_state = 1 if cmd.state else 0
            self._set_led_visual(self.led_state)
            return {"status": "ok", "led": self.led_state}

        @self.app.get("/led")
        async def get_led_state():
            """Get current LED state."""
            return {"led": self.led_state}

        @self.app.post("/utility/mark_path")
        async def mark_path(cmd: PathMarkerCommand):
            """Draw a path marker in the simulation (for debugging)."""
            marker = Marker()
            marker.header.frame_id = "odom"
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "path_marker"
            marker.id = 0
            marker.type = Marker.LINE_STRIP
            marker.action = Marker.ADD
            marker.scale.x = 0.05
            marker.color.a = 1.0
            marker.color.r = 1.0
            marker.color.g = 1.0

            from geometry_msgs.msg import Point
            for p in cmd.points:
                pt = Point()
                pt.x = float(p[0])
                pt.y = float(p[1])
                pt.z = 0.01
                marker.points.append(pt)

            self.marker_pub.publish(marker)
            return {"status": "marker_published"}

        @self.app.get("/get_num_boxes_portal")
        async def get_num_boxes_portal():
            """Portal box count and trigger."""
            with self._portal_apriltag_lock:
                return dict(self._portal_settings)

        @self.app.post("/set_num_boxes_portal")
        async def set_num_boxes_portal(body: PortalSettingsUpdate):
            """Set portal count/trigger from GUI or automation."""
            with self._portal_apriltag_lock:
                if body.count is not None:
                    self._portal_settings["count"] = body.count
                if body.trigger is not None:
                    self._portal_settings["trigger"] = body.trigger
            return {"status": "success"}

        @self.app.post("/set_num_boxes_portal_esp")
        async def set_num_boxes_portal_esp(body: PortalEspTrigger):
            """External ESP-style trigger update (trigger only)."""
            with self._portal_apriltag_lock:
                self._portal_settings["trigger"] = body.trigger
            return {"status": "trigger_updated"}

        @self.app.post("/april_tag")
        async def post_april_tag(body: AprilTagPayload):
            """Append one AprilTag report (raw + decoded coordinates)."""
            entry = {
                "raw": body.raw,
                "order": body.order,
                "x": body.x,
                "y": body.y,
            }
            with self._portal_apriltag_lock:
                self._april_tags.append(entry)
            return {"status": "received"}

        @self.app.get("/get_april_tag")
        async def get_april_tag():
            """List all cached AprilTag reports."""
            with self._portal_apriltag_lock:
                return {"data": list(self._april_tags)}

        @self.app.post("/reset_april_tag")
        async def reset_april_tag(body: ResetAprilTagsPayload):
            """Clear AprilTag cache (password required)."""
            if body.password != "slrc_is_the_best":
                raise HTTPException(status_code=401, detail="unauthorized")
            with self._portal_apriltag_lock:
                self._april_tags.clear()
            return {"status": "cleared"}

    def odom_callback(self, msg: Odometry):
        if self.current_odom is None:
            self.get_logger().info(f"First odometry received for {self.robot_name}!")
        self.current_odom = msg

    def cam_fl_callback(self, msg: Image):
        self.latest_frames['front_left'] = self._process_image(msg)

    def cam_fr_callback(self, msg: Image):
        self.latest_frames['front_right'] = self._process_image(msg)

    def cam_floor_callback(self, msg: Image):
        self.latest_frames['floor'] = self._process_image(msg)

    def imu_callback(self, msg: Imu):
        self.current_imu = msg

    def hostile_position_callback(self, msg: Odometry):
        self.hostile_position = msg

    def _process_image(self, msg: Image) -> bytes:
        try:
            # Basic conversion for BGR8/RGB8
            if msg.encoding == 'bgr8':
                img = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
            elif msg.encoding == 'rgb8':
                img = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            else:
                # Fallback for other encodings if needed
                return None
            _, jpeg = cv2.imencode('.jpg', img)
            return jpeg.tobytes()
        except Exception as e:
            self.get_logger().error(f"Image processing error: {e}")
            return None

    def generate_mjpeg(self, cam_id: str):
        while True:
            frame = self.latest_frames.get(cam_id)
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)

    def _resolve_led_sdf_names_from_urdf(self) -> Tuple[str, str]:
        """Align LED entity names with this machine's sdformat URDF→SDF merge (differs by version)."""
        try:
            pkg = get_package_share_directory('slrc_tron_sim')
        except LookupError:
            self.get_logger().debug('slrc_tron_sim share not found; using default LED entity names')
            return ('', '')
        urdf_path = os.path.join(pkg, 'urdf', 'ares.urdf')
        if not os.path.isfile(urdf_path):
            return ('', '')
        try:
            with open(urdf_path, 'r', encoding='utf-8') as f:
                urdf_text = f.read()
        except OSError:
            return ('', '')
        urdf_text = urdf_text.replace('package://slrc_tron_sim', pkg)
        binaries = []
        ign = shutil.which('ign')
        gz = shutil.which('gz')
        if ign:
            binaries.append(ign)
        if gz and gz != ign:
            binaries.append(gz)
        for binary in binaries:
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.urdf', delete=False, encoding='utf-8'
                ) as tf:
                    tf.write(urdf_text)
                    tmp_path = tf.name
                proc = subprocess.run(
                    [binary, 'sdf', '-p', tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=30.0,
                )
                if proc.returncode != 0:
                    continue
                current_link = None
                for line in proc.stdout.splitlines():
                    lm = re.search(r"<link name='([^']+)'", line)
                    if lm:
                        current_link = lm.group(1)
                        continue
                    vm = re.search(r"<visual name='([^']*led_dome[^']*)'", line)
                    if vm and current_link:
                        vis = vm.group(1)
                        self.get_logger().info(
                            f'Resolved LED SDF names via {binary}: '
                            f'link={current_link!r} visual={vis!r}'
                        )
                        return (current_link, vis)
            except (subprocess.SubprocessError, OSError):
                continue
            finally:
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
        self.get_logger().warn(
            'Could not resolve LED dome visual via ign/gz sdf -p; using built-in defaults'
        )
        return ('', '')

    def _ign_cli_env(self):
        """Match partition with container_sim.launch.py / entrypoint.sh."""
        env = os.environ.copy()
        env.setdefault('IGN_PARTITION', 'slrc_sim')
        env.setdefault('GZ_PARTITION', 'slrc_sim')
        return env

    def _ign_service(self, service: str, reqtype: str, reptype: str, req: str) -> bool:
        """Call `ign service` or `gz service` (Gazebo Sim 6; ign_msgs.* types in CLI)."""
        binaries = []
        for b in (shutil.which('ign'), shutil.which('gz')):
            if b and b not in binaries:
                binaries.append(b)
        if not binaries:
            self.get_logger().warn(
                'Neither ign nor gz CLI found; LED will not update in Gazebo. '
                'Install gz/ign tools (e.g. ros-humble-ros-gz-sim dependencies).'
            )
            return False
        for binary in binaries:
            try:
                proc = subprocess.run(
                    [
                        binary,
                        'service',
                        '-s', service,
                        '--reqtype', reqtype,
                        '--reptype', reptype,
                        '--timeout', '2500',
                        '--req', req,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                    env=self._ign_cli_env(),
                )
                if proc.returncode == 0:
                    return True
                self.get_logger().debug(
                    f'{binary} service {service} rc={proc.returncode} '
                    f'err={proc.stderr!r} out={proc.stdout!r}'
                )
            except (subprocess.SubprocessError, OSError) as e:
                self.get_logger().debug(f'{binary} service failed: {e}')
                continue
        self.get_logger().warn(f'service call failed for {service} (tried: {binaries})')
        return False

    def _set_led_visual(self, on: int):
        """Dome emissive + point light intensity via UserCommands (Fortress).

        UserCommands.cc looks up entities via ECM components::Name() which
        stores the LOCAL (unscoped) name, not the fully-qualified
        model::link::visual path.  So we must pass just the bare names.
        """
        if self.robot_name != 'ares':
            return

        vis_name = self._led_dome_visual_sdf
        vis_parent = self._led_lump_link

        if on:
            visual_req = f'''name: "{vis_name}"
parent_name: "{vis_parent}"
cast_shadows: false
material {{
  ambient {{ r: 0.1 g: 0.4 b: 1.0 a: 1.0 }}
  diffuse {{ r: 0.1 g: 0.4 b: 1.0 a: 1.0 }}
  emissive {{ r: 0.45 g: 0.85 b: 1.0 a: 1.0 }}
}}
'''
        else:
            visual_req = f'''name: "{vis_name}"
parent_name: "{vis_parent}"
cast_shadows: false
material {{
  ambient {{ r: 0.15 g: 0.15 b: 0.15 a: 1.0 }}
  diffuse {{ r: 0.15 g: 0.15 b: 0.15 a: 1.0 }}
  emissive {{ r: 0.0 g: 0.0 b: 0.0 a: 1.0 }}
}}
'''

        w = f'/world/{self._GZ_WORLD}'
        ok = self._ign_service(
            f'{w}/visual_config', 'ign_msgs.Visual', 'ign_msgs.Boolean', visual_req
        )
        if not ok:
            self.get_logger().warn(
                'Could not reach Gazebo visual_config. '
                'Is the sim running with IGN_PARTITION=slrc_sim and the ares model spawned?'
            )

    def _quaternion_to_yaw(self, q) -> float:
        """Extract yaw from quaternion."""
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)

    def publish_cmd_vel(self, velocity: float, omega: float):
        msg = Twist()
        msg.linear.x = float(velocity)
        msg.linear.y = 0.0  # Differential drive cannot strafe
        msg.angular.z = float(omega)
        self.cmd_vel_pub.publish(msg)
        self.last_command_time = time.time()

    def _publish_stop(self):
        msg = Twist()
        self.cmd_vel_pub.publish(msg)

    def watchdog_loop(self):
        rate = 0.1
        watchdog_triggered = False

        while rclpy.ok():
            if self.active_move_thread and self.active_move_thread.is_alive():
                watchdog_triggered = False
            else:
                elapsed = time.time() - self.last_command_time
                if elapsed > self.watchdog_timeout:
                    if not watchdog_triggered:
                        self.get_logger().warn("Watchdog timeout - stopping robot")
                        self._publish_stop()
                        watchdog_triggered = True
                else:
                    watchdog_triggered = False
            time.sleep(rate)

    def execute_move_relative(self, cmd):
        max_v = AresConfig.MAX_LINEAR_VEL
        max_w = AresConfig.MAX_ANGULAR_VEL
        acc_v = AresConfig.MAX_LINEAR_ACCEL
        acc_w = AresConfig.MAX_ANGULAR_ACCEL

        profile_lin = TrapezoidalProfile(
            max_vel=max_v, 
            max_accel=acc_v, 
            dt=0.05
        )
        profile_ang = TrapezoidalProfile(
            max_vel=max_w, 
            max_accel=acc_w, 
            dt=0.05
        )
        rate = self.create_rate(20)

        # Linear
        if abs(cmd.distance) > 0.001:
            vels = profile_lin.calculate_distance_profile(cmd.distance)
            for v in vels:
                if self.stop_requested:
                    break
                self.publish_cmd_vel(v, 0.0)
                rate.sleep()
            self.publish_cmd_vel(0.0, 0.0)

        # Angular
        if abs(cmd.rotation) > 0.001:
            vels = profile_ang.calculate_distance_profile(cmd.rotation)
            for w in vels:
                if self.stop_requested:
                    break
                self.publish_cmd_vel(0.0, w)
                rate.sleep()
            self.publish_cmd_vel(0.0, 0.0)
        self.publish_cmd_vel(0.0, 0.0)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main(args=None):
    rclpy.init(args=args)
    node = ApiServiceNode()

    executor = MultiThreadedExecutor()
    executor.add_node(node)

    ros_thread = threading.Thread(target=executor.spin, daemon=True)
    ros_thread.start()

    uvicorn.run(node.app, host="0.0.0.0", port=node.api_port, log_level="info")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
