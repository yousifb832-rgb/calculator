/*
  servo_calibration.ino  -  Stage 1 tool
  Low-Cost Robotic Assistance Glove project

  WHAT THIS IS FOR
  Moves ONE servo slowly to any angle you type in the Serial Monitor, so you
  can find the two safe limits of your finger (or glove):
     OPEN angle   = finger straight, tendon just tight (not slack, not pulling)
     CLOSED angle = the most flexion you want, before anything strains
  Write both numbers in your logbook. You will copy them into robotic_glove.ino.

  WIRING (same as the full project)
     Servo signal (orange/yellow) -> 330 ohm resistor -> D9  (D10 for the thumb)
     Servo red   (+)              -> +5 V of the EXTERNAL supply, never the Arduino 5V pin
     Servo brown (-)              -> GND of the external supply AND an Arduino GND pin

  HOW TO USE
     1. Unhook the tendon from the drum before the first upload.
     2. Upload. Open Tools > Serial Monitor, choose 115200 baud and "Newline".
     3. Type a number 0-180 and press Enter: the servo moves there slowly.
     4. Type  +  or  -  to nudge by 2 degrees.
     5. Type  s20  to set the speed to 20 degrees per second (5 to 60).
     6. Type  ?  to print the current angle.
*/

#include <Servo.h>

const uint8_t SERVO_PIN   = 9;    // change to 10 to calibrate the thumb servo
const int     START_ANGLE = 90;   // where the servo goes at power-up
const int     MIN_ANGLE   = 0;    // limits of this tool
const int     MAX_ANGLE   = 180;
const int     NUDGE_DEG   = 2;

Servo servo;
float current  = START_ANGLE;     // where the servo is now (degrees)
float target   = START_ANGLE;     // where we want it to be
float speedDps = 20.0;            // movement speed, degrees per second
unsigned long lastStepMs = 0;

char    line[16];                 // one typed command
uint8_t lineLen = 0;

void printAngle() {
  Serial.print(F("Angle now: "));
  Serial.print((int)(current + 0.5));
  Serial.print(F(" deg   (speed "));
  Serial.print((int)speedDps);
  Serial.println(F(" deg/s)"));
}

void setTarget(int deg) {
  if (deg < MIN_ANGLE) deg = MIN_ANGLE;
  if (deg > MAX_ANGLE) deg = MAX_ANGLE;
  target = deg;
  Serial.print(F("Moving to "));
  Serial.println(deg);
}

void handleLine(char *s) {
  if (s[0] == '\0') return;
  if (s[0] == '+') {
    setTarget((int)(target + 0.5) + NUDGE_DEG);
  } else if (s[0] == '-') {
    setTarget((int)(target + 0.5) - NUDGE_DEG);
  } else if (s[0] == '?') {
    printAngle();
  } else if (s[0] == 's' || s[0] == 'S') {
    float v = atof(s + 1);
    if (v >= 5 && v <= 60) {
      speedDps = v;
      printAngle();
    } else {
      Serial.println(F("Speed must be 5 to 60, e.g. s20"));
    }
  } else if (isdigit(s[0])) {
    setTarget(atoi(s));
  } else {
    Serial.println(F("Unknown. Type 0-180, +, -, s20 or ?"));
  }
}

void readSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      line[lineLen] = '\0';
      handleLine(line);
      lineLen = 0;
    } else if (lineLen < sizeof(line) - 1) {
      line[lineLen++] = c;
    }
  }
}

void setup() {
  Serial.begin(115200);
  servo.write(START_ANGLE);   // set the position BEFORE attach() so it does not jump
  servo.attach(SERVO_PIN);
  Serial.println(F("Servo calibration ready. Type 0-180, +, -, s20 or ?"));
  printAngle();
}

void loop() {
  readSerial();

  // Every 20 ms move a small step toward the target. Small steps = slow, gentle motion.
  unsigned long now = millis();
  if (now - lastStepMs >= 20) {
    float maxStep = speedDps * (now - lastStepMs) / 1000.0;
    lastStepMs = now;
    float diff = target - current;
    if (diff == 0) return;
    if (fabs(diff) <= maxStep) {
      current = target;               // arrived
      servo.write((int)(current + 0.5));
      printAngle();
    } else {
      current += (diff > 0) ? maxStep : -maxStep;
      servo.write((int)(current + 0.5));
    }
  }
}
