# PROGRESS - PercuMap

Last updated: 2026-11-25 (session 1)

## Where we are
Phase 0 (Setup + first win) - IN PROGRESS.

## Phases
- [ ] Phase 0 - Setup + first win (no hardware)
- [ ] Phase 1 - The website in demo mode (no hardware)
- [ ] Phase 2 - Hardware hello (parts needed)
- [ ] Phase 3 - Live link
- [ ] Phase 4 - The brain
- [ ] Phase 5 - Testing & research
- [ ] Phase 6 - Ship & present

## Phase 0 checklist
- [x] Brief saved as docs/BRIEF.md; CLAUDE.md and PROGRESS.md created
- [x] Folders created: firmware/, web/, docs/, data/
- [x] Git repository + first commit (the repo already existed on GitHub, so no
      "git init" was needed)
- [ ] Step 1: check Git, Node.js and Chrome/Edge on the PC we will use
- [ ] Install the missing tools (ask first)
- [ ] Tiny "knock" page: plays a fake knock sound, draws its waveform and spectrum
- [ ] We open that page ourselves
- [ ] We can explain Node.js, git and "spectrum" (viva questions -> docs/VIVA_QA.md)

## Next
- Get the friend's name and today's driver / navigator.
- Phase 0, Step 1: check the tools on the PC.

## Problems / blocked
- Friend's name not known yet. Update CLAUDE.md and this file when we know it.
- This session runs in a cloud computer. It cannot install programs on our PC or reach
  the ESP32 over USB. For PC installs and for Phase 2+, we need a Claude session that
  runs on our own PC.
- Parts: not known yet if they are ordered.

## Decisions
- 2026-11-25: PercuMap files live at the repo root (docs/, firmware/, web/, data/), as
  the brief says. The older projects in this repo stay untouched.

## Notes for later (not decided yet)
- Phase 3 speed: one tap = 300 ms x 16 kHz x 2 bytes = about 9.6 KB. At 115200 baud
  that takes about 0.8 s, which breaks the "under 1 second" goal. Idea: send binary
  data at 921600 baud (about 0.1 s). Decide when we write docs/PROTOCOL.md.
- Phase 6 deploy: the GitHub repo is named "calculator" and holds older projects. We
  may want a separate "percumap" repo. Decide then.
- Find and check the prior work named in the brief ("Tabla", 2018) before we cite it.

## Session log
- Session 1 (2026-11-25): Step 0 done. Driver: ? Navigator: ?
