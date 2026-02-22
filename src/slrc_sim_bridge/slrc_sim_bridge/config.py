"""SLRC 2026 simulation config: arena, Ares, Hostile limits."""
import math


class ArenaConfig:
    GRID_SIZE = 25
    CELL_SIZE = 0.40
    GRID_SPAN = 10.0

    @staticmethod
    def cell_to_world(i, j):
        half = ArenaConfig.GRID_SPAN / 2.0
        x = -half + (i + 0.5) * ArenaConfig.CELL_SIZE
        y = half - (j + 0.5) * ArenaConfig.CELL_SIZE
        return x, y


class AresConfig:
    MAX_LINEAR_VEL = 1.6
    MAX_ANGULAR_VEL = 4.0
    MAX_LINEAR_ACCEL = 2.0
    MAX_ANGULAR_ACCEL = 4.0
    WHEEL_RADIUS = 0.03
    WHEEL_SEPARATION = 0.16


class HostileConfig:
    CRUISE_SPEED = 0.6
    STEER_KP = 0.005
    STEER_KD = 0.002
    MAX_LINEAR_VEL = 1.0
    MAX_ANGULAR_VEL = 3.0
    TURN_SPEED = 2.0
    REVERSAL_PROB = 0.002
    YELLOW_H_LOW = 20
    YELLOW_H_HIGH = 40
    YELLOW_S_LOW = 80
    YELLOW_S_HIGH = 255
    YELLOW_V_LOW = 150
    YELLOW_V_HIGH = 255
