// PID controller implementation for the tracking loop.

#include "pid.h"

namespace {

float clamp(float value, float limit) {
  if (value > limit) return limit;
  if (value < -limit) return -limit;
  return value;
}

}  // namespace

PID::PID(float kp, float ki, float kd, float outputLimit, float integralLimit)
    : kp_(kp),
      ki_(ki),
      kd_(kd),
      outputLimit_(outputLimit),
      integralLimit_(integralLimit),
      integral_(0.0f),
      prevError_(0.0f),
      hasPrevError_(false) {}

void PID::setGains(float kp, float ki, float kd) {
  kp_ = kp;
  ki_ = ki;
  kd_ = kd;
}

void PID::reset() {
  integral_ = 0.0f;
  prevError_ = 0.0f;
  hasPrevError_ = false;
}

float PID::update(float error, float dt) {
  if (dt <= 0.0f) {
    return 0.0f;
  }

  integral_ = clamp(integral_ + error * dt, integralLimit_);

  float derivative = hasPrevError_ ? (error - prevError_) / dt : 0.0f;
  prevError_ = error;
  hasPrevError_ = true;

  float output = kp_ * error + ki_ * integral_ + kd_ * derivative;
  float limited = clamp(output, outputLimit_);

  // Unwind the integrator when the output saturates, so it cannot keep growing while the actuator is pinned.
  if (limited != output && ki_ != 0.0f) {
    integral_ -= (output - limited) / ki_;
    integral_ = clamp(integral_, integralLimit_);
  }

  return limited;
}
