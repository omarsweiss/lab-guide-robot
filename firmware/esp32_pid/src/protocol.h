// Serial communication protocol definitions shared with the ROS2 esp32_bridge_node.
//
// Line-based ASCII at 115200 baud, one message per '\n'.
//
//   host -> board:  TGT <offset>            normalized visitor offset in [-1, 1], positive is right
//                   PID <kp> <ki> <kd>      retune the tracking loop at runtime
//                   PING                    liveness check
//
//   board -> host:  STS <angle> <output>    current actuator angle in degrees and raw PID output
//                   EST <0|1>               emergency stop state, emitted on every change
//                   LOG <text>              human readable message, forwarded to the ROS log
//                   PONG                    reply to PING

#pragma once

#define CMD_TARGET "TGT"
#define CMD_GAINS "PID"
#define CMD_PING "PING"

#define MSG_STATUS "STS"
#define MSG_ESTOP "EST"
#define MSG_LOG "LOG"
#define MSG_PONG "PONG"

#define SERIAL_BAUD 115200
#define MAX_LINE_LENGTH 64
