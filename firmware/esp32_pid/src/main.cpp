// Firmware entry point: tracking PID loop and emergency-stop logic for the ESP32-S3.
//
// No actuator is wired up yet, so the tracking loop integrates its own output into a simulated
// angle and reports it over serial. Swap simulateActuator() for a real servo write when the
// hardware exists.

#include <Arduino.h>
#include <stdlib.h>
#include <string.h>

#include "pid.h"
#include "protocol.h"

namespace {

constexpr int ESTOP_PIN = 0;  // BOOT button on the DevKitC, active low.
constexpr unsigned long CONTROL_PERIOD_MS = 20;
constexpr unsigned long ESTOP_DEBOUNCE_MS = 50;
constexpr float ANGLE_LIMIT_DEG = 90.0f;

PID tracker(60.0f, 0.0f, 4.0f, 120.0f, 10.0f);

float targetOffset = 0.0f;
float actuatorAngle = 0.0f;
bool estopEngaged = false;

unsigned long lastControlMs = 0;
unsigned long lastEstopChangeMs = 0;
int lastEstopReading = HIGH;

char line[MAX_LINE_LENGTH];
size_t lineLength = 0;

void emitEstop() {
  Serial.print(MSG_ESTOP " ");
  Serial.println(estopEngaged ? 1 : 0);
}

void handleLine(const char* text) {
  if (strncmp(text, CMD_TARGET, strlen(CMD_TARGET)) == 0) {
    targetOffset = atof(text + strlen(CMD_TARGET));
  } else if (strncmp(text, CMD_GAINS, strlen(CMD_GAINS)) == 0) {
    float kp = 0.0f;
    float ki = 0.0f;
    float kd = 0.0f;
    if (sscanf(text + strlen(CMD_GAINS), "%f %f %f", &kp, &ki, &kd) == 3) {
      tracker.setGains(kp, ki, kd);
      tracker.reset();
      Serial.println(MSG_LOG " gains updated");
    }
  } else if (strncmp(text, CMD_PING, strlen(CMD_PING)) == 0) {
    Serial.println(MSG_PONG);
  }
}

void readSerial() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n' || c == '\r') {
      if (lineLength > 0) {
        line[lineLength] = '\0';
        handleLine(line);
        lineLength = 0;
      }
    } else if (lineLength < MAX_LINE_LENGTH - 1) {
      line[lineLength++] = c;
    } else {
      lineLength = 0;  // Overlong line, drop it rather than wrapping into the next one.
    }
  }
}

void updateEstop() {
  int reading = digitalRead(ESTOP_PIN);
  unsigned long now = millis();

  if (reading != lastEstopReading) {
    lastEstopReading = reading;
    lastEstopChangeMs = now;
    return;
  }

  if (now - lastEstopChangeMs < ESTOP_DEBOUNCE_MS) {
    return;
  }

  bool pressed = (reading == LOW);
  if (pressed != estopEngaged) {
    estopEngaged = pressed;
    if (estopEngaged) {
      tracker.reset();
    }
    emitEstop();
  }
}

// Stands in for a servo write until the tracking hardware is attached.
void simulateActuator(float output, float dt) {
  actuatorAngle += output * dt;
  if (actuatorAngle > ANGLE_LIMIT_DEG) actuatorAngle = ANGLE_LIMIT_DEG;
  if (actuatorAngle < -ANGLE_LIMIT_DEG) actuatorAngle = -ANGLE_LIMIT_DEG;
}

}  // namespace

void setup() {
  Serial.begin(SERIAL_BAUD);
  pinMode(ESTOP_PIN, INPUT_PULLUP);
  lastControlMs = millis();
  Serial.println(MSG_LOG " lab guide tracker ready");
  emitEstop();
}

void loop() {
  readSerial();
  updateEstop();

  unsigned long now = millis();
  if (now - lastControlMs < CONTROL_PERIOD_MS) {
    return;
  }

  float dt = (now - lastControlMs) / 1000.0f;
  lastControlMs = now;

  float output = 0.0f;
  if (estopEngaged) {
    tracker.reset();
  } else {
    // Positive offset means the visitor is right of centre, so the actuator must turn the same way.
    output = tracker.update(targetOffset, dt);
    simulateActuator(output, dt);
  }

  Serial.print(MSG_STATUS " ");
  Serial.print(actuatorAngle, 2);
  Serial.print(' ');
  Serial.println(output, 2);
}
