#!/usr/bin/env python3
"""
SLRC 2026 API Service Node

Provides REST and streaming API for contestant access to the simulation.
Handles velocity commands, odometry, camera streams, and arena metadata.

Differential drive robot uses:
- velocity: forward/backward speed (m/s)
- omega: rotational speed (rad/s)

Author: kirangunathilaka
Contact: slrc@uom.lk
"""

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, Imu
from std_msgs.msg import String
from visualization_msgs.msg import Marker

import threading
import uvicorn
import yaml
from pathlib import Path
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2
import numpy as np
import time
import math
from typing import Optional, List

from slrc_sim_bridge.utils.trajectory import TrapezoidalProfile
from slrc_sim_bridge.config import AresConfig, ArenaConfig, HostileConfig


# -----------------------------------------------------------------------------
# FastAPI Models
# -----------------------------------------------------------------------------

class VelocityCommand(BaseModel):
    """Differential drive velocity command."""
    velocity: float  # Forward/backward speed in m/s (positive = forward)
    omega: float = 0.0  # Rotational speed in rad/s (positive = counter-clockwise)


class MoveRelativeCommand(BaseModel):
    """Relative move command with trapezoidal profile."""
    distance: float  # Distance to move in meters (positive = forward)
    rotation: float = 0.0  # Rotation in radians (positive = counter-clockwise)


class LedCommand(BaseModel):
    state: str  # "on", "off", "blink"
    color: str  # "red", "blue", "green"


class PathMarkerCommand(BaseModel):
    points: list  # [[x,y], [x,y]]
    type: str = "polyline"


# -----------------------------------------------------------------------------
# ROS Node
# -----------------------------------------------------------------------------
class ApiServiceNode(Node):
    def __init__(self):
        super().__init__('api_service')

        # Parameters
        self.declare_parameter('port', 8000)
        self.declare_parameter('start_x', 2.0)
        self.declare_parameter('start_y', 2.0)
        self.declare_parameter('watchdog_timeout', 1.0)
        self.declare_parameter('arena_config_file', '')
        self.declare_parameter('robot_name', 'ares')

        self.api_port = self.get_parameter('port').value
        self.start_x = self.get_parameter('start_x').value
        self.start_y = self.get_parameter('start_y').value
        self.watchdog_timeout = self.get_parameter('watchdog_timeout').value
        self.robot_name = self.get_parameter('robot_name').value
        arena_config_path = self.get_parameter('arena_config_file').value

        # Load arena configuration
        self.arena_config = self._load_arena_config(arena_config_path)

        self.get_logger().info(f"Starting API Service on port {self.api_port}")

        # Publishers (using /{self.robot_name}/ namespace)
        self.cmd_vel_pub = self.create_publisher(Twist, f'/{self.robot_name}/cmd_vel', 10)
        self.marker_pub = self.create_publisher(Marker, 'visualization_marker', 10)
        self.led_pub = self.create_publisher(String, 'led_cmd', 10)

        # Subscribers
        self.create_subscription(Odometry, f'/{self.robot_name}/odom', self.odom_callback, 10)
        self.create_subscription(Image, f'/{self.robot_name}/front_left/image_raw', self.cam_fl_callback, 10)
        self.create_subscription(Image, f'/{self.robot_name}/front_right/image_raw', self.cam_fr_callback, 10)
        self.create_subscription(Image, f'/{self.robot_name}/floor/image_raw', self.cam_floor_callback, 10)
        self.create_subscription(Imu, f'/{self.robot_name}/imu/data', self.imu_callback, 10)

        # Subscribe to hostile position
        self.hostile_position = None
        self.create_subscription(PoseStamped, '/hostile/position', self.hostile_position_callback, 10)

        # State
        self.current_odom = None
        self.current_imu = None
        self.latest_frames = {
            'front_left': None,
            'front_right': None,
            'floor': None
        }

        # Movement Control
        self.active_move_thread = None
        self.stop_requested = False
        self.last_command_time = time.time()

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
                'portal_cell': [20, 3]
            }
        }

    def setup_routes(self):
        # ... (Routes are largely unchanged, but I'll make sure they use the config limits implicitly) ...
        # =====================================================================
        # System Routes
        # =====================================================================
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

        # =====================================================================
        # Motion Control Routes
        # =====================================================================
        @self.app.post("/set_velocity")
        async def set_velocity(cmd: VelocityCommand):
            """Set robot velocity (differential drive) with limits."""
            self.stop_requested = True
            if self.active_move_thread and self.active_move_thread.is_alive():
                self.active_move_thread.join(timeout=0.1)

            # Clamp velocities
            if self.robot_name == 'hostile':
                max_v = HostileConfig.PATROL_SPEED
                max_w = HostileConfig.ROTATION_SPEED
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

        # =====================================================================
        # Sensor Routes
        # =====================================================================
        @self.app.get("/odometry")
        async def get_odometry():
            """Get current robot odometry (pose and velocity)."""
            if self.current_odom is None:
                raise HTTPException(status_code=503, detail="No odometry data available")

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
                raise HTTPException(status_code=503, detail="No IMU data available")

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

        # =====================================================================
        # Camera Routes
        # =====================================================================
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

        # =====================================================================
        # Arena Routes
        # =====================================================================
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
                "portal_cell": locations.get('portal_cell', [20, 3]),
                "start_world": {"x": self.start_x, "y": self.start_y}
            }

        @self.app.get("/arena/hostile_loop")
        async def get_hostile_loop():
            """Get the yellow hostile loop path as grid cells and world coordinates."""
            loop = self.arena_config.get('hostile_loop', [])
            
            # Convert to world coordinates
            world_coords = []
            for cell in loop:
                if isinstance(cell, list) and len(cell) == 2:
                    x, y = self._cell_to_world(cell[0], cell[1])
                    world_coords.append({"x": x, "y": y})
            
            return {
                "cells": loop,
                "world_coordinates": world_coords,
                "node_count": len(loop)
            }

        @self.app.get("/hostile/position")
        async def get_hostile_position():
            """Get current hostile robot position."""
            if self.hostile_position is None:
                raise HTTPException(status_code=503, detail="Hostile position not available")
            
            p = self.hostile_position.pose.position
            o = self.hostile_position.pose.orientation
            yaw = self._quaternion_to_yaw(o)
            
            return {
                "x": p.x,
                "y": p.y,
                "yaw": yaw,
                "timestamp": self.hostile_position.header.stamp.sec
            }

        @self.app.get("/start_coordinate")
        async def get_start_coordinate():
            """Get the ego robot start position in world coordinates."""
            return {"x": self.start_x, "y": self.start_y}

        # =====================================================================
        # Utility Routes
        # =====================================================================
        @self.app.post("/utility/set_led")
        async def set_led(cmd: LedCommand):
            """Set robot LED state and color."""
            msg = String()
            msg.data = f"{cmd.state}:{cmd.color}"
            self.led_pub.publish(msg)
            return {"status": "led_command_sent", "cmd": msg.data}

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

            self.marker_pub.publish(marker)
            return {"status": "marker_published"}

    # -------------------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------------------
    def odom_callback(self, msg: Odometry):
        """Update current odometry state."""
        self.current_odom = msg

    def cam_fl_callback(self, msg: Image):
        """Update front-left camera frame."""
        self.latest_frames['front_left'] = self._process_image(msg)

    def cam_fr_callback(self, msg: Image):
        """Update front-right camera frame."""
        self.latest_frames['front_right'] = self._process_image(msg)

    def cam_floor_callback(self, msg: Image):
        """Update floor camera frame."""
        self.latest_frames['floor'] = self._process_image(msg)

    def imu_callback(self, msg: Imu):
        """Update IMU data."""
        self.current_imu = msg

    def hostile_position_callback(self, msg: PoseStamped):
        """Update known position of the hostile robot."""
        self.hostile_position = msg

    def _process_image(self, msg: Image) -> bytes:
        """Convert ROS Image message to JPEG bytes."""
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
        """Generator for MJPEG stream."""
        while True:
            frame = self.latest_frames.get(cam_id)
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    def _quaternion_to_yaw(self, q) -> float:
        """Extract yaw from quaternion."""
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)

    def _cell_to_world(self, i: int, j: int) -> tuple:
        """Convert grid cell indices to world coordinates using ArenaConfig."""
        return ArenaConfig.cell_to_world(i, j)

    def publish_cmd_vel(self, velocity: float, omega: float):
        """Publish velocity command and update command timestamp."""
        msg = Twist()
        msg.linear.x = float(velocity)
        msg.linear.y = 0.0  # Differential drive cannot strafe
        msg.angular.z = float(omega)
        self.cmd_vel_pub.publish(msg)
        self.last_command_time = time.time()

    def _publish_stop(self):
        """Publish stop command WITHOUT updating last_command_time."""
        msg = Twist()
        self.cmd_vel_pub.publish(msg)

    def watchdog_loop(self):
        """Safety watchdog - stops robot if no commands received within timeout."""
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
        """Execute a relative move using trapezoidal velocity profiles with configured limits."""
        if self.robot_name == 'hostile':
            max_v = HostileConfig.PATROL_SPEED
            max_w = HostileConfig.ROTATION_SPEED
            acc_v = HostileConfig.LINEAR_ACCEL
            acc_w = HostileConfig.ANGULAR_ACCEL
        else:
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

        # Linear Move (distance)
        if abs(cmd.distance) > 0.001:
            vels = profile_lin.calculate_distance_profile(cmd.distance)
            for v in vels:
                if self.stop_requested:
                    break
                self.publish_cmd_vel(v, 0.0)
                time.sleep(0.05)
            self.publish_cmd_vel(0.0, 0.0)

        # Angular Move (rotation)
        if abs(cmd.rotation) > 0.001:
            vels = profile_ang.calculate_distance_profile(cmd.rotation)
            for w in vels:
                if self.stop_requested:
                    break
                self.publish_cmd_vel(0.0, w)
                time.sleep(0.05)
            self.publish_cmd_vel(0.0, 0.0)
        
        # Ensure stop at end
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
