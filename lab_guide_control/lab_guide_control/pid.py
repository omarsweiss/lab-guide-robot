# PID controller used for visitor-tracking control, mirrored by the ESP32 firmware implementation.

from dataclasses import dataclass, field


@dataclass
class PID:
    kp: float
    ki: float = 0.0
    kd: float = 0.0
    output_limit: float = float('inf')
    integral_limit: float = float('inf')

    _integral: float = field(default=0.0, init=False)
    _prev_error: float | None = field(default=None, init=False)

    def reset(self) -> None:
        self._integral = 0.0
        self._prev_error = None

    def update(self, error: float, dt: float) -> float:
        if dt <= 0.0:
            raise ValueError('dt must be positive')

        self._integral = _clamp(self._integral + error * dt, self.integral_limit)
        derivative = 0.0 if self._prev_error is None else (error - self._prev_error) / dt
        self._prev_error = error

        output = self.kp * error + self.ki * self._integral + self.kd * derivative
        limited = _clamp(output, self.output_limit)

        # Unwind the integrator when the output saturates, so it cannot keep growing while the actuator is pinned.
        if limited != output and self.ki != 0.0:
            self._integral -= (output - limited) / self.ki
            self._integral = _clamp(self._integral, self.integral_limit)

        return limited


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))
