
import math


class TrapezoidalProfile:
    def __init__(self, max_vel, max_accel, dt):
        self.max_vel = max_vel
        self.max_accel = max_accel
        self.dt = dt

    def _velocity_at_time(self, t, t_accel, t_coast, is_triangle):
        """
        Continuous trapezoidal (or triangle) profile: velocity at time t.
        Returns magnitude (non-negative). Caller applies direction.
        """
        if is_triangle:
            # Triangle: accel to peak then decel. Total time 2*t_accel.
            if t <= 0:
                return 0.0
            if t < t_accel:
                return self.max_accel * t
            if t < 2 * t_accel:
                return self.max_accel * (2 * t_accel - t)
            return 0.0
        else:
            # Trapezoid: accel, coast, decel.
            t_decel_start = t_accel + t_coast
            t_total = 2 * t_accel + t_coast
            if t <= 0:
                return 0.0
            if t < t_accel:
                return self.max_accel * t
            if t < t_decel_start:
                return self.max_vel
            if t < t_total:
                return self.max_vel - self.max_accel * (t - t_decel_start)
            return 0.0

    def calculate_distance_profile(self, distance):
        """
        Generates a sequence of velocity commands to move 'distance' meters
        (or radians for angular) with a trapezoidal velocity profile.

        Uses time-based sampling so that applying each velocity for dt seconds
        gives total distance equal to |distance| (within one step). This fixes
        the previous step-count approach which caused large errors.

        Returns a list of velocities (signed).
        """
        if distance == 0:
            return []

        direction = 1.0 if distance > 0 else -1.0
        dist_mag = abs(distance)

        # Time to accelerate to max_vel and distance covered in that time
        t_accel_full = self.max_vel / self.max_accel
        d_accel_full = 0.5 * self.max_accel * t_accel_full ** 2

        if 2 * d_accel_full >= dist_mag:
            # Triangle profile: we never reach max_vel
            # dist_mag = a * t_accel^2  =>  t_accel = sqrt(dist_mag / a)
            t_accel = math.sqrt(dist_mag / self.max_accel)
            t_coast = 0.0
            is_triangle = True
            t_total = 2 * t_accel
        else:
            # Trapezoid: accel, coast at max_vel, decel
            t_accel = t_accel_full
            d_coast = dist_mag - 2 * d_accel_full
            t_coast = d_coast / self.max_vel
            is_triangle = False
            t_total = 2 * t_accel + t_coast

        # Sample velocity at t = 0, dt, 2*dt, ... until we reach/pass t_total
        velocities = []
        t = 0.0
        while t < t_total:
            v_mag = self._velocity_at_time(t, t_accel, t_coast, is_triangle)
            velocities.append(v_mag * direction)
            t += self.dt

        # Final zero to ensure we stop
        velocities.append(0.0)
        return velocities
