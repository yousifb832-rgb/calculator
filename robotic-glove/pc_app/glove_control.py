#!/usr/bin/env python3
"""
glove_control.py - PC control panel for the Low-Cost Robotic Assistance Glove

What it does
  * Connects to the Arduino over USB (or to a built-in SIMULATOR, no hardware needed)
  * START / STOP / RE-ARM the movement cycle
  * Sends the settings: mode, speed, range of motion, repetitions, hold and rest time
  * Shows the live state, repetition count, servo angles and motor-supply voltage
  * Saves one row per test session to glove_results.csv (opens in Excel)

Install once:   pip install pyserial
Run:            python glove_control.py

Research and education prototype. Not a medical device.
"""

import csv
import os
import queue
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk

try:
    import serial
    import serial.tools.list_ports
except ImportError:          # the app still runs, with the simulator only
    serial = None

BAUD = 115200
SIMULATOR = "SIMULATOR (no hardware)"
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_FILE = os.path.join(HERE, "glove_results.csv")
CSV_COLUMNS = [
    "test_id", "tester", "date", "start_time", "end_time", "duration_s",
    "mode", "speed_deg_s", "range_pct", "hold_ms", "rest_ms",
    "reps_target", "reps_completed", "result", "min_motor_v", "notes",
]

STATE_TEXT = {      # Arduino state -> (text shown, colour)
    "IDLE": ("Ready", "#3b6ea5"),
    "FLEX": ("Flexing", "#2e8b57"),
    "HOLD": ("Holding", "#2e8b57"),
    "EXTEND": ("Extending", "#2e8b57"),
    "REST": ("Resting", "#2e8b57"),
    "STOPPING": ("Stopping...", "#c77700"),
    "ESTOP": ("EMERGENCY STOP", "#c0392b"),
}


def parse_fields(words):
    """['st=IDLE', 'rep=3'] -> {'st': 'IDLE', 'rep': '3'}"""
    fields = {}
    for word in words:
        if "=" in word:
            key, value = word.split("=", 1)
            fields[key] = value
    return fields


# ----------------------------------------------------------------------------
#  Link to the real Arduino
# ----------------------------------------------------------------------------
class SerialLink:
    """Opens the COM port. A background thread puts every received line in a queue."""

    def __init__(self, port, inbox):
        self.inbox = inbox
        self.ser = serial.Serial(port, BAUD, timeout=0.1)
        self.running = True
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        buffer = b""
        while self.running:
            try:
                data = self.ser.read(256)
            except (serial.SerialException, OSError) as exc:
                if self.running:
                    self.inbox.put(("LINK_LOST", str(exc)))
                return
            if not data:
                continue
            buffer += data
            while b"\n" in buffer:
                raw, buffer = buffer.split(b"\n", 1)
                text = raw.decode("ascii", errors="replace").strip()
                if text:
                    self.inbox.put(("LINE", text))

    def send(self, text):
        self.ser.write((text + "\n").encode("ascii"))

    def close(self):
        self.running = False
        self.thread.join(timeout=0.5)
        try:
            self.ser.close()
        except Exception:
            pass


# ----------------------------------------------------------------------------
#  Simulator: behaves like the Arduino firmware, for testing without hardware
# ----------------------------------------------------------------------------
class SimulatedGlove:
    OPEN = {"f": 20.0, "t": 20.0}
    CLOSED = {"f": 150.0, "t": 120.0}

    def __init__(self, inbox):
        self.inbox = inbox
        self.lock = threading.Lock()
        self.state, self.mode = "IDLE", "FULL"
        self.rep, self.reps = 0, 10
        self.speed, self.range, self.hold, self.rest = 40, 80, 1000, 1000
        self.pos = dict(self.OPEN)
        self.goal = dict(self.OPEN)
        self.move_speed = self.speed
        self.timer_end = 0.0
        self.power_on = True
        self.running = True
        self.inbox.put(("LINE", "READY ROBOTIC-GLOVE v1.0 (simulator)"))
        threading.Thread(target=self._run, daemon=True).start()

    # --- helpers -------------------------------------------------------------
    def _say(self, text):
        self.inbox.put(("LINE", text))

    def _flex_goal(self, key):
        o, c = self.OPEN[key], self.CLOSED[key]
        return o + (c - o) * self.range / 100.0

    def _set_goals(self, closing, speed):
        uses_f = self.mode != "THUMB"
        uses_t = self.mode != "FINGERS"
        self.goal["f"] = self._flex_goal("f") if (closing and uses_f) else self.OPEN["f"]
        self.goal["t"] = self._flex_goal("t") if (closing and uses_t) else self.OPEN["t"]
        self.move_speed = speed

    def _arrived(self):
        return all(abs(self.pos[k] - self.goal[k]) < 0.05 for k in self.pos)

    def _status(self):
        self._say(
            "STATUS st={} md={} rep={} reps={} f={:.1f} t={:.1f} v={} spd={} rng={} "
            "hold={} rest={}".format(
                self.state, self.mode, self.rep, self.reps, self.pos["f"], self.pos["t"],
                "5.03" if self.power_on else "0.00", self.speed, self.range,
                self.hold, self.rest))

    # --- the same state machine as the firmware ----------------------------
    def _run(self):
        last, last_status = time.time(), 0.0
        while self.running:
            time.sleep(0.02)
            now = time.time()
            dt, last = now - last, now
            with self.lock:
                if not self.power_on and self.state != "ESTOP":
                    self.state = "ESTOP"
                    self._say("EVENT ESTOP {}".format(self.rep))
                if self.state != "ESTOP":
                    for k in self.pos:
                        step = self.move_speed * dt
                        diff = self.goal[k] - self.pos[k]
                        self.pos[k] = self.goal[k] if abs(diff) <= step else self.pos[k] + step * (1 if diff > 0 else -1)
                    self._advance(now)
                if now - last_status >= 0.25:
                    last_status = now
                    self._status()

    def _advance(self, now):
        s = self.state
        if s == "FLEX" and self._arrived():
            self.state, self.timer_end = "HOLD", now + self.hold / 1000.0
        elif s == "HOLD" and now >= self.timer_end:
            self._set_goals(False, self.speed)
            self.state = "EXTEND"
        elif s == "EXTEND" and self._arrived():
            self.rep += 1
            self._say("EVENT REP {}".format(self.rep))
            if self.rep >= self.reps:
                self.state = "IDLE"
                self._say("EVENT DONE {}".format(self.rep))
            else:
                self.state, self.timer_end = "REST", now + self.rest / 1000.0
        elif s == "REST" and now >= self.timer_end:
            self._set_goals(True, self.speed)
            self.state = "FLEX"
        elif s == "STOPPING" and self._arrived():
            self.state = "IDLE"
            self._say("EVENT STOPPED {}".format(self.rep))

    # --- commands from the app ----------------------------------------------
    def send(self, text):
        words = text.strip().upper().split()
        if not words:
            return
        cmd, arg = words[0], (words[1] if len(words) > 1 else None)
        limits = {"SPEED": (10, 90), "RANGE": (10, 100), "REPS": (1, 200),
                  "HOLD": (0, 10000), "REST": (300, 10000)}
        with self.lock:
            busy = self.state not in ("IDLE", "ESTOP")
            if cmd == "START":
                if self.state == "IDLE":
                    self.rep = 0
                    self._say("EVENT START md={} reps={} spd={} rng={} hold={} rest={}".format(
                        self.mode, self.reps, self.speed, self.range, self.hold, self.rest))
                    self._set_goals(True, self.speed)
                    self.state = "FLEX"
                elif self.state == "ESTOP":
                    self._rearm()
                else:
                    self._say("ERR BUSY already running")
            elif cmd == "STOP":
                if busy and self.state != "STOPPING":
                    self._set_goals(False, 60)
                    self.state = "STOPPING"
                self._say("OK STOP")
            elif cmd == "RESET":
                if self.state == "ESTOP":
                    self._rearm()
                else:
                    self._say("OK RESET nothing to reset")
            elif cmd == "STATUS":
                self._status()
            elif cmd == "PING":
                self._say("PONG")
            elif cmd == "SIM_POWER":          # simulator only: flip the E-stop switch
                self.power_on = (arg == "ON")
                self._say("INFO simulated motor power {}".format(arg))
            elif cmd == "MODE":
                if busy:
                    self._say("ERR BUSY settings can only change while stopped")
                elif arg in ("FULL", "FINGERS", "THUMB"):
                    self.mode = arg
                    self._say("OK MODE " + arg)
                else:
                    self._say("ERR BAD_MODE use FULL, FINGERS or THUMB")
            elif cmd in limits:
                if busy:
                    self._say("ERR BUSY settings can only change while stopped")
                elif arg is None or not arg.lstrip("-").isdigit():
                    self._say("ERR MISSING_VALUE e.g. SPEED 40")
                else:
                    lo, hi = limits[cmd]
                    value = max(lo, min(hi, int(arg)))
                    setattr(self, {"SPEED": "speed", "RANGE": "range", "REPS": "reps",
                                   "HOLD": "hold", "REST": "rest"}[cmd], value)
                    self._say("OK {} {}".format(cmd, value))
            else:
                self._say("ERR UNKNOWN_COMMAND type HELP")

    def _rearm(self):
        if not self.power_on:
            self._say("ERR NO_MOTOR_POWER switch the motor supply back on first")
            return
        self.pos, self.goal = dict(self.OPEN), dict(self.OPEN)
        self.state = "IDLE"
        self._say("EVENT REARMED 0")

    def close(self):
        self.running = False


# ----------------------------------------------------------------------------
#  The window
# ----------------------------------------------------------------------------
class GloveApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Robotic Glove Control Panel")
        self.minsize(860, 600)
        self.inbox = queue.Queue()
        self.link = None
        self.is_sim = False
        self.status = {}
        self.session = None          # dict while a test is running
        self.last_line_time = 0.0
        self.connect_time = 0.0
        self.got_ready = False
        self.sim_power_on = True
        self._build_ui()
        self.refresh_ports()
        self.after(50, self._poll)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- layout ----------------------------------------------------------------
    def _build_ui(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Start.TButton", font=("Segoe UI", 13, "bold"), foreground="white",
                        background="#2e8b57", padding=10)
        style.map("Start.TButton", background=[("active", "#257048"), ("disabled", "#9bbfab")])
        style.configure("Stop.TButton", font=("Segoe UI", 13, "bold"), foreground="white",
                        background="#c0392b", padding=10)
        style.map("Stop.TButton", background=[("active", "#9e2f23"), ("disabled", "#d9a19b")])
        style.configure("Big.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Value.TLabel", font=("Consolas", 12))

        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1, uniform="half")
        root.columnconfigure(1, weight=1, uniform="half")
        root.rowconfigure(3, weight=1)

        # Connection bar
        conn = ttk.LabelFrame(root, text="1. Connection", padding=8)
        conn.grid(row=0, column=0, columnspan=2, sticky="ew")
        conn.columnconfigure(1, weight=1)
        ttk.Label(conn, text="Port:").grid(row=0, column=0, padx=(0, 6))
        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(conn, textvariable=self.port_var, state="readonly", width=48)
        self.port_box.grid(row=0, column=1, sticky="ew")
        ttk.Button(conn, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=6)
        self.connect_btn = ttk.Button(conn, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=3)
        self.link_lbl = ttk.Label(conn, text="Not connected", foreground="#777777")
        self.link_lbl.grid(row=0, column=4, padx=(12, 0))

        # Controls
        ctrl = ttk.LabelFrame(root, text="2. Exercise settings", padding=8)
        ctrl.grid(row=1, column=0, sticky="nsew", pady=8, padx=(0, 4))
        ctrl.columnconfigure(1, weight=1)
        self.mode_var = tk.StringVar(value="FULL")
        ttk.Label(ctrl, text="Mode").grid(row=0, column=0, sticky="w")
        modes = ttk.Frame(ctrl)
        modes.grid(row=0, column=1, columnspan=2, sticky="w")
        for text, value in (("Full grasp", "FULL"), ("Fingers", "FINGERS"), ("Thumb", "THUMB")):
            ttk.Radiobutton(modes, text=text, value=value, variable=self.mode_var).pack(side="left", padx=(0, 8))

        self.speed_var = tk.IntVar(value=40)
        self.range_var = tk.IntVar(value=80)
        self._slider(ctrl, 1, "Speed (deg/s)", self.speed_var, 10, 90)
        self._slider(ctrl, 2, "Range of motion (%)", self.range_var, 10, 100)
        self.reps_var = tk.IntVar(value=10)
        self.hold_var = tk.IntVar(value=1000)
        self.rest_var = tk.IntVar(value=1000)
        self._spin(ctrl, 3, "Repetitions", self.reps_var, 1, 200, 1)
        self._spin(ctrl, 4, "Hold closed (ms)", self.hold_var, 0, 10000, 250)
        self._spin(ctrl, 5, "Rest open (ms)", self.rest_var, 300, 10000, 250)

        buttons = ttk.Frame(ctrl)
        buttons.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        self.start_btn = ttk.Button(buttons, text="START", style="Start.TButton", command=self.start)
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.stop_btn = ttk.Button(buttons, text="STOP", style="Stop.TButton", command=self.stop)
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.rearm_btn = ttk.Button(buttons, text="Re-arm after emergency stop", command=self.rearm)
        self.rearm_btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.sim_btn = ttk.Button(buttons, text="Simulator: flip E-stop switch", command=self.sim_toggle_power)

        # Live status
        stat = ttk.LabelFrame(root, text="3. Live status", padding=8)
        stat.grid(row=1, column=1, sticky="nsew", pady=8, padx=(4, 0))
        stat.columnconfigure(1, weight=1)
        self.state_lbl = ttk.Label(stat, text="-", style="Big.TLabel", foreground="#777777")
        self.state_lbl.grid(row=0, column=0, columnspan=2, sticky="w")
        self.rep_lbl = ttk.Label(stat, text="Repetition 0 / 0", font=("Segoe UI", 14))
        self.rep_lbl.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 2))
        self.progress = ttk.Progressbar(stat, maximum=100)
        self.progress.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.value_lbls = {}
        for row, (key, text) in enumerate((("md", "Mode"), ("f", "Finger servo (deg)"),
                                            ("t", "Thumb servo (deg)"), ("v", "Motor supply (V)"),
                                            ("cfg", "Arduino settings")), start=3):
            ttk.Label(stat, text=text).grid(row=row, column=0, sticky="nw", pady=1)
            lbl = ttk.Label(stat, text="-", style="Value.TLabel")
            lbl.grid(row=row, column=1, sticky="w", padx=(10, 0))
            self.value_lbls[key] = lbl

        # Test record
        rec = ttk.LabelFrame(root, text="4. Test record (saved to CSV when a session ends)", padding=8)
        rec.grid(row=2, column=0, columnspan=2, sticky="ew")
        rec.columnconfigure(5, weight=1)
        self.test_id_var = tk.StringVar(value="T01")
        self.tester_var = tk.StringVar()
        self.notes_var = tk.StringVar(value="artificial finger")
        ttk.Label(rec, text="Test ID").grid(row=0, column=0)
        ttk.Entry(rec, textvariable=self.test_id_var, width=8).grid(row=0, column=1, padx=(4, 12))
        ttk.Label(rec, text="Tester").grid(row=0, column=2)
        ttk.Entry(rec, textvariable=self.tester_var, width=14).grid(row=0, column=3, padx=(4, 12))
        ttk.Label(rec, text="Notes").grid(row=0, column=4)
        ttk.Entry(rec, textvariable=self.notes_var).grid(row=0, column=5, sticky="ew", padx=(4, 0))
        ttk.Label(rec, text="File: " + RESULTS_FILE, foreground="#777777").grid(
            row=1, column=0, columnspan=6, sticky="w", pady=(6, 0))

        # Log
        logf = ttk.LabelFrame(root, text="Messages", padding=4)
        logf.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        logf.rowconfigure(0, weight=1)
        logf.columnconfigure(0, weight=1)
        self.log_box = tk.Text(logf, height=8, font=("Consolas", 10), state="disabled", wrap="none")
        self.log_box.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(logf, command=self.log_box.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_box.configure(yscrollcommand=scroll.set)
        self._set_controls(False)

    def _slider(self, parent, row, text, var, lo, hi):
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Scale(parent, from_=lo, to=hi, variable=var, orient="horizontal",
                  command=lambda v: var.set(int(float(v)))).grid(row=row, column=1, sticky="ew", padx=6)
        ttk.Label(parent, textvariable=var, width=4).grid(row=row, column=2)

    def _spin(self, parent, row, text, var, lo, hi, inc):
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Spinbox(parent, from_=lo, to=hi, increment=inc, textvariable=var, width=8).grid(
            row=row, column=1, sticky="w", padx=6)

    # --- helpers ---------------------------------------------------------------
    def log(self, text):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", "{}  {}\n".format(stamp, text))
        if int(self.log_box.index("end-1c").split(".")[0]) > 500:
            self.log_box.delete("1.0", "100.0")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def send(self, text):
        if not self.link:
            self.log("Not connected.")
            return False
        try:
            self.link.send(text)
        except Exception as exc:
            self.log("Send failed: {}".format(exc))
            self.disconnect("send failed")
            return False
        self.log(">> " + text)
        return True

    def _set_controls(self, connected):
        for widget in (self.start_btn, self.stop_btn, self.rearm_btn):
            widget.state(["!disabled"] if connected else ["disabled"])

    def _number(self, var, lo, hi, default):
        try:
            return max(lo, min(hi, int(var.get())))
        except (tk.TclError, ValueError):
            return default

    # --- connection --------------------------------------------------------
    def refresh_ports(self):
        ports = []
        if serial is not None:
            for p in serial.tools.list_ports.comports():
                ports.append("{}  -  {}".format(p.device, p.description))
        ports.append(SIMULATOR)
        self.port_box["values"] = ports
        if not self.port_var.get() or self.port_var.get() not in ports:
            self.port_var.set(ports[0])
        if serial is None:
            self.log("pyserial is not installed: only the simulator is available. Run: pip install pyserial")

    def toggle_connection(self):
        if self.link:
            self.disconnect("you disconnected")
        else:
            self.connect()

    def connect(self):
        choice = self.port_var.get()
        try:
            if choice == SIMULATOR:
                self.link, self.is_sim = SimulatedGlove(self.inbox), True
                self.sim_power_on = True
                self.sim_btn.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
            else:
                port = choice.split()[0]
                self.link, self.is_sim = SerialLink(port, self.inbox), False
                self.log("Port {} open. The Arduino restarts now; wait about 2 seconds.".format(port))
        except Exception as exc:
            self.link = None
            self.log("Could not open the port: {}".format(exc))
            self.log("Check: right COM port? Serial Monitor closed? Cable is a data cable?")
            return
        self.connect_time = time.time()
        self.last_line_time = time.time()
        self.got_ready = False
        self.connect_btn.configure(text="Disconnect")
        self.link_lbl.configure(text="Connected" + (" (simulator)" if self.is_sim else ""), foreground="#2e8b57")
        self._set_controls(True)

    def disconnect(self, reason):
        if self.link:
            if self.status.get("st") not in (None, "IDLE", "ESTOP"):
                try:
                    self.link.send("STOP")       # never leave the glove running unattended
                except Exception:
                    pass
            self.link.close()
        self.link = None
        if self.session:
            self.finish_session("DISCONNECTED", self.session.get("reps_done", 0))
        self.sim_btn.grid_remove()
        self.connect_btn.configure(text="Connect")
        self.link_lbl.configure(text="Not connected", foreground="#777777")
        self.state_lbl.configure(text="-", foreground="#777777")
        self._set_controls(False)
        self.status = {}
        self.log("Disconnected ({}).".format(reason))

    # --- buttons -----------------------------------------------------------------
    def send_settings(self):
        values = [
            "MODE " + self.mode_var.get(),
            "SPEED {}".format(self._number(self.speed_var, 10, 90, 40)),
            "RANGE {}".format(self._number(self.range_var, 10, 100, 80)),
            "REPS {}".format(self._number(self.reps_var, 1, 200, 10)),
            "HOLD {}".format(self._number(self.hold_var, 0, 10000, 1000)),
            "REST {}".format(self._number(self.rest_var, 300, 10000, 1000)),
        ]
        for line in values:
            if not self.send(line):
                return False
        return True

    def start(self):
        if self.status.get("st") == "ESTOP":
            self.log("Emergency stop is active. Switch motor power back on, then press Re-arm.")
            return
        if self.send_settings():
            self.send("START")

    def stop(self):
        self.send("STOP")

    def rearm(self):
        self.send("RESET")

    def sim_toggle_power(self):
        self.sim_power_on = not self.sim_power_on
        self.send("SIM_POWER " + ("ON" if self.sim_power_on else "OFF"))

    # --- incoming messages ---------------------------------------------------------
    def _poll(self):
        try:
            for _ in range(200):
                kind, payload = self.inbox.get_nowait()
                if kind == "LINE":
                    self.handle_line(payload)
                elif kind == "LINK_LOST":
                    self.log("USB connection lost: {}".format(payload))
                    self.disconnect("cable unplugged?")
        except queue.Empty:
            pass
        if self.link:
            quiet = time.time() - self.last_line_time
            if quiet > 2.5:
                self.link_lbl.configure(text="No data from Arduino", foreground="#c0392b")
            if not self.got_ready and time.time() - self.connect_time > 5:
                self.got_ready = True      # warn only once
                self.log("No READY message yet. Is robotic_glove.ino uploaded? Baud must be 115200.")
        self.after(50, self._poll)

    def handle_line(self, line):
        self.last_line_time = time.time()
        words = line.split()
        head = words[0] if words else ""
        if head == "STATUS":
            if self.link:
                self.link_lbl.configure(text="Connected" + (" (simulator)" if self.is_sim else ""),
                                        foreground="#2e8b57")
            self.update_status(parse_fields(words[1:]))
            return
        self.log("<< " + line)
        if head == "READY":
            self.got_ready = True
            self.send("STATUS")
        elif head == "EVENT" and len(words) >= 2:
            self.handle_event(words[1], words[2:])

    def handle_event(self, name, rest):
        count = int(rest[0]) if rest and rest[0].isdigit() else 0
        if name == "START":
            self.start_session(parse_fields(rest))
        elif name == "REP" and self.session:
            self.session["reps_done"] = count
        elif name == "DONE":
            self.finish_session("COMPLETED", count)
        elif name == "STOPPED":
            self.finish_session("STOPPED", count)
        elif name == "ESTOP":
            self.finish_session("E-STOP", count)
            self.log("EMERGENCY STOP: motor power is off. Check the glove, then switch power on and press Re-arm.")
        elif name == "MODE" and rest:
            self.mode_var.set(rest[0])

    def update_status(self, s):
        self.status = s
        state = s.get("st", "?")
        text, colour = STATE_TEXT.get(state, (state, "#777777"))
        self.state_lbl.configure(text=text, foreground=colour)
        try:
            rep, reps = int(s.get("rep", 0)), int(s.get("reps", 0))
        except ValueError:
            rep, reps = 0, 0
        self.rep_lbl.configure(text="Repetition {} / {}".format(rep, reps))
        self.progress["value"] = 100.0 * rep / reps if reps else 0
        self.value_lbls["md"].configure(text=s.get("md", "-"))
        self.value_lbls["f"].configure(text=s.get("f", "-"))
        self.value_lbls["t"].configure(text=s.get("t", "-"))
        self.value_lbls["v"].configure(text=s.get("v", "-"))
        self.value_lbls["cfg"].configure(text="{} deg/s, {} %\nhold {} / rest {} ms".format(
            s.get("spd", "?"), s.get("rng", "?"), s.get("hold", "?"), s.get("rest", "?")))
        if self.session:
            try:
                volts = float(s.get("v", "nan"))
                if volts == volts:                     # not NaN
                    self.session["min_v"] = min(self.session["min_v"], volts)
            except ValueError:
                pass

    # --- CSV results ---------------------------------------------------------------
    def start_session(self, cfg):
        now = datetime.now()
        self.session = {
            "test_id": self.test_id_var.get().strip() or "T?",
            "tester": self.tester_var.get().strip(),
            "notes": self.notes_var.get().strip(),
            "start": now,
            "mode": cfg.get("md", self.mode_var.get()),
            "speed": cfg.get("spd", ""), "range": cfg.get("rng", ""),
            "hold": cfg.get("hold", ""), "rest": cfg.get("rest", ""),
            "reps_target": cfg.get("reps", ""),
            "reps_done": 0,
            "min_v": float("inf"),
        }

    def finish_session(self, result, reps_done):
        if not self.session:
            return
        s, end = self.session, datetime.now()
        self.session = None
        row = {
            "test_id": s["test_id"], "tester": s["tester"],
            "date": s["start"].strftime("%Y-%m-%d"),
            "start_time": s["start"].strftime("%H:%M:%S"),
            "end_time": end.strftime("%H:%M:%S"),
            "duration_s": round((end - s["start"]).total_seconds(), 1),
            "mode": s["mode"], "speed_deg_s": s["speed"], "range_pct": s["range"],
            "hold_ms": s["hold"], "rest_ms": s["rest"],
            "reps_target": s["reps_target"], "reps_completed": max(reps_done, s["reps_done"]),
            "result": result,
            "min_motor_v": "" if s["min_v"] == float("inf") else "{:.2f}".format(s["min_v"]),
            "notes": s["notes"],
        }
        path = self.save_row(row)
        if path:
            self.log("Saved {} ({}, {} reps) to {}".format(row["test_id"], result, row["reps_completed"], path))
            self.test_id_var.set(self.next_id(row["test_id"]))

    def save_row(self, row):
        for path in (RESULTS_FILE, RESULTS_FILE.replace(".csv", datetime.now().strftime("_%H%M%S.csv"))):
            try:
                is_new = not os.path.exists(path) or os.path.getsize(path) == 0
                with open(path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                    if is_new:
                        writer.writeheader()
                    writer.writerow(row)
                if path != RESULTS_FILE:
                    self.log("glove_results.csv was locked (open in Excel?), saved a separate file instead.")
                return path
            except OSError as exc:
                self.log("Could not write {}: {}".format(path, exc))
        return None

    @staticmethod
    def next_id(test_id):
        """T07 -> T08, Run9 -> Run10, anything else unchanged."""
        digits = ""
        while test_id and test_id[-1].isdigit():
            digits, test_id = test_id[-1] + digits, test_id[:-1]
        if not digits:
            return test_id
        return "{}{:0{}d}".format(test_id, int(digits) + 1, len(digits))

    def on_close(self):
        self.disconnect("window closed")
        self.destroy()


if __name__ == "__main__":
    GloveApp().mainloop()
