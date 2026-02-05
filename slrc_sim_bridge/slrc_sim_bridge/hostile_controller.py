#!/usr/bin/env python3
"""
Hostile Controller Node - AI-controlled sentinel robot for SLRC 2026

Author: kirangunathilaka
Contact: slrc@uom.lk
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry

import yaml
import math
import random
import threading
import time
from pathlib import Path
from ament_index_python.packages import get_package_share_directory

from slrc_sim_bridge.utils.trajectory import TrapezoidalProfile
from slrc_sim_bridge.config import HostileConfig, ArenaConfig


def normalize_angle(angle: float) -> float:
    """Normalize angle to [-pi, pi]."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def quaternion_to_yaw(q) -> float:
    """Extract yaw from quaternion."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def cardinal_yaw_from_step(dx: int, dy: int) -> float:
    """
    Convert a single grid step direction (dx, dy) into a *cardinal* yaw.

    Assumptions:
    - Odom/world frame uses x-right, y-up in meters.
    - Your ArenaConfig.cell_to_world uses:
        x = -half + (i+0.5)*cell_size
        y =  half - (j+0.5)*cell_size
      That means increasing j moves y *down* in world coordinates.
      However the loop direction dx,dy are in grid indices (i,j), not world meters.

    For yaw, we only need consistency with actual motion:
    - dx changes world x directly (+dx => +x).
    - dy changes world y inversely (+dy => -y).
    So:
      dy = +1 (down in grid) => world y decreases => yaw = -pi/2
      dy = -1 (up in grid)   => world y increases => yaw = +pi/2
    """
    if dx == 1 and dy == 0:
        return 0.0
    if dx == -1 and dy == 0:
        return math.pi
    if dx == 0 and dy == 1:
        return -math.pi / 2.0
    if dx == 0 and dy == -1:
        return math.pi / 2.0
    raise ValueError(f"Invalid step direction dx,dy = {dx},{dy}")


class HostileController(Node):
    """
    Grid-robust hostile controller using trapezoidal velocity profiles.
    """

    STATE_INIT = "init"
    STATE_IDLE = "idle"
    STATE_EXECUTING_PROFILE = "executing"

    def __init__(self):
        super().__init__("hostile_controller")

        # Configuration (YAML just for hostile_loop)
        self.config = self._load_yaml_config()
        self.loop_cells = self.config.get("hostile_loop", [])

        if not self.loop_cells:
            self.get_logger().error("hostile_loop is empty. Hostile will not move.")

        # State
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_yaw = 0.0
        self.odom_received = False

        self.state = self.STATE_INIT
        self.is_running = True
        self.stop_requested = False

        # Path management
        self.current_cell_idx = HostileConfig.START_INDEX
        self.direction = 1  # 1 forward, -1 backward

        # Publishers/Subscribers
        self.cmd_vel_pub = self.create_publisher(Twist, "hostile/cmd_vel", 20)
        self.position_pub = self.create_publisher(PoseStamped, "hostile/position", 10)

        self.odom_sub = self.create_subscription(
            Odometry, "hostile/odom", self.odom_callback, 20
        )

        # Control thread
        self.control_thread = threading.Thread(target=self.control_loop, daemon=True)
        self.control_thread.start()

        self.get_logger().info("Hostile Controller (Grid-Snapped Trapezoidal) Initialized")

    def _load_yaml_config(self):
        """Load arena config just for the loop path."""
        try:
            pkg_share = get_package_share_directory("slrc_sim_bridge")
            config_path = Path(pkg_share) / "config" / "arena_config.yaml"
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {"hostile_loop": []}
        except Exception as e:
            self.get_logger().error(f"Failed to load yaml config: {e}")
            return {"hostile_loop": []}

    def odom_callback(self, msg: Odometry):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        self.current_yaw = quaternion_to_yaw(msg.pose.pose.orientation)
        self.odom_received = True

        # Publish position for debugging/visualization
        pose_msg = PoseStamped()
        pose_msg.header.stamp = self.get_clock().now().to_msg()
        pose_msg.header.frame_id = "odom"
        pose_msg.pose = msg.pose.pose
        self.position_pub.publish(pose_msg)

    def publish_cmd(self, v: float, w: float):
        msg = Twist()
        msg.linear.x = float(v)
        msg.angular.z = float(w)
        self.cmd_vel_pub.publish(msg)

    def execute_trapezoidal_move(self, distance: float = 0.0, rotation: float = 0.0):
        """
        Execute a blocking trapezoidal move with drift-free timing.
        NOTE: This is still open-loop in the sense of "play this profile",
        but we add end-of-segment pose snapping elsewhere to avoid accumulation.
        """
        self.state = self.STATE_EXECUTING_PROFILE
        dt = 0.01  # 100 Hz

        lin_prof = TrapezoidalProfile(
            max_vel=HostileConfig.PATROL_SPEED,
            max_accel=HostileConfig.LINEAR_ACCEL,
            dt=dt,
        )
        ang_prof = TrapezoidalProfile(
            max_vel=HostileConfig.ROTATION_SPEED,
            max_accel=HostileConfig.ANGULAR_ACCEL,
            dt=dt,
        )

        velocities_v = []
        velocities_w = []

        if abs(rotation) > 0.0005:
            velocities_w = ang_prof.calculate_distance_profile(rotation)

        if abs(distance) > 0.001:
            velocities_v = lin_prof.calculate_distance_profile(distance)

        def play_profile(v_list, is_angular=False):
            t_start = time.time()
            for i, val in enumerate(v_list):
                if self.stop_requested or not self.is_running:
                    return

                if is_angular:
                    self.publish_cmd(0.0, val)
                else:
                    self.publish_cmd(val, 0.0)

                target_time = t_start + ((i + 1) * dt)
                sleep_duration = target_time - time.time()
                if sleep_duration > 0:
                    time.sleep(sleep_duration)

            self.publish_cmd(0.0, 0.0)
            time.sleep(0.05)

        # Rotate then translate (grid style)
        if velocities_w:
            play_profile(velocities_w, is_angular=True)

        if velocities_v:
            play_profile(velocities_v, is_angular=False)

        self.state = self.STATE_IDLE

    def correct_heading(self, target_yaw: float):
        """
        Fine-tune rotation to match target yaw.
        FIXED: lower minimum angular rate to prevent overshoot near target.
        """
        timeout = 2.0
        start_time = time.time()

        kp = 2.0
        min_w = 0.05   # was 0.2; too aggressive near target
        max_w = 1.0

        while (time.time() - start_time) < timeout and self.is_running:
            yaw_diff = normalize_angle(target_yaw - self.current_yaw)

            # tolerance ~0.3 deg
            if abs(yaw_diff) < 0.005:
                break

            cmd_w = yaw_diff * kp

            # clamp with small minimum only when not tiny
            if cmd_w > 0:
                cmd_w = min(max_w, max(min_w, cmd_w))
            else:
                cmd_w = max(-max_w, min(-min_w, cmd_w))

            self.publish_cmd(0.0, cmd_w)
            time.sleep(0.02)

        self.publish_cmd(0.0, 0.0)
        time.sleep(0.05)

    def get_next_segment(self):
        """
        Look ahead in the loop to find the longest straight segment.
        Returns:
          (num_cells, world_target_x, world_target_y, end_idx, step_dx, step_dy)
        where step_dx,step_dy are the grid direction of the segment.
        """
        if not self.loop_cells:
            return 0, 0.0, 0.0, self.current_cell_idx, 0, 0

        n = len(self.loop_cells)
        idx = self.current_cell_idx
        start_cell = self.loop_cells[idx]

        # Determine initial direction from immediate next
        next_idx = idx + self.direction
        if next_idx >= n:
            next_idx = 0
        if next_idx < 0:
            next_idx = n - 1

        next_cell = self.loop_cells[next_idx]
        dx = next_cell[0] - start_cell[0]
        dy = next_cell[1] - start_cell[1]

        # Walk while direction matches
        cells_count = 0
        curr_idx = idx

        while True:
            nxt = curr_idx + self.direction
            if nxt >= n:
                nxt = 0
            if nxt < 0:
                nxt = n - 1

            c1 = self.loop_cells[curr_idx]
            c2 = self.loop_cells[nxt]
            cdx = c2[0] - c1[0]
            cdy = c2[1] - c1[1]

            if cdx == dx and cdy == dy:
                cells_count += 1
                curr_idx = nxt
            else:
                break

        target_cell = self.loop_cells[curr_idx]
        wx, wy = ArenaConfig.cell_to_world(target_cell[0], target_cell[1])
        return cells_count, wx, wy, curr_idx, dx, dy

    def snap_to_cell_center(self, target_ox: float, target_oy: float, desired_yaw: float):
        """
        End-of-segment correction to avoid drift accumulation.

        Strategy:
        - compute small position error to the expected cell center
        - if error is small, do a short correction move:
            rotate toward error, move a short capped distance, rotate back to desired_yaw
        """
        ex = target_ox - self.current_x
        ey = target_oy - self.current_y
        err = math.hypot(ex, ey)

        if err < 0.01:
            return  # already good

        # Cap correction so we never do big weird diagonal moves
        max_corr = 0.08  # 8 cm
        corr_dist = min(err, max_corr)

        corr_yaw = math.atan2(ey, ex)
        yaw_to_corr = normalize_angle(corr_yaw - self.current_yaw)

        # Only correct if meaningful
        if abs(yaw_to_corr) > 0.01:
            self.execute_trapezoidal_move(rotation=yaw_to_corr)
            self.correct_heading(corr_yaw)

        if corr_dist > 0.005:
            self.execute_trapezoidal_move(distance=corr_dist)

        # Return to cardinal heading
        yaw_back = normalize_angle(desired_yaw - self.current_yaw)
        if abs(yaw_back) > 0.01:
            self.execute_trapezoidal_move(rotation=yaw_back)
            self.correct_heading(desired_yaw)

    def maybe_random_direction_switch(self):
        """
        Randomly flip direction. We do NOT blindly rotate 180 anymore.
        We flip direction first, then rotate to the next segment's *cardinal* heading.
        """
        if not self.loop_cells:
            return

        if random.random() >= HostileConfig.DIRECTION_SWITCH_PROB:
            return

        self.get_logger().info(">>> RANDOM DIRECTION SWITCH <<<")
        self.direction *= -1

        # After flipping, rotate to the new upcoming segment cardinal yaw
        num_cells, wx, wy, next_idx, step_dx, step_dy = self.get_next_segment()
        if num_cells <= 0:
            return

        desired_yaw = cardinal_yaw_from_step(step_dx, step_dy)
        yaw_diff = normalize_angle(desired_yaw - self.current_yaw)

        if abs(yaw_diff) > 0.002:
            self.execute_trapezoidal_move(rotation=yaw_diff)
            self.correct_heading(desired_yaw)

        time.sleep(0.2)

    def control_loop(self):
        """Main loop."""
        # Wait for odom
        while not self.odom_received and self.is_running:
            time.sleep(0.05)

        time.sleep(0.5)

        if not self.loop_cells:
            self.get_logger().error("No loop cells. Exiting control loop.")
            return

        # Spawn cell world => used to convert world cell centers to odom-relative
        spawn_cell = self.loop_cells[HostileConfig.START_INDEX]
        spawn_wx, spawn_wy = ArenaConfig.cell_to_world(spawn_cell[0], spawn_cell[1])

        self.get_logger().info(f"Hostile Patrol Started. Spawn Index: {HostileConfig.START_INDEX}")

        # Optional: initial align to first segment
        num_cells, wx, wy, next_idx, step_dx, step_dy = self.get_next_segment()
        if num_cells > 0:
            desired_yaw = cardinal_yaw_from_step(step_dx, step_dy)
            yaw_diff = normalize_angle(desired_yaw - self.current_yaw)
            if abs(yaw_diff) > 0.01:
                self.execute_trapezoidal_move(rotation=yaw_diff)
                self.correct_heading(desired_yaw)

        while self.is_running and rclpy.ok():
            # 1) random switch (flip + align properly)
            self.maybe_random_direction_switch()

            # 2) plan next segment
            num_cells, global_tx, global_ty, next_idx, step_dx, step_dy = self.get_next_segment()
            if num_cells <= 0:
                time.sleep(0.1)
                continue

            desired_yaw = cardinal_yaw_from_step(step_dx, step_dy)

            # 3) rotate to exact cardinal direction (never aim diagonally)
            yaw_diff = normalize_angle(desired_yaw - self.current_yaw)
            self.get_logger().info(
                f"Segment: {num_cells} cells | Turn: {math.degrees(yaw_diff):.1f} deg | Dir: ({step_dx},{step_dy})"
            )

            if abs(yaw_diff) > 0.002:
                self.execute_trapezoidal_move(rotation=yaw_diff)
                self.correct_heading(desired_yaw)

            # 4) move exact grid distance
            dist_to_go = float(num_cells) * float(ArenaConfig.CELL_SIZE)
            if dist_to_go > 0.001:
                self.execute_trapezoidal_move(distance=dist_to_go)

            # 5) update index to end of segment
            self.current_cell_idx = next_idx

            # 6) snap to expected cell center (odom-relative)
            target_cell = self.loop_cells[self.current_cell_idx]
            wx, wy = ArenaConfig.cell_to_world(target_cell[0], target_cell[1])
            target_ox = wx - spawn_wx
            target_oy = wy - spawn_wy

            self.snap_to_cell_center(target_ox, target_oy, desired_yaw)

            time.sleep(0.05)

    def destroy_node(self):
        self.is_running = False
        self.publish_cmd(0.0, 0.0)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = HostileController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
