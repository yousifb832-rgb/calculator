# CLAUDE.md - PercuMap

Before starting any phase, read that phase in docs/BRIEF.md.

## Who we are
- Yousif Basil and [friend's name - ask, then update this file and PROGRESS.md].
- 2nd-year medical device (biomedical) engineering students in Iraq.
- Zero coding experience. Every tool and command is new to us.
- English is our second language: short, simple sentences.
- Windows PCs. Small budget.
- Everything is in English: explanations, code, comments, website, docs.
- Goal: a real, working device + a lively website we can demo and defend in front of
  our professors.

## The project (short)
PercuMap = robotic percussion in real time. A solenoid "hammer" taps a plastic disc on
the skin with the same force every time. An INMP441 microphone records the sound. In
under 1 second the website shows the waveform, the spectrum and the result
(RESONANT / DULL / TYMPANIC / FLAT) with a confidence level.
Modes: TAP, MAP (body grid), BORDER (1-cm scan finds where resonant turns dull),
DIAPHRAGM (border at full breath-out vs full breath-in = excursion).
Limit: percussion only "sees" about 5-6 cm deep.

## How to work with us
1. One small step at a time: (a) what + why, max 2 lines; (b) exactly what to click,
   type or plug in; (c) how to check it worked; (d) STOP and wait for us.
2. Define every new word the first time: one line + an everyday example.
3. You run the commands (installs, builds, uploads). Before each command, say in one
   line what it does. Ask before installing anything.
4. Small pieces of code, tested after each piece. Never leave the project broken.
   Comments explain WHY. No big rewrites without asking us.
5. Before any wiring: a pin-to-pin table, then ask for a clear photo of the wiring and
   check it BEFORE the USB cable is plugged in.
6. When something breaks: the error in plain words, the cause, then the fix.
7. End of each phase: ask us 2-3 short viva questions. Save the questions and good
   answers in docs/VIVA_QA.md.
8. Be honest. Never invent data or results. Simulated data is labeled "DEMO DATA"
   everywhere.
9. Free tools only. Ask before suggesting anything that costs money.
10. Two of us: at each session start, ask who types ("driver") and who checks and takes
    notes ("navigator"). Remind us to swap roles every session.

## Session routine
- Start: read PROGRESS.md. Tell us in 3 lines: where we are, what is next, what is
  blocked. Then ask who is driver and navigator today.
- End (or when we say "save progress"): update PROGRESS.md (done / next / problems /
  decisions) and make a git commit with a clear message.
- Keep sessions focused (usage limits). Suggest a fresh session when a big topic ends.

## Where commands run
- Claude may run in a cloud computer, not on our PC. The cloud is fine for building
  and testing the website. Installs on our Windows PC, USB, ESP32 uploads and Web
  Serial need a Claude session running on our PC. Always say which machine a command
  runs on.

## Key decisions (ask before changing)
- Hardware: ESP32 DevKit (WROOM-32), INMP441 I2S mic, 5 V push-pull solenoid (~10 mm
  stroke, 0837B type), logic-level MOSFET module (AOD4184 / D4184 type), 1N5819 diode,
  2200 uF 16 V capacitor, 10k resistor, push button. Full list: docs/BRIEF.md section 5.
- Pins (confirm against the board's labels):
  INMP441 VDD->3V3, GND->GND, SCK->GPIO26, WS->GPIO25, SD->GPIO33, L/R->GND.
  MOSFET signal->GPIO27, with 10k from GPIO27 to GND. Button GPIO14->GND (pull-up).
- Firmware (firmware/): Arduino C++, built and uploaded with arduino-cli. I2S mic at
  16 kHz. One tap = start recording, pulse the solenoid (default 15 ms), record about
  300 ms in total, send the samples to the PC. Protocol: docs/PROTOCOL.md.
- Website (web/): Vite + React + Tailwind CSS, JavaScript (not TypeScript).
  Live mode = Web Serial (Chrome/Edge on a PC). Demo mode = simulator with the SAME data
  interface. Demo data is always badged "DEMO DATA". Build the full site before parts.
- Analysis (web/src/analysis/): small pure functions + Vitest unit tests.
- Storage: browser only (IndexedDB). No backend, no accounts. Profile codes (P01, P02),
  never real names. Export CSV, JSON, WAV.
- Deploy at the end: GitHub Pages or Netlify (free, HTTPS).
- Folders: firmware/, web/, docs/, data/. This repo also holds older projects
  (calculator files at the root, electronic-circuits/, robotic-glove/). Leave them
  alone unless we ask.

## Safety rules (non-negotiable)
- Firmware limits: max pulse 40 ms; at least 400 ms between taps; solenoid always OFF
  after a pulse or any error.
- Gentle taps only. Start with the shortest pulse. Test on your own forearm first.
- Never tap the head, face, eyes, neck or throat. Never over injuries, bruises,
  fractures or recent surgery. Not on a pregnant belly. Nobody with a pacemaker or
  other implanted device. Stop if it is uncomfortable.
- USB power or a USB power bank only. Nothing connected to mains (wall) power.
- Solenoids get hot: respect the firmware limits.
- Electrolytic capacitors can burst if connected backwards: check polarity (stripe =
  minus) before power-on.
- Consent, anonymous codes, healthy volunteers only. Anything with patients needs our
  supervisor and the college ethics committee first.
- Never present the device as diagnostic (app, report, slides). Every result shows:
  "Research & teaching prototype - not a medical device. Not for diagnosis."

## Honesty rules for results and the report
- Never "clean up" data. Results go in docs/VALIDATION.md and on the Lab page.
- Verify every reference and link before adding it.
- Before claiming "first", search the literature again and cite what exists
  (including the prior work named in the brief).
