
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, Imu
from std_msgs.msg import String
from visualization_msgs.msg import Marker

import threading
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import cv2
import numpy as np
import io
import time
import math
from typing import Optional

# Import local utils
from slrc_sim_bridge.utils.trajectory import TrapezoidalProfile

# -----------------------------------------------------------------------------
# FastAPI Models
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# FastAPI Models
# -----------------------------------------------------------------------------
class VelocityCommand(BaseModel):
    vx: float
    vy: float
    omega: float

class MoveRelativeCommand(BaseModel):
    dx: float
    dy: float
    dtheta: float
    
class LedCommand(BaseModel):
    state: str # "on", "off", "blink"
    color: str # "red", "blue", "green"

class PathMarkerCommand(BaseModel):
    points: list # [[x,y], [x,y]]
    type: str = "polyline" # polyline, points

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
        self.declare_parameter('watchdog_timeout', 1.0) # seconds
        
        self.api_port = self.get_parameter('port').value
        self.start_x = self.get_parameter('start_x').value
        self.start_y = self.get_parameter('start_y').value
        self.watchdog_timeout = self.get_parameter('watchdog_timeout').value
        
        self.get_logger().info(f"Starting API Service on port {self.api_port}")

        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.marker_pub = self.create_publisher(Marker, 'visualization_marker', 10)
        self.led_pub = self.create_publisher(String, 'led_cmd', 10)
        
        # Subscribers
        self.create_subscription(Odometry, 'odom', self.odom_callback, 10)
        self.create_subscription(Image, 'front_left/image_raw', self.cam_fl_callback, 10)
        self.create_subscription(Image, 'front_right/image_raw', self.cam_fr_callback, 10)
        self.create_subscription(Image, 'floor/image_raw', self.cam_floor_callback, 10)
        
        # State
        self.current_odom = None
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
        self.app = FastAPI()
        self.setup_routes()

    def setup_routes(self):
        @self.app.get("/")
        async def root():
            return {"status": "running", "team": self.get_namespace().strip('/')}

        @self.app.post("/set_velocity")
        async def set_velocity(cmd: VelocityCommand):
            # Pre-empt any active relative move
            self.stop_requested = True
            if self.active_move_thread and self.active_move_thread.is_alive():
                self.active_move_thread.join(timeout=0.1)
            
            self.publish_cmd_vel(cmd.vx, cmd.vy, cmd.omega)
            return {"status": "executed"}

        @self.app.post("/move_relative")
        async def move_relative(cmd: MoveRelativeCommand):
            if self.active_move_thread and self.active_move_thread.is_alive():
                return JSONResponse(status_code=409, content={"error": "Move already in progress"})
            
            self.stop_requested = False
            self.last_command_time = time.time() + 999999 # Disable watchdog for autonomous move? Or keep it?
            # Better: The move thread updates activity.
            
            self.active_move_thread = threading.Thread(target=self.execute_move_relative, args=(cmd,))
            self.active_move_thread.start()
            return {"status": "started", "description": "Trapezoidal move initiated"}

        @self.app.get("/odometry")
        async def get_odometry():
            if self.current_odom is None:
                return {"error": "No updates yet"}
            
            # Convert quaternion to yaw if needed, or just return raw
            p = self.current_odom.pose.pose.position
            o = self.current_odom.pose.pose.orientation
            v = self.current_odom.twist.twist.linear
            w = self.current_odom.twist.twist.angular
            
            return {
                "pose": {"x": p.x, "y": p.y, "z": p.z, 
                         "orientation": {"x": o.x, "y": o.y, "z": o.z, "w": o.w}},
                "velocity": {"vx": v.x, "vy": v.y, "wz": w.z}
            }

        @self.app.get("/start_coordinate")
        async def get_start_coordinate():
            return {"x": self.start_x, "y": self.start_y}

        @self.app.get("/camera/{cam_id}/stream")
        async def camera_stream(cam_id: str):
            if cam_id not in self.latest_frames:
                raise HTTPException(status_code=404, detail="Camera not found")
            return StreamingResponse(self.generate_mjpeg(cam_id), media_type="multipart/x-mixed-replace; boundary=frame")

        @self.app.post("/utility/set_led")
        async def set_led(cmd: LedCommand):
            msg = String()
            msg.data = f"{cmd.state}:{cmd.color}"
            self.led_pub.publish(msg)
            return {"status": "led_command_sent", "cmd": msg.data}

        @self.app.post("/utility/mark_path")
        async def mark_path(cmd: PathMarkerCommand):
            marker = Marker()
            marker.header.frame_id = "odom"
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "path_marker"
            marker.id = 0
            marker.type = Marker.LINE_STRIP
            marker.action = Marker.ADD
            marker.scale.x = 0.05 # Line width
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

    # -------------------------------------------------------------------------
    # Logic
    # -------------------------------------------------------------------------
    def publish_cmd_vel(self, vx, vy, omega):
        msg = Twist()
        msg.linear.x = float(vx)
        msg.linear.y = float(vy)
        msg.angular.z = float(omega)
        self.cmd_vel_pub.publish(msg)
        self.last_command_time = time.time()

    def watchdog_loop(self):
        rate = 0.1 # Check every 100ms
        while rclpy.ok():
            if self.active_move_thread and self.active_move_thread.is_alive():
                 # Don't watchdog during autonomous move
                 pass
            else:
                if time.time() - self.last_command_time > self.watchdog_timeout:
                    # Timeout! Stop robot
                    self.publish_cmd_vel(0.0, 0.0, 0.0)
            time.sleep(rate)

    def execute_move_relative(self, cmd):
        """
        Naive implementation: Rotate then Move.
        Or Move X then Move Y?
        Requirement: "target displacement and rotation ... automatically execute a trapezoidal velocity profile"
        
        For simplicity in a diff-drive/holonomic context:
        If holonomic (omni), we can move in X and Y simultaneously.
        If diff-drive, we must Rotate -> Move -> Rotate.
        The 'lightcycle' is typically diff-drive.
        
        Let's assume Diff Drive behavior sequence:
        1. Rotate to face target (dtheta from current pose... oh wait, is this relative to ROBOT frame?)
        If `move_relative(dx, dy, dtheta)` is in ROBOT FRAME, then:
           - dx is forward
           - dy is lateral (0 for diff drive usually, unless holonomic)
           - dtheta is rotation
        
        URDF says 'DiffDrive' plugin. So dy must be 0 or ignored.
        
        Sequence:
        1. Rotate `dtheta`. (Or maybe `atan2(dy, dx)` first? No, relative means dx meters forward.)
        Wait, standard `move_relative` usually implies:
        Move `dx` forward, rotate `dtheta`.
        
        Let's support just linear (dx) and angular (dtheta). 
        If dy is provided and non-zero on diff drive, we can't do it easily without arc turn.
        Let's implement:
        1. Rotate `dtheta`? OR
        2. Move `dx`?
        
        Actually, let's just do sequential:
        1. Move `dx` (Trapezoidal Linear)
        2. Rotate `dtheta` (Trapezoidal Angular)
        
        This assumes dx is pure forward motion.
        """
        
        profile_lin = TrapezoidalProfile(max_vel=1.0, max_accel=1.0, dt=0.05) # 20Hz control
        profile_ang = TrapezoidalProfile(max_vel=2.0, max_accel=2.0, dt=0.05)
        
        # 1. Linear Move
        if abs(cmd.dx) > 0.001:
            vels = profile_lin.calculate_distance_profile(cmd.dx)
            for v in vels:
                if self.stop_requested: break
                self.publish_cmd_vel(v, 0.0, 0.0)
                time.sleep(0.05)
            self.publish_cmd_vel(0.0, 0.0, 0.0) # Stop

        # 2. Angular Move
        if abs(cmd.dtheta) > 0.001:
            vels = profile_ang.calculate_distance_profile(cmd.dtheta)
            for w in vels:
                if self.stop_requested: break
                self.publish_cmd_vel(0.0, 0.0, w)
                time.sleep(0.05)
            self.publish_cmd_vel(0.0, 0.0, 0.0)

    # -------------------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------------------
    def odom_callback(self, msg):
        self.current_odom = msg

    def _process_image(self, msg, key):
        # Convert ROS Image to OpenCV
        # Assuming R8G8B8 or similar
        try:
            # Manual conversion for simplicity without cv_bridge dependency if possible,
            # but cv_bridge is standard. Let's try raw buffer if format is simple.
            # GZ sends R8G8B8 usually.
            if msg.encoding == 'rgb8':
                img = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            elif msg.encoding == 'bgr8':
                img = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
            else:
                self.get_logger().warn(f"Unsupported encoding: {msg.encoding}")
                return

            # Encode to JPEG for streaming
            ret, buffer = cv2.imencode('.jpg', img)
            if ret:
                self.latest_frames[key] = buffer.tobytes()
        except Exception as e:
            self.get_logger().error(f"Image processing error: {e}")

    def cam_fl_callback(self, msg):
        self._process_image(msg, 'front_left')
    
    def cam_fr_callback(self, msg):
        self._process_image(msg, 'front_right')
        
    def cam_floor_callback(self, msg):
        self._process_image(msg, 'floor')

    def generate_mjpeg(self, cam_id):
        while True:
            frame = self.latest_frames.get(cam_id)
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05) # 20 FPS

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main(args=None):
    rclpy.init(args=args)
    node = ApiServiceNode()
    
    # Run ROS in a separate thread
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    ros_thread = threading.Thread(target=executor.spin, daemon=True)
    ros_thread.start()
    
    # Run FastAPI
    # Note: host='0.0.0.0' to allow Docker mapping
    uvicorn.run(node.app, host="0.0.0.0", port=node.api_port, log_level="info")
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
