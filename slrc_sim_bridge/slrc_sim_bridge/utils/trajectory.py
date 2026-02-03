
import math

class TrapezoidalProfile:
    def __init__(self, max_vel, max_accel, dt):
        self.max_vel = max_vel
        self.max_accel = max_accel
        self.dt = dt

    def calculate_distance_profile(self, distance):
        """
        Generates a sequence of velocity commands to move 'distance' meters
        with a trapezoidal velocity profile.
        Returns a list of velocities.
        """
        if distance == 0:
            return []

        direction = 1.0 if distance > 0 else -1.0
        dist_mag = abs(distance)
        
        # Calculate time to accelerate to max_vel
        t_accel = self.max_vel / self.max_accel
        d_accel = 0.5 * self.max_accel * t_accel**2

        if 2 * d_accel > dist_mag:
            # Triangle profile (we don't reach max_vel)
            # d_accel_actual = dist_mag / 2
            # 0.5 * a * t^2 = d/2 => t = sqrt(d/a)
            t_accel = math.sqrt(dist_mag / self.max_accel)
            t_coast = 0
            # peak_vel = self.max_accel * t_accel
        else:
            # M-Trapezoid profile
            d_coast = dist_mag - 2 * d_accel
            t_coast = d_coast / self.max_vel

        # Generate profile steps
        velocities = []
        
        # Acceleration phase
        steps_accel = int(t_accel / self.dt)
        for i in range(steps_accel):
            v = self.max_accel * (i * self.dt)
            velocities.append(v * direction)
            
        # Coast phase
        steps_coast = int(t_coast / self.dt)
        peak_vel = (self.max_accel * t_accel) * direction
        for i in range(steps_coast):
            velocities.append(peak_vel)
            
        # Deceleration phase
        # Note: Ideally exact mirror of acceleration
        # We start from current velocity and reduce
        current_v = abs(peak_vel)
        for i in range(steps_accel):
            current_v -= self.max_accel * self.dt
            if current_v < 0: current_v = 0
            velocities.append(current_v * direction)

        # Final stop
        velocities.append(0.0)
        
        return velocities
