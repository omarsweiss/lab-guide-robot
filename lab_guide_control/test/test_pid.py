# Unit tests for pid.py.

import pytest

from lab_guide_control.pid import PID


def test_proportional_only_scales_the_error():
    pid = PID(kp=2.0)
    assert pid.update(0.5, dt=0.1) == pytest.approx(1.0)


def test_zero_error_produces_zero_output():
    pid = PID(kp=2.0, ki=1.0, kd=1.0)
    assert pid.update(0.0, dt=0.1) == pytest.approx(0.0)


def test_integral_accumulates_over_time():
    pid = PID(kp=0.0, ki=1.0)
    assert pid.update(1.0, dt=0.5) == pytest.approx(0.5)
    assert pid.update(1.0, dt=0.5) == pytest.approx(1.0)


def test_derivative_responds_to_change_in_error():
    pid = PID(kp=0.0, kd=2.0)
    # The first sample has no previous error, so the derivative term stays out of it.
    assert pid.update(1.0, dt=0.1) == pytest.approx(0.0)
    assert pid.update(2.0, dt=0.1) == pytest.approx(20.0)


def test_output_is_clamped_to_the_limit():
    pid = PID(kp=10.0, output_limit=1.5)
    assert pid.update(1.0, dt=0.1) == pytest.approx(1.5)
    assert pid.update(-1.0, dt=0.1) == pytest.approx(-1.5)


def test_integral_does_not_wind_up_while_output_is_saturated():
    pid = PID(kp=0.0, ki=1.0, output_limit=1.0)
    for _ in range(50):
        pid.update(1.0, dt=0.1)

    # Once the error flips, a wound-up integrator would keep pushing the wrong way for many cycles.
    assert pid.update(-1.0, dt=0.1) < 1.0


def test_integral_limit_caps_accumulation():
    pid = PID(kp=0.0, ki=1.0, integral_limit=0.2)
    for _ in range(10):
        output = pid.update(1.0, dt=0.1)
    assert output == pytest.approx(0.2)


def test_reset_clears_accumulated_state():
    pid = PID(kp=0.0, ki=1.0, kd=1.0)
    pid.update(1.0, dt=0.1)
    pid.update(1.0, dt=0.1)
    pid.reset()
    assert pid.update(1.0, dt=0.1) == pytest.approx(0.1)


def test_non_positive_dt_is_rejected():
    pid = PID(kp=1.0)
    with pytest.raises(ValueError):
        pid.update(1.0, dt=0.0)
