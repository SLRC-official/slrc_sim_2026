"""
SLRC 2026 Simulation Configuration

Central configuration for robot parameters, limits, and behavior.
"""
import math


class ArenaConfig:
    # Grid parameters (must match world file)
    GRID_SIZE = 25
    CELL_SIZE = 0.40  # meters
    GRID_SPAN = 10.0  # meters

    @staticmethod
    def cell_to_world(i, j):
        """Convert grid cell indices to world coordinates."""
        half = ArenaConfig.GRID_SPAN / 2.0
        x = -half + (i + 0.5) * ArenaConfig.CELL_SIZE
        y = half - (j + 0.5) * ArenaConfig.CELL_SIZE
        return x, y


class AresConfig:
    # Physical limits
    MAX_LINEAR_VEL = 1.6  # m/s
    MAX_ANGULAR_VEL = 4.0  # rad/s
    MAX_LINEAR_ACCEL = 2.0  # m/s^2
    MAX_ANGULAR_ACCEL = 4.0  # rad/s^2

    # Dimensions
    WHEEL_RADIUS = 0.03
    WHEEL_SEPARATION = 0.16


class HostileConfig:
    # Line-following parameters
    CRUISE_SPEED = 0.6  # m/s (forward speed while line following)
    STEER_KP = 0.005  # Proportional gain for steering (error in pixels -> rad/s)
    STEER_KD = 0.002  # Derivative gain for steering damping
    MAX_LINEAR_VEL = 1.0  # m/s
    MAX_ANGULAR_VEL = 3.0  # rad/s

    # 180° reversal behavior
    TURN_SPEED = 2.0  # rad/s for 180° turns
    REVERSAL_PROB = 0.002  # Probability of 180° reversal per control cycle (~30Hz)

    # Camera / HSV thresholds for yellow line detection
    YELLOW_H_LOW = 20
    YELLOW_H_HIGH = 40
    YELLOW_S_LOW = 80
    YELLOW_S_HIGH = 255
    YELLOW_V_LOW = 150
    YELLOW_V_HIGH = 255
