// PID controller interface for the tracking loop.

#pragma once

class PID {
 public:
  PID(float kp, float ki, float kd, float outputLimit, float integralLimit);

  void setGains(float kp, float ki, float kd);
  void reset();
  float update(float error, float dt);

 private:
  float kp_;
  float ki_;
  float kd_;
  float outputLimit_;
  float integralLimit_;

  float integral_;
  float prevError_;
  bool hasPrevError_;
};
