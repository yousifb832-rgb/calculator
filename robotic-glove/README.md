# Low-Cost Robotic Assistance Glove

Second-year Medical Devices Technology Engineering project: a tendon-driven glove that assists
finger flexion and extension for rehabilitation research.

**Education and research prototype. Not a medical device.** All powered testing is done on the
artificial finger and the artificial hand. No patients.

## What is here

| Path | What it is |
| --- | --- |
| `index.html` | The full build guide: design review, mechanics, wiring, code walkthrough, ten stages, IQD budget tool, testing and safety, schedule. Open it in any browser. |
| `firmware/servo_calibration/servo_calibration.ino` | Stage 1 tool: moves one servo slowly to the angle you type, to find OPEN and CLOSED. |
| `firmware/robotic_glove/robotic_glove.ino` | Full Arduino Nano program: two servos, START/STOP/MODE buttons, E-stop sensing on A0, USB command protocol. |
| `pc_app/glove_control.py` | PC control panel (Python 3.8+, Tkinter, pyserial) with a built-in simulator and CSV logging. |
| `robotic-glove-project.zip` | The two sketches and the PC app in one download. |
| `site/` | `template.html` and `build.py` that generate `index.html` (run `python3 site/build.py`). |

## Quick start

1. Arduino IDE 2: board **Arduino Nano**, processor **ATmega328P** (use **Old Bootloader** if upload fails).
2. Upload `servo_calibration.ino`, find your OPEN and CLOSED angles, and put them in section 2 of `robotic_glove.ino`.
3. PC app: `pip install pyserial`, then `python pc_app/glove_control.py`. Pick **SIMULATOR (no hardware)** to try it without the Arduino.

## How the code was checked

- `robotic_glove.ino` was compiled with g++ against mock Arduino and Servo headers and run through
  simulated sessions: full cycles, clamping of out-of-range settings, STOP button, E-stop with no
  automatic restart, mode button and the fingers-before-thumb order. All passed.
- `glove_control.py` was run headlessly against its simulator: two sessions logged to CSV
  (COMPLETED and E-STOP), START refused during an emergency stop, re-arm working.
- It has **not** been compiled with the real AVR toolchain or run on real hardware yet. That
  happens in Stage 1.
