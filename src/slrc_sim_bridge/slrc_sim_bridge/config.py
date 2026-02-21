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
