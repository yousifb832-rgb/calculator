/*
  robotic_glove.ino  -  Prototype v1 firmware
  Low-Cost Automatic Robotic Glove for Finger Movement Assistance

  Board   : Arduino Nano (ATmega328P). Arduino IDE 2.x, built-in Servo library.
  Motors  : servo 1 pulls the four-finger tendon, servo 2 pulls the thumb tendon.

  WHAT IT DOES
   - Repeats flexion -> hold -> extension -> rest cycles automatically.
   - Speed, range of motion, repetitions, hold and rest time can be changed
     from the PC app over USB, or by editing the defaults in section 4.
   - START and STOP push buttons. Optional MODE button (D4).
   - Watches the motor supply through A0. When the emergency switch cuts motor
     power, the program stops all motion and will not move again until power is
     back AND someone presses START (re-arm). It never restarts by itself.
   - Every position is clamped between the calibrated OPEN and CLOSED angles,
     so no command (from the PC or a bug) can drive past them.

  Research and education prototype. Not a medical device.

  SERIAL PROTOCOL (115200 baud, one command per line, not case sensitive)
     START | STOP | RESET | STATUS | PING | HELP
     MODE FULL|FINGERS|THUMB      SPEED <deg/s>     RANGE <percent>
     REPS <count>                 HOLD <ms>         REST <ms>
  The board replies "OK ..." or "ERR ...", sends "EVENT ..." when something
  happens, and a "STATUS ..." line four times per second.
*/

#include <Servo.h>
#include <math.h>
#include <string.h>
#include <ctype.h>
#include <stdlib.h>

// ============================ 1. PINS ============================
const uint8_t PIN_SERVO_FINGERS = 9;
const uint8_t PIN_SERVO_THUMB   = 10;
const uint8_t PIN_BTN_START     = 2;    // push button to GND (internal pull-up)
const uint8_t PIN_BTN_STOP      = 3;    // push button to GND
const uint8_t PIN_BTN_MODE      = 4;    // optional push button to GND
const uint8_t PIN_LED           = 13;   // the LED on the Nano board
const uint8_t PIN_MOTOR_SENSE   = A0;   // motor +5 V through a 10k/10k divider

// ======================= 2. CALIBRATION ==========================
// Copy the angles you measured with servo_calibration.ino.
//   OPEN   = finger straight, tendon just tight.
//   CLOSED = the most flexion that is still safe.
// Either number may be the larger one (it depends on how the servo is mounted).
const float FINGERS_OPEN_DEG   = 20;
const float FINGERS_CLOSED_DEG = 150;
const float THUMB_OPEN_DEG     = 20;
const float THUMB_CLOSED_DEG   = 120;

// ======================= 3. SAFETY LIMITS ========================
const float SPEED_MIN_DPS = 10;     // slowest allowed movement (deg/s, average)
const float SPEED_MAX_DPS = 90;     // fastest allowed movement
const int   RANGE_MIN_PCT = 10;     // smallest range of motion (% of calibration)
const int   RANGE_MAX_PCT = 100;    // 100 % = exactly the CLOSED angle, never more
const int   REPS_MIN = 1;
const int   REPS_MAX = 200;
const long  HOLD_MIN_MS = 0;
const long  HOLD_MAX_MS = 10000;
const long  REST_MIN_MS = 300;
const long  REST_MAX_MS = 10000;
const float RELEASE_SPEED_DPS = 60; // speed used when STOP is pressed
const unsigned long THUMB_LAG_MS = 300;  // FULL mode: fingers close first, thumb
                                         // follows; on release the thumb opens first.
                                         // This keeps the thumb from being trapped.

// Motor power sensing. Set USE_MOTOR_SENSE to false if you did not build the divider.
const bool  USE_MOTOR_SENSE  = true;
const float SENSE_DIVIDER    = 2.0;     // 10k + 10k divider halves the voltage
const float POWER_LOST_V     = 3.5;     // below this the motor supply is OFF
const float POWER_OK_V       = 4.2;     // above this the motor supply is back
const unsigned long POWER_LOST_CONFIRM_MS = 50;

// ===================== 4. DEFAULT SETTINGS =======================
float speedDps   = 40;     // degrees per second
int   rangePct   = 80;     // % of the calibrated range
int   targetReps = 10;
long  holdMs     = 1000;   // time held closed
long  restMs     = 1000;   // time resting open

enum Mode { MODE_FULL, MODE_FINGERS, MODE_THUMB, MODE_COUNT };
Mode mode = MODE_FULL;
const char *MODE_NAMES[] = { "FULL", "FINGERS", "THUMB" };

// ================= 5. TYPES AND PROGRAM STATE ====================
// (All types are declared before the first function so the Arduino IDE's
//  automatic function prototypes compile.)

// One "axis" = one servo plus the movement it is currently doing.
struct Axis {
  Servo   servo;
  uint8_t pin;
  float   openDeg, closedDeg;     // calibrated limits
  float   pos;                    // last angle sent to the servo
  float   fromDeg, toDeg;         // current movement
  unsigned long startMs, durMs;
  bool    moving;
};

Axis fingers;
Axis thumb;

// The exercise cycle: IDLE -> FLEX -> HOLD -> EXTEND -> REST -> FLEX ...
enum State { ST_IDLE, ST_FLEX, ST_HOLD, ST_EXTEND, ST_REST, ST_STOPPING, ST_ESTOP };
const char *STATE_NAMES[] = { "IDLE", "FLEX", "HOLD", "EXTEND", "REST", "STOPPING", "ESTOP" };

State state = ST_IDLE;
unsigned long stateStartMs = 0;
int repsDone = 0;

float motorVolts    = 0;
bool  motorPowerOk  = true;
bool  powerLowSeen  = false;
unsigned long powerLowSinceMs = 0;

struct Button {
  uint8_t pin;
  bool stable;      // debounced level (HIGH = not pressed, because of the pull-up)
  bool lastRead;
  unsigned long changedMs;
};

Button btnStart = { PIN_BTN_START, HIGH, HIGH, 0 };
Button btnStop  = { PIN_BTN_STOP,  HIGH, HIGH, 0 };
Button btnMode  = { PIN_BTN_MODE,  HIGH, HIGH, 0 };

// ========================= 6. MOTION =============================
int degToMicros(float deg) {
  // Servo library default: 0 deg = 544 us, 180 deg = 2400 us.
  // Microseconds give ~0.1 deg steps instead of 1 deg steps: smoother motion.
  return (int)(544.0 + deg * (2400.0 - 544.0) / 180.0 + 0.5);
}

float clampToAxis(const Axis &a, float deg) {
  float lo = (a.openDeg < a.closedDeg) ? a.openDeg : a.closedDeg;
  float hi = (a.openDeg < a.closedDeg) ? a.closedDeg : a.openDeg;
  if (deg < lo) return lo;
  if (deg > hi) return hi;
  return deg;
}

void writeAxis(Axis &a, float deg) {
  a.pos = clampToAxis(a, deg);           // THE safety clamp: every write passes here
  a.servo.writeMicroseconds(degToMicros(a.pos));
}

float flexTarget(const Axis &a) {
  return a.openDeg + (a.closedDeg - a.openDeg) * (rangePct / 100.0);
}

// Plan a smooth movement from the current position to 'target'.
void startMove(Axis &a, float target, float speed, unsigned long delayMs) {
  target    = clampToAxis(a, target);
  a.fromDeg = a.pos;
  a.toDeg   = target;
  a.durMs   = (unsigned long)(fabs(target - a.pos) / speed * 1000.0);
  if (a.durMs < 1) a.durMs = 1;
  a.startMs = millis() + delayMs;
  a.moving  = true;
}

// Called every loop: moves the servo along an S-curve (slow - faster - slow).
void updateAxis(Axis &a, unsigned long now) {
  if (!a.moving) return;
  long elapsed = (long)(now - a.startMs);
  if (elapsed < 0) return;                       // still waiting for its delay
  if ((unsigned long)elapsed >= a.durMs) {
    writeAxis(a, a.toDeg);
    a.moving = false;
    return;
  }
  float u = (float)elapsed / (float)a.durMs;      // progress 0..1
  float s = (1.0 - cos(PI * u)) / 2.0;            // smooth start and stop
  writeAxis(a, a.fromDeg + (a.toDeg - a.fromDeg) * s);
}

bool anyMoving() { return fingers.moving || thumb.moving; }

// ======================= 7. STATE MACHINE ========================
void setState(State s) {
  state = s;
  stateStartMs = millis();
}

bool usesFingers() { return mode != MODE_THUMB; }
bool usesThumb()   { return mode != MODE_FINGERS; }

void beginFlex() {
  if (usesFingers()) startMove(fingers, flexTarget(fingers), speedDps, 0);
  if (usesThumb())   startMove(thumb, flexTarget(thumb), speedDps,
                               mode == MODE_FULL ? THUMB_LAG_MS : 0);
  setState(ST_FLEX);
}

void beginExtend() {
  if (usesThumb())   startMove(thumb, thumb.openDeg, speedDps, 0);
  if (usesFingers()) startMove(fingers, fingers.openDeg, speedDps,
                               mode == MODE_FULL ? THUMB_LAG_MS : 0);
  setState(ST_EXTEND);
}

void sendEvent(const char *name, int value) {
  Serial.print(F("EVENT "));
  Serial.print(name);
  Serial.print(' ');
  Serial.println(value);
}

void startCycle() {
  repsDone = 0;
  Serial.print(F("EVENT START md="));
  Serial.print(MODE_NAMES[mode]);
  Serial.print(F(" reps="));  Serial.print(targetReps);
  Serial.print(F(" spd="));   Serial.print((int)speedDps);
  Serial.print(F(" rng="));   Serial.print(rangePct);
  Serial.print(F(" hold="));  Serial.print(holdMs);
  Serial.print(F(" rest="));  Serial.println(restMs);
  beginFlex();
}

void requestStop() {
  if (state == ST_IDLE || state == ST_ESTOP || state == ST_STOPPING) return;
  startMove(fingers, fingers.openDeg, RELEASE_SPEED_DPS, 0);
  startMove(thumb,   thumb.openDeg,   RELEASE_SPEED_DPS, 0);
  setState(ST_STOPPING);
}

void enterEstop() {
  fingers.moving = false;
  thumb.moving   = false;
  fingers.servo.detach();   // stop sending pulses: the servos go limp
  thumb.servo.detach();
  setState(ST_ESTOP);
  sendEvent("ESTOP", repsDone);
}

void attachAtOpen(Axis &a) {
  a.pos = a.openDeg;
  a.servo.writeMicroseconds(degToMicros(a.openDeg));  // position first ...
  a.servo.attach(a.pin);                              // ... then attach: no jump
}

void rearm() {
  attachAtOpen(fingers);
  attachAtOpen(thumb);
  setState(ST_IDLE);
  Serial.println(F("EVENT REARMED 0"));
}

// START button or START command
void onStart() {
  if (state == ST_IDLE) {
    startCycle();
  } else if (state == ST_ESTOP) {
    if (motorPowerOk) rearm();
    else Serial.println(F("ERR NO_MOTOR_POWER switch the motor supply back on first"));
  } else {
    Serial.println(F("ERR BUSY already running"));
  }
}

void runStateMachine(unsigned long now) {
  switch (state) {
    case ST_FLEX:
      if (!anyMoving()) setState(ST_HOLD);
      break;
    case ST_HOLD:
      if ((long)(now - stateStartMs) >= holdMs) beginExtend();
      break;
    case ST_EXTEND:
      if (!anyMoving()) {
        repsDone++;
        sendEvent("REP", repsDone);
        if (repsDone >= targetReps) {
          setState(ST_IDLE);
          sendEvent("DONE", repsDone);
        } else {
          setState(ST_REST);
        }
      }
      break;
    case ST_REST:
      if ((long)(now - stateStartMs) >= restMs) beginFlex();
      break;
    case ST_STOPPING:
      if (!anyMoving()) {
        setState(ST_IDLE);
        sendEvent("STOPPED", repsDone);
      }
      break;
    default:          // ST_IDLE and ST_ESTOP: nothing to do
      break;
  }
}

// ===================== 8. MOTOR POWER SENSE ======================
void readMotorPower(unsigned long now) {
  if (!USE_MOTOR_SENSE) { motorPowerOk = true; return; }
  float v = analogRead(PIN_MOTOR_SENSE) * (5.0 / 1023.0) * SENSE_DIVIDER;
  motorVolts = v;
  if (v < POWER_LOST_V) {
    if (!powerLowSeen) { powerLowSeen = true; powerLowSinceMs = now; }
    if (now - powerLowSinceMs >= POWER_LOST_CONFIRM_MS) motorPowerOk = false;
  } else {
    powerLowSeen = false;
    if (v > POWER_OK_V) motorPowerOk = true;
  }
}

// ========================= 9. BUTTONS ============================
// True once per press. A press must be stable for 30 ms (debounce).
bool pressed(Button &b, unsigned long now) {
  bool r = digitalRead(b.pin);
  if (r != b.lastRead) { b.lastRead = r; b.changedMs = now; }
  if (now - b.changedMs >= 30 && r != b.stable) {
    b.stable = r;
    if (r == LOW) return true;
  }
  return false;
}

void nextMode() {
  if (state != ST_IDLE) return;
  mode = (Mode)((mode + 1) % MODE_COUNT);
  Serial.print(F("EVENT MODE "));
  Serial.println(MODE_NAMES[mode]);
}

// ==================== 10. SERIAL COMMANDS ========================
char    rx[40];
uint8_t rxLen = 0;

bool settingsAllowed() {
  if (state == ST_IDLE || state == ST_ESTOP) return true;
  Serial.println(F("ERR BUSY settings can only change while stopped"));
  return false;
}

long clampLong(long v, long lo, long hi) { return v < lo ? lo : (v > hi ? hi : v); }

void replyOk(const char *what, long value) {
  Serial.print(F("OK "));
  Serial.print(what);
  Serial.print(' ');
  Serial.println(value);
}

void sendStatus() {
  Serial.print(F("STATUS st="));  Serial.print(STATE_NAMES[state]);
  Serial.print(F(" md="));    Serial.print(MODE_NAMES[mode]);
  Serial.print(F(" rep="));   Serial.print(repsDone);
  Serial.print(F(" reps="));  Serial.print(targetReps);
  Serial.print(F(" f="));     Serial.print(fingers.pos, 1);
  Serial.print(F(" t="));     Serial.print(thumb.pos, 1);
  Serial.print(F(" v="));
  if (USE_MOTOR_SENSE) Serial.print(motorVolts, 2); else Serial.print(F("NA"));
  Serial.print(F(" spd="));   Serial.print((int)speedDps);
  Serial.print(F(" rng="));   Serial.print(rangePct);
  Serial.print(F(" hold="));  Serial.print(holdMs);
  Serial.print(F(" rest="));  Serial.println(restMs);
}

void printHelp() {
  Serial.println(F("INFO commands: START STOP RESET STATUS PING HELP"));
  Serial.println(F("INFO MODE FULL|FINGERS|THUMB  SPEED 10-90  RANGE 10-100"));
  Serial.println(F("INFO REPS 1-200  HOLD 0-10000  REST 300-10000"));
}

void handleCommand(char *line) {
  for (char *p = line; *p; p++) *p = toupper(*p);
  char *cmd = strtok(line, " =,");
  char *arg = strtok(NULL, " =,");
  if (cmd == NULL) return;
  long val = (arg != NULL) ? atol(arg) : 0;

  if (!strcmp(cmd, "START")) {
    onStart();
  } else if (!strcmp(cmd, "STOP")) {
    requestStop();
    Serial.println(F("OK STOP"));
  } else if (!strcmp(cmd, "RESET")) {
    if (state == ST_ESTOP && motorPowerOk) rearm();
    else if (state == ST_ESTOP) Serial.println(F("ERR NO_MOTOR_POWER switch the motor supply back on first"));
    else Serial.println(F("OK RESET nothing to reset"));
  } else if (!strcmp(cmd, "STATUS")) {
    sendStatus();
  } else if (!strcmp(cmd, "PING")) {
    Serial.println(F("PONG"));
  } else if (!strcmp(cmd, "HELP")) {
    printHelp();
  } else if (strcmp(cmd, "MODE") && strcmp(cmd, "SPEED") && strcmp(cmd, "RANGE") &&
             strcmp(cmd, "REPS") && strcmp(cmd, "HOLD")  && strcmp(cmd, "REST")) {
    Serial.println(F("ERR UNKNOWN_COMMAND type HELP"));
  } else if (arg == NULL) {
    Serial.println(F("ERR MISSING_VALUE e.g. SPEED 40"));
  } else if (!strcmp(cmd, "MODE")) {
    if (!settingsAllowed()) return;
    if (!strcmp(arg, "FULL") || !strcmp(arg, "0"))         mode = MODE_FULL;
    else if (!strcmp(arg, "FINGERS") || !strcmp(arg, "1")) mode = MODE_FINGERS;
    else if (!strcmp(arg, "THUMB") || !strcmp(arg, "2"))   mode = MODE_THUMB;
    else { Serial.println(F("ERR BAD_MODE use FULL, FINGERS or THUMB")); return; }
    Serial.print(F("OK MODE "));
    Serial.println(MODE_NAMES[mode]);
  } else if (!strcmp(cmd, "SPEED")) {
    if (!settingsAllowed()) return;
    speedDps = clampLong(val, (long)SPEED_MIN_DPS, (long)SPEED_MAX_DPS);
    replyOk("SPEED", (long)speedDps);
  } else if (!strcmp(cmd, "RANGE")) {
    if (!settingsAllowed()) return;
    rangePct = clampLong(val, RANGE_MIN_PCT, RANGE_MAX_PCT);
    replyOk("RANGE", rangePct);
  } else if (!strcmp(cmd, "REPS")) {
    if (!settingsAllowed()) return;
    targetReps = clampLong(val, REPS_MIN, REPS_MAX);
    replyOk("REPS", targetReps);
  } else if (!strcmp(cmd, "HOLD")) {
    if (!settingsAllowed()) return;
    holdMs = clampLong(val, HOLD_MIN_MS, HOLD_MAX_MS);
    replyOk("HOLD", holdMs);
  } else if (!strcmp(cmd, "REST")) {
    if (!settingsAllowed()) return;
    restMs = clampLong(val, REST_MIN_MS, REST_MAX_MS);
    replyOk("REST", restMs);
  }
}

void readSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (rxLen > 0) {
        rx[rxLen] = '\0';
        handleCommand(rx);
        rxLen = 0;
      }
    } else if (rxLen < sizeof(rx) - 1) {
      rx[rxLen++] = c;
    }
  }
}

// ======================== 11. STATUS LED =========================
void updateLed(unsigned long now) {
  bool on;
  switch (state) {
    case ST_IDLE:     on = (now % 1000) < 100; break;   // short blink: ready
    case ST_ESTOP:    on = (now % 200)  < 100; break;   // fast blink: emergency stop
    case ST_STOPPING: on = (now % 400)  < 200; break;   // medium blink: stopping
    default:          on = true;                        // steady: running
  }
  digitalWrite(PIN_LED, on ? HIGH : LOW);
}

// ===================== 12. SETUP AND LOOP ========================
unsigned long lastStatusMs = 0;
unsigned long lastSenseMs  = 0;

void setupAxis(Axis &a, uint8_t pin, float openDeg, float closedDeg) {
  a.pin       = pin;
  a.openDeg   = openDeg;
  a.closedDeg = closedDeg;
  a.moving    = false;
  attachAtOpen(a);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BTN_START, INPUT_PULLUP);
  pinMode(PIN_BTN_STOP,  INPUT_PULLUP);
  pinMode(PIN_BTN_MODE,  INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);

  setupAxis(fingers, PIN_SERVO_FINGERS, FINGERS_OPEN_DEG, FINGERS_CLOSED_DEG);
  setupAxis(thumb,   PIN_SERVO_THUMB,   THUMB_OPEN_DEG,   THUMB_CLOSED_DEG);
  setState(ST_IDLE);

  Serial.println(F("READY ROBOTIC-GLOVE v1.0"));
  Serial.print(F("INFO calibration fingers "));
  Serial.print(FINGERS_OPEN_DEG, 0); Serial.print('-'); Serial.print(FINGERS_CLOSED_DEG, 0);
  Serial.print(F(" thumb "));
  Serial.print(THUMB_OPEN_DEG, 0);   Serial.print('-'); Serial.println(THUMB_CLOSED_DEG, 0);
}

void loop() {
  unsigned long now = millis();

  // 1) Safety first: is the motor supply still on?
  if (now - lastSenseMs >= 5) {
    lastSenseMs = now;
    readMotorPower(now);
    if (!motorPowerOk && state != ST_ESTOP) enterEstop();
  }

  // 2) Buttons. STOP is checked before START.
  if (pressed(btnStop, now))  requestStop();
  if (pressed(btnStart, now)) onStart();
  if (pressed(btnMode, now))  nextMode();

  // 3) Commands from the PC
  readSerial();

  // 4) Move the servos and advance the exercise cycle
  if (state != ST_ESTOP) {
    updateAxis(fingers, now);
    updateAxis(thumb, now);
    runStateMachine(now);
  }

  // 5) Report to the PC and show state on the LED
  if (now - lastStatusMs >= 250) {
    lastStatusMs = now;
    sendStatus();
  }
  updateLed(now);
}
