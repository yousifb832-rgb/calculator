Hi Claude Code! This message is our full project brief. Please read all of it.

=== STEP 0 (do this first) ===
1. Save this entire message, exactly as written, as docs/BRIEF.md in this folder.
2. Write a short CLAUDE.md (under 120 lines) with: who we are, how to work with us,
   the key decisions, the safety rules, and this line:
   "Before starting any phase, read that phase in docs/BRIEF.md."
3. Create PROGRESS.md. Then do "START NOW" at the bottom.

=== 1. WHO WE ARE ===
- Two 2nd-year medical device (biomedical) engineering students in Iraq:
  Yousif Basil and [friend's name]. Ask us for the second name and update the files.
- We have ZERO coding experience. Every tool and command is new to us.
- English is our second language: use short, simple sentences.
- We use Windows PCs and have a small budget.
- EVERYTHING is in English: your explanations, the code, comments, the website, all docs.
- Goal: a real, working, advanced device + a great, lively website that we can demo
  and defend in front of our professors.

=== 2. THE PROJECT: "PercuMap" (working name) - robotic percussion in real time ===
Percussion is a classic physical exam (since 1761): the doctor taps the chest or belly
and listens. Air sounds "resonant" (lung) or "tympanic" (stomach gas). Solid organs and
fluid sound "dull" (liver, fluid). Muscle sounds "flat" (thigh). Doctors use it to find
organ borders, fluid around the lung, and how far the diaphragm moves when you breathe.
But it depends on the doctor's finger and ear, and measuring organ size by percussion
has very poor agreement between doctors.

Our device does percussion like a robot, in real time:
- A small solenoid "hammer" taps a plastic disc on the skin with the SAME force every
  time.
- A microphone (INMP441) records the sound. In under 1 second the website shows the
  waveform, the spectrum and the result: RESONANT / DULL / TYMPANIC / FLAT, with a
  confidence level.
- MAP mode: tap a grid of points on a body diagram -> a color map of the chest/belly.
- BORDER mode: move the device 1 cm at a time along a ruler line -> the website finds
  the exact point where resonant turns dull (e.g. the lung-liver border).
- DIAPHRAGM mode: find the border at full breath-out and at full breath-in -> the
  distance between them = diaphragmatic excursion (normally a few cm).

Why it is new: research groups have built percussion devices that classify the sound
at one spot (for example "Tabla", 2018). We could not find any device that finds organ
borders or measures diaphragmatic excursion automatically and in real time. That is
our "first". Before we claim "first" in our report, search the literature again and
cite what exists.

Limit to remember: percussion only "sees" about 5-6 cm deep, like a doctor's finger.

=== 3. HOW YOU WORK WITH US (most important) ===
1. One small step at a time. Each step: (a) what and why, max 2 lines; (b) exactly what
   we click, type or plug in; (c) how we check it worked; (d) STOP and wait for us.
2. Define every new word the first time (one line + an everyday example).
3. You run the commands (installs, builds, uploads) so we don't mistype them. Before
   each command, say in one line what it does. Ask before installing anything.
4. Small pieces of code, tested after each piece. Never leave the project broken.
   Comments explain WHY. No big rewrites without asking us.
5. Before any wiring: give a pin-to-pin table, then ask for a clear photo of our wiring
   and check it BEFORE we plug in the USB cable.
6. When something breaks: explain the error in plain words, say the cause, then fix it.
7. Teach us. At the end of each phase, ask us 2-3 short questions (professors will
   question us). Save the questions and good answers in docs/VIVA_QA.md.
8. Be honest. Never invent data or results. Label simulated data "DEMO DATA" everywhere.
9. Free tools only. Ask before suggesting anything that costs money.
10. There are two of us. At each session start, ask who types ("driver") and who checks
    and takes notes ("navigator"). Remind us to swap roles every session.

=== 4. SESSION ROUTINE ===
- Start of every session: read PROGRESS.md, then tell us in 3 lines where we are,
  what's next, and anything blocked.
- End of a session (or when we say "save progress"): update PROGRESS.md
  (done / next / problems / decisions) and make a git commit with a clear message.
- Keep sessions focused (our plan has usage limits). Suggest a fresh session when a big
  topic is finished.

=== 5. HARDWARE (decided - ask before changing) ===
Parts (approx. AliExpress prices; buy spares of the cheap parts):
- ESP32 DevKit (ESP32-WROOM-32), x2 ............................ $2-6 each
- INMP441 I2S MEMS microphone module, x2 ........................ $1-2 each
- 5 V push-pull solenoid, about 10 mm stroke (e.g. 0837B type) .. $3-9
- Logic-level MOSFET switch module that works with a 3.3 V signal
  (e.g. AOD4184 / D4184 type) ................................... $1-2
- Diodes 1N5819 (or 1N4007) x2, electrolytic capacitor 2200 uF 16 V,
  10k ohm resistor .............................................. $1
- Push button, breadboard, jumper wires ......................... $3-5
- Housing: a piece of PVC pipe (3-4 cm wide) or a 3D print, foam rubber, a small hard
  plastic disc (2-3 cm) as the "pleximeter", medical tape, a paper tape measure.
- A data-capable USB cable (many cheap cables are charge-only - test it first).
- From home: plastic bottles, water, a ruler, a wooden board.

Wiring (ESP32 DevKit - confirm against our board's labels):
- INMP441: VDD->3V3, GND->GND, SCK->GPIO26, WS->GPIO25, SD->GPIO33, L/R->GND.
- Solenoid: MOSFET module signal->GPIO27, module GND->ESP32 GND. A 10k ohm resistor from
  GPIO27 to GND keeps the solenoid OFF while the ESP32 boots. Module power from the
  5 V pin (USB) and GND. Solenoid on the module output. Diode across the solenoid
  (stripe to +5 V). 2200 uF capacitor between 5 V and GND near the module -
  CHECK THE POLARITY (the stripe is minus). If the ESP32 resets when the solenoid
  fires, power the solenoid from a USB power bank and connect the grounds.
- Button: GPIO14 -> button -> GND (internal pull-up).

The handheld head: the solenoid sits in the tube; its plunger hits the plastic disc that
rests on the skin. The microphone sits in a small sealed cup next to the disc, touching
the skin, with foam between it and the solenoid body to block the click.

=== 6. SOFTWARE (decided) ===
- Firmware (firmware/): Arduino C++ on the ESP32, compiled and uploaded by YOU with
  arduino-cli. I2S microphone at 16 kHz (raise it if needed).
  One "tap" = start recording, fire the solenoid for a short pulse (default 15 ms),
  record about 300 ms in total, then send the samples to the PC.
  Taps come from the website (Web Serial command), the button, or an auto-scan timer.
  Firmware safety limits: max pulse 40 ms, at least 400 ms between taps, solenoid
  always OFF after a pulse or an error. Document the protocol in docs/PROTOCOL.md.
- Website (web/): Vite + React + Tailwind CSS, JavaScript (not TypeScript).
  Live mode = Web Serial in Chrome or Edge on a PC.
  Demo mode = a realistic simulator: synthetic taps (damped vibrations with a different
  pitch and decay for each class, plus noise), a demo body and a demo border scan.
  Same data interface for both. Demo data is always badged "DEMO DATA".
  We build the full website BEFORE the parts arrive.
- Analysis (web/src/analysis/): small pure functions + unit tests (Vitest).
- Storage: browser only (IndexedDB). No backend, no accounts. Profiles use codes
  (P01, P02), never real names. Export CSV, JSON and WAV.
- Deploy at the end: GitHub Pages or Netlify (free, HTTPS, so live mode works there).

=== 7. HOW ONE TAP IS ANALYZED (real time, under 1 second) ===
1. Find the moment of impact, cut a fixed window after it, remove noise.
2. Features: peak level, decay time (how fast the sound dies, e.g. the -20 dB time),
   dominant frequency, spectral centroid, low/high band energy ratio, and length above
   the noise floor.
3. Classifier v1: simple rules from our own labeled calibration taps.
   Classifier v2: k-nearest neighbours trained in the browser on our labeled dataset,
   with honest accuracy (leave-one-out). Show the confidence; say "unsure" when unsure.
4. Personal calibration: a few reference taps per person (upper chest = resonant,
   thigh = flat) to adjust for body size and fat.
5. Border finder: a "resonance score" for each position along the line, then the point
   where the score crosses halfway between the resonant and dull levels
   (interpolated, in cm).
6. Diaphragmatic excursion = border at full breath-in minus border at full breath-out,
   with on-screen breath-hold prompts.

=== 8. WEBSITE SPEC (make it really good and lively) ===
- Feel: "acoustics lab meets clinic". Dark navy base, glowing sound-wave accents, clean
  white cards. Light mode too.
- The star: every tap makes a ripple animation, the waveform draws itself, the spectrum
  bars jump, and the result card flips in - all within a second. A "play" button
  replays the real tap sound.
- Pages:
  - Home: what percussion is (with sound examples), why objective percussion matters,
    how our device works, a "Try the demo" button, the team.
  - Tap: single-tap mode with live waveform, spectrum, result and confidence.
  - Map: front/back body diagram with numbered points; each tap paints its point;
    left vs right comparison.
  - Border & Diaphragm: guided 1-cm scan along a ruler line, a live plot of the
    resonance score vs position, the border line, and the excursion result.
  - Lab (our research tools): labeled dataset recorder, classifier training +
    confusion matrix, repeatability stats (mean, SD, CV), test templates for
    section 9, robot-tap vs finger-tap comparison, exports.
  - About: the science with references (verify every link before adding it),
    limitations, team, disclaimer.
- Motion: smooth and fast; respect prefers-reduced-motion. Keyboard friendly, WCAG AA
  contrast, works on phones in demo mode. Live mode needs Chrome/Edge on a PC - show a
  friendly message elsewhere.
- Every result shows: "Research & teaching prototype - not a medical device.
  Not for diagnosis."

=== 9. HOW WE PROVE IT WORKS (testing plan - no video needed) ===
All tests use phantoms, our own bodies, or consenting healthy friends.
1. Phantom test (known answers): an empty sealed bottle, a bottle full of water and a
   thick wooden board. Accuracy per class.
2. Water-line test (our "fake diaphragm"): a tall bottle half full of water. Scan down
   its side 1 cm at a time; the device must find the water line. Measure the real line
   with a ruler and report the error in cm. Change the water level - the border must
   move with it.
3. Body landmarks: upper chest (resonant), right lower ribs (dull, liver), left upper
   belly (tympanic, stomach gas), thigh (flat). A doctor or our professor confirms each
   label by manual percussion. Report accuracy and a confusion matrix.
4. Repeatability: 20 robot taps on the same spot vs 20 finger taps recorded by the same
   microphone. Compare the variation (CV) - is the robot more consistent?
5. Diaphragm test: back of the chest (scapular line), full breath-out vs full
   breath-in, 3 repeats per person. Mean +/- SD, compared with normal values from the
   literature (and with ultrasound if the college can measure it - a bonus).
6. Examiner spread: 3 students mark the liver border by finger percussion; compare
   their spread with the device's spread.
Results go in docs/VALIDATION.md and on the Lab page. Never "clean up" data.

=== 10. SAFETY & ETHICS (non-negotiable) ===
- Gentle taps only. Start with the shortest pulse and test on your own forearm first.
- Never tap the head, face, eyes, neck or throat. Never over injuries, bruises,
  fractures or recent surgery. Not on a pregnant belly. Nobody with a pacemaker or
  other implanted device. Stop if it is uncomfortable.
- USB power or a power bank only; nothing connected to mains (wall) power.
- Solenoids get hot: respect the firmware limits. Electrolytic capacitors can burst if
  connected backwards - double-check polarity before power-on.
- Consent, anonymous codes, healthy volunteers only. Anything involving patients needs
  our supervisor and the college ethics committee first.
- Never present the device as diagnostic - not in the app, the report or the slides.

=== 11. PHASES (in order; finish every "Done when" before moving on) ===
Phase 0 - Setup + first win (no hardware)
  Check/install Git, Node.js LTS and Chrome or Edge (VS Code optional). Create the
  folders (firmware/, web/, docs/, data/), git init, first commit. A tiny page that
  plays a fake "knock" sound and draws its waveform and spectrum.
  Done when: we opened that page ourselves and can explain Node.js, git and "spectrum".
Phase 1 - The website in demo mode (no hardware)
  Design system first (show us and ask our opinion), then all pages with the simulator.
  Done when: demo tapping, the body map and a demo border scan all work, it looks
  great, and we can start the site ourselves.
Phase 2 - Hardware hello (parts needed)
  arduino-cli + ESP32 board package + USB driver; blink; microphone test (live sound
  level); solenoid driver with the photo check; first safe taps on a bottle.
  Done when: the mic hears a finger snap, the solenoid taps on command, and the wiring
  photo is saved in docs/photos/.
Phase 3 - Live link
  "Connect device" button (Web Serial); tap command; each tap's sound arrives and is
  drawn in under 1 second; record & replay taps (data/).
  Done when: 20 taps in a row arrive with no errors and unplug/replug recovers.
Phase 4 - The brain
  Features, classifier v1 -> v2, personal calibration, border finder, excursion;
  unit tests on synthetic taps; tuning on the phantoms.
  Done when: tests pass, the phantoms are classified correctly most of the time, and
  the water-line test works.
Phase 5 - Testing & research
  Run section 9. Charts on the Lab page; methods, results and honest limitations in
  docs/VALIDATION.md.
Phase 6 - Ship & present
  Deploy the site; README.md (what it is, parts + prices, how to run, disclaimer);
  report draft (docs/REPORT.md, including a literature check of our "first" claim);
  slide content; a 3-minute live demo script; a mock viva from docs/VIVA_QA.md.
  Done when: the public link works and each of us can explain the whole system alone.
Stretch (only if time is left): an auto-scan wheel (rotary encoder) so the device taps
automatically every 1 cm while we slide it along the skin.

=== START NOW (first session only) ===
Do STEP 0. Then explain the whole project to us in 5 simple lines, ask who is typing
today, and start Phase 0. If our parts haven't arrived yet, that's fine: Phases 0 and 1
need no hardware.
