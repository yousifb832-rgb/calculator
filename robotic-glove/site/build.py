#!/usr/bin/env python3
"""Builds the Robotic Glove Build Guide.

Reads template.html, injects the real source files (so the page always shows
exactly the code in firmware/ and pc_app/), generates the stage cards, the
schedule and the budget table, then writes:
  ../index.html                 beginner guide, standalone (open it in any browser)
  ../reference.html             technical reference, standalone
  ../robotic-glove-project.zip  firmware + PC app + README
  <out_dir>/index.html          beginner guide fragment for the Claude artifact (optional arg)
  <out_dir>/reference.html      technical reference page published beside it
"""
import base64
import html
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- stages
STAGES = [
    ("Build and test one artificial finger", "both", "Weeks 1–2",
     ["Wooden 20 × 20 mm stick, 3 mini hinges, screw eyes", "Braided line, elastic cord, SG90 + drum",
      "Arduino and the Stage 1 circuit", "Luggage scale, protractor, multimeter"],
     ["Follow the <a href=\"#stage1\">Stage 1 chapter</a>: build steps 1–9, wire, measure force and travel by hand.",
      "Calibrate OPEN and CLOSED, fix the stopper bead, run at low speed.",
      "Run 100 cycles and record them.", "Decide the four-finger motor with the calculator."],
     "A finger that bends at least 60° at MCP and PIP and returns straight every cycle, plus a force–travel table, calibrated angles and a written motor decision.",
     ["Servo powered from the Arduino 5V pin", "No common ground", "Tendon eyes out of line", "Elastic far too strong", "Measurements not written down"]),
    ("Design the tendon mechanism", "s1", "Week 3",
     ["Chosen four-finger servo (MG996R if the calculator says so)", "Two drums, PTFE tube 1 m, snap swivels",
      "Tendon bar: plastic strip, 4 × M3 screws and washers", "Stop blocks, wooden base"],
     ["Build the actuator pack (<a href=\"#mechanical\">A8</a>).",
      "Drive the Stage 1 finger through a 40 cm sheath with one 90° bend.",
      "Repeat the force test with and without the sheath: the difference is your friction loss.",
      "Clamp four test lines of different lengths on the tendon bar and adjust until they tighten together.",
      "Set the travel-stop gaps; test the quick-release under load."],
     "The finger moves through the sheath, friction loss is measured (if it is above about 30 %, shorten the sheath or open its bends), the bar adjusts every tendon, and the release works in under 3 s.",
     ["Sheath ends not pressed against washers, so the sheath moves instead of the tendon", "Bends tighter than 5 cm radius",
      "Drum without flanges", "Stops set so tight they act during normal motion"]),
    ("Build the complete glove", "s1", "Weeks 3–5",
     ["Snug glove, fabric for caps, PTFE or refill tubes", "Strong thread, Velcro, 2 mm plastic sheet, foam, washers",
      "Flat elastic and buckles", "Wood and 11 hinges for the artificial hand"],
     ["Build the artificial hand (<a href=\"#mechanical\">A9</a>).", "Mark the glove while it is on the hand.",
      "Sew caps, guides, palm plate and elastics (<a href=\"#mechanical\">A7</a>).", "Tie the tendons and route the sheaths.",
      "Pull each tendon by hand through the luggage scale; record the force for full flexion of each finger with the glove on."],
     "The glove on the artificial hand: pulling a tendon by hand curls its finger smoothly, the elastics straighten it, and you have a measured force per finger to check the motor choice again.",
     ["Guides sewn over joint creases", "Weak stitching at the caps: they tear out", "Glove too loose", "Elastic too tight", "Tendons crossing in the palm"]),
    ("Install the servo motors", "s1", "Week 5",
     ["Actuator pack from Stage 2, thumb servo", "Cable ties, cover box, screws"],
     ["Mount both servos and drums.", "Seat the glove's sheaths in the sheath stop.",
      "Clamp the four finger tendons at the bar with the servo at 90° and the tendons just slack.",
      "Fit the cover and strain relief.", "Fix the pack to the table 30 to 50 cm from the hand."],
     "A rigid pack with seated sheaths. With the servos unpowered, pulling a tendon moves only the drum, and nothing rubs.",
     ["Pack not fixed down, so it slides toward the hand", "Loose servo screws", "Sheaths too long, forming loops"]),
    ("Connect the Arduino and electronics", "s2", "Weeks 3–4",
     ["Nano, breadboard, 5 V adapter, jack adapter", "Fuse, E-stop, 1000 µF, 2 × 330 Ω, 2 × 10 kΩ",
      "3 buttons, wires, multimeter", "Small plastic control box"],
     ["Build Figure 6 in the order given in <a href=\"#electronics\">chapter B</a>.",
      "Multimeter checks before power; power-on checks after.",
      "Move the buttons and E-stop into the control box lid."],
     "Rail 4.8 to 5.3 V with the E-stop released and 0 V when pressed, about 2.5 V at A0, and STATUS shows each button working.",
     ["Capacitor reversed", "E-stop placed in the ground line instead of +", "Servos fed from the 5V pin", "No common ground", "Loose breadboard contacts"]),
    ("Write and test the Arduino program", "s2", "Weeks 4–6",
     ["PC with Arduino IDE", "servo_calibration.ino and robotic_glove.ino", "Assembled glove, pack and electronics"],
     ["Calibrate both servos with the glove on the artificial hand (D9, then D10).",
      "Enter the angles; set USE_MOTOR_SENSE to true.",
      "Run the test list in <a href=\"#firmware\">chapter C</a> with the tendons unhooked.",
      "Hook the tendons; run FINGERS, THUMB and FULL at SPEED 20, RANGE 50, then step up.",
      "Fine-tune the tendon bar so all fingers close together."],
     "Every mode runs, every limit is proven, and STOP, E-stop and re-arm behave exactly as specified.",
     ["Calibrating without the glove on (the angles change)", "Jumping straight to RANGE 100", "Editing the code without repeating the limit tests"]),
    ("Develop the PC application", "s2", "Weeks 2–6",
     ["Python 3.10+, pyserial", "glove_control.py"],
     ["Run it on the simulator and read through each part of the code.", "Connect to the real Arduino.",
      "Run sessions, open the CSV in Excel and make one chart.", "Optional: add one feature, such as a live plot."],
     "Full control from the PC, a correct live display, and one CSV row per session with the right result.",
     ["Serial Monitor left open", "Wrong COM port", "CSV open in Excel during a test", "Changing the protocol on one side only"]),
    ("Integrate all components", "both", "Week 7",
     ["Everything built so far"],
     ["Lay out the demo bench: hand on its stand, pack, control box, laptop.",
      "Integration checklist: cable lengths, labels, strain relief.",
      "Full runs from the buttons alone (no PC), then from the PC.", "A 50-cycle run in each mode."],
     "The system runs both standalone and from the PC, and every session is logged.",
     ["Cables that pull on the glove", "Testing alone", "Changing several things at once"]),
    ("Mechanical and electrical testing", "both", "Weeks 8–9",
     ["Test plan in chapter G", "Phone camera, thermometer, multimeter, luggage scale"],
     ["Run every test in <a href=\"#testing\">chapter G</a>.", "Record results in the CSV and the logbook.",
      "Fix and re-test anything that fails.", "Make charts for the report."],
     "A results table with pass or fail for every test, and charts ready for the report.",
     ["Testing each thing only once", "Not recording failures", "Changing the design without re-testing"]),
    ("Prepare the final demonstration", "both", "Weeks 9–10",
     ["Report, slides, backup kit", "A recorded video of a good run"],
     ["Follow the <a href=\"#demo\">demo-day script</a>.", "Rehearse three times with a timer.",
      "Record the backup video.", "Practise the examiner questions."],
     "A seven-minute demonstration that works first time, with a backup for every part.",
     ["First full rehearsal on the day", "Untested last-minute changes", "Medical claims in the talk"]),
]
OWNER = {"s1": ("s1", "Student 1"), "s2": ("s2", "Student 2"), "both": ("both", "Both")}
GANTT = [(1, 2, "both"), (3, 3, "s1"), (3, 5, "s1"), (5, 5, "s1"), (3, 4, "s2"),
         (4, 6, "s2"), (2, 6, "s2"), (7, 7, "both"), (8, 9, "both"), (9, 10, "both")]
SHORT = ["Artificial finger", "Tendon mechanism", "Glove + artificial hand", "Install servos", "Electronics",
         "Arduino program", "PC application", "Integration", "Testing", "Demo preparation"]


def stages_html():
    out = []
    for i, (title, owner, weeks, mats, steps, expected, mistakes) in enumerate(STAGES, 1):
        cls, name = OWNER[owner]
        out.append(
            '<article class="stage" id="stage-{i}">\n'
            '  <div class="stage-head"><span class="stage-num">STAGE {i:02d}</span><h3>{title}</h3>'
            '<span class="stage-meta"><span class="chip {cls}">{name}</span><span class="chip">{weeks}</span></span></div>\n'
            '  <div class="stage-grid">\n'
            '    <div><h4>Materials</h4><ul>{mats}</ul></div>\n'
            '    <div><h4>Procedure</h4><ol>{steps}</ol></div>\n'
            '    <div><h4>Expected result</h4><p>{exp}</p></div>\n'
            '    <div><h4>Common mistakes</h4><ul>{mis}</ul></div>\n'
            '  </div>\n</article>'.format(
                i=i, title=title, cls=cls, name=name, weeks=weeks,
                mats="".join("<li>%s</li>" % m for m in mats),
                steps="".join("<li>%s</li>" % s for s in steps),
                exp=expected, mis="".join("<li>%s</li>" % m for m in mistakes)))
    return "\n".join(out)


def gantt_html():
    rows = []
    for i, ((a, b, who), label) in enumerate(zip(GANTT, SHORT), 1):
        cells = ['<div class="gl">%d · %s</div>' % (i, label)]
        for w in range(1, 11):
            cells.append('<div class="c %s"><i></i></div>' % who if a <= w <= b else '<div class="c"></div>')
        rows.append("".join(cells))
    return "\n      ".join(rows)


# ---------------------------------------------------------------- budget
# id, name, note, category, qty, stage-1 qty, low, high, default unit price
BUDGET = [
    ("e1", "Arduino Nano (CH340 clone) + USB cable", "Check the cable carries data, not only charge.", "ess", 1, 1, 8000, 12000, 10000),
    ("e2", "SG90 micro servo", "Stage 1 finger; later the thumb servo and a spare.", "ess", 2, 1, 2500, 4000, 3000),
    ("e3", "MG996R metal-gear servo", "Buy only after the sizing calculator says so.", "ess", 1, 0, 10000, 15000, 12500),
    ("e4", "Regulated 5 V adapter, 3 A or more", "5 A preferred with MG996R. Never 9 V or 12 V.", "ess", 1, 1, 5000, 8000, 6500),
    ("e5", "Barrel jack to screw-terminal adapter", "", "ess", 1, 1, 500, 1000, 750),
    ("e6", "Breadboard + jumper wires (M-M, M-F)", "", "ess", 1, 1, 4000, 7000, 5000),
    ("e7", "Push buttons 12 mm", "START, STOP, MODE.", "ess", 3, 0, 250, 500, 350),
    ("e8", "Emergency stop: 22 mm latching mushroom (NC) or 5 A rocker", "Electrical-panel shops.", "ess", 1, 1, 1000, 6000, 3000),
    ("e9", "Inline fuse holder + T3A/T4A fuses", "", "ess", 1, 0, 1000, 2000, 1500),
    ("e10", "Capacitor 1000 µF 16 V", "", "ess", 2, 1, 250, 500, 350),
    ("e11", "Resistors: 330 Ω ×2, 10 kΩ ×2", "", "ess", 4, 2, 50, 100, 75),
    ("e12", "Snug cotton or knit work glove", "One to build, one spare.", "ess", 2, 0, 1500, 4000, 2500),
    ("e13", "Braided PE fishing line 0.2–0.3 mm (30–50 lb)", "Fishing-tackle shops; 0.5 mm mono as a fallback.", "ess", 1, 1, 3000, 8000, 5000),
    ("e14", "PTFE tube 2 mm ID × 4 mm OD, per metre", "3D-printer shops; bicycle brake housing also works.", "ess", 2, 0, 1500, 4000, 2500),
    ("e15", "Flat elastic 8–10 mm + 2 mm elastic cord", "Tailoring supplies.", "ess", 1, 1, 1000, 2000, 1500),
    ("e16", "Sew-on Velcro + strap, per metre", "", "ess", 1, 0, 1000, 3000, 2000),
    ("e17", "Wood: 20 × 20 mm stick (1 m) + 9–12 mm board", "Carpentry offcuts are fine.", "ess", 1, 1, 2000, 5000, 3500),
    ("e18", "Mini hinges 20–25 mm with screws", "3 for Stage 1; 14 for the whole artificial hand.", "ess", 14, 3, 250, 500, 350),
    ("e19", "Small screw eyes, pack of about 20", "", "ess", 1, 1, 1000, 2000, 1500),
    ("e20", "Drum parts: bottle caps or spools, epoxy or superglue", "", "ess", 1, 1, 1500, 3000, 2000),
    ("e21", "M3 screws, nuts, washers, small wood screws", "", "ess", 1, 1, 1000, 2500, 1500),
    ("e22", "Fishing snap swivels (quick-release)", "", "ess", 4, 0, 250, 500, 350),
    ("e23", "Strong nylon thread, needles, fabric glue", "", "ess", 1, 0, 1000, 2500, 1500),
    ("e24", "Hot glue, tape, zip ties, heat-shrink", "", "ess", 1, 1, 1500, 3000, 2000),
    ("t1", "Digital luggage scale 0–50 kg, 10 g steps", "Essential for measuring; borrow one if you can.", "test", 1, 1, 5000, 8000, 6500),
    ("t2", "Multimeter (DT-830 class)", "Usually available in the university lab.", "test", 1, 1, 5000, 8000, 6000),
    ("o1", "MG90S for the thumb instead of SG90", "Metal gears, same size.", "opt", 1, 0, 5000, 7000, 6000),
    ("o2", "Plastic project box for electronics", "", "opt", 1, 0, 3000, 6000, 4500),
    ("o3", "Green and red LEDs with 220 Ω resistors", "", "opt", 1, 0, 500, 1000, 750),
    ("o4", "Spiral cable wrap, 1 m", "", "opt", 1, 0, 1000, 2000, 1500),
    ("o5", "3D-printed drums, thimbles and guides (material)", "If the university has a printer.", "opt", 1, 0, 2000, 5000, 3500),
    ("o6", "Small buzzer", "", "opt", 1, 0, 500, 1000, 750),
]
CAT_TITLES = {"ess": "Essential for prototype v1", "test": "Test equipment: borrow first",
              "opt": "Optional improvements"}


def budget_rows():
    rows, last = [], None
    for (bid, name, note, cat, qty, s1, lo, hi, d) in BUDGET:
        if cat != last:
            rows.append('<tr class="cat"><td colspan="6">%s</td></tr>' % CAT_TITLES[cat])
            last = cat
        on = cat == "ess"
        rows.append(
            '<tr data-id="{id}"{off}><td><input type="checkbox" id="b-{id}-on" aria-label="Include {aname}"{chk}></td>'
            '<td class="item">{name}{note}</td>'
            '<td class="r"><input type="number" class="qty" id="b-{id}-qty" min="0" step="1" value="{qty}" aria-label="Quantity"></td>'
            '<td class="r"><input type="number" class="price" id="b-{id}-price" min="0" step="250" value="{d}" aria-label="Unit price in IQD"></td>'
            '<td class="r">{lo} – {hi}</td><td class="r line">{line}</td></tr>'.format(
                id=bid, off="" if on else ' class="off"', aname=html.escape(name), chk=" checked" if on else "",
                name=html.escape(name), note=("<small>%s</small>" % html.escape(note)) if note else "",
                qty=qty, d=d, lo="{:,}".format(lo), hi="{:,}".format(hi), line="{:,}".format(qty * d)))
    return "\n".join(rows)


def budget_json():
    data = [{"id": b, "cat": c, "qty": q, "s1": s1, "def": d} for (b, _n, _no, c, q, s1, _lo, _hi, d) in BUDGET]
    return json.dumps(data).replace("<", "\\u003c")


def totals():
    full = sum(q * d for (_b, _n, _no, c, q, _s, _l, _h, d) in BUDGET if c == "ess")
    s1 = sum(s * d for (_b, _n, _no, c, _q, s, _l, _h, d) in BUDGET if c == "ess")
    return full, s1


# ---------------------------------------------------------------- build
README = """# Low-Cost Robotic Assistance Glove: code

Education and research prototype. Not a medical device. Test on the artificial finger and artificial hand only.

firmware/servo_calibration/servo_calibration.ino  Stage 1 tool: move one servo slowly to typed angles
firmware/robotic_glove/robotic_glove.ino          Full program: 2 servos, buttons, E-stop sense, USB protocol
pc_app/glove_control.py                           PC control panel (Python 3.8+, Tkinter, pyserial)

Arduino: open each .ino in Arduino IDE 2, board "Arduino Nano", processor ATmega328P
(use "Old Bootloader" if upload fails). Set your calibration angles in section 2 first.

PC app:  pip install pyserial   then   python glove_control.py
Choose "SIMULATOR (no hardware)" to try it without the Arduino.

The beginner guide is index.html and the technical reference is reference.html in this folder.
"""


SHOP = [
    ("Arduino Nano + USB cable", "أردوينو نانو مع كيبل USB", 10000),
    ("SG90 servo motor", "محرك سيرفو SG90", 3000),
    ("5 V 3 A adapter + jack connector", "أدابتر 5 فولت 3 أمبير مع مأخذ", 7250),
    ("Breadboard + jumper wires", "بريدبورد وأسلاك توصيل", 5000),
    ("ON/OFF switch or red emergency button", "سويج أو زر طوارئ أحمر", 3000),
    ("1000 µF capacitor + 330 Ω resistor", "متسعة 1000 مايكرو فاراد ومقاومة 330 أوم", 500),
    ("Braided fishing line 0.25 mm", "خيط صيد مضفور 0.25 ملم", 5000),
    ("Thin elastic cord 2 mm", "لاستيك رفيع 2 ملم", 1500),
    ("Square wood stick 20 × 20 mm + small board", "عود خشب مربع 2×2 سم ولوح صغير", 3500),
    ("3 small hinges", "3 مفصلات صغيرة", 1050),
    ("Small screw eyes (one pack)", "براغي حلقية صغيرة", 1500),
    ("Bottle cap + strong glue", "غطاء قنينة وغراء قوي", 2000),
    ("Small screws and washers", "براغي صغيرة وحلقات معدنية", 1500),
    ("Hot glue, tape, cable ties", "شمع حراري وشريط لاصق وأربطة", 2000),
]


def shop_rows():
    rows = []
    for i, (en, ar, price) in enumerate(SHOP, 1):
        rows.append('<li><label><input type="checkbox" id="shop-{i}" data-k="shop{i}" data-price="{p}">'
                    '<span class="it"><b>{en}</b><span class="ar" lang="ar">{ar}</span></span>'
                    '<span class="pr">≈ {pf}</span></label></li>'.format(
                        i=i, p=price, en=html.escape(en), ar=ar, pf="{:,}".format(price)))
    return "\n    ".join(rows)


def test_board_svg(tpl):
    start = tpl.index('<svg viewBox="0 0 900 320"')
    end = tpl.index("</svg>", start) + len("</svg>")
    return tpl[start:end]


def standalone(page):
    head, body = page.split("<!--BODY-->", 1)
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
            + head + "\n</head>\n<body>\n" + body + "\n</body>\n</html>\n")


def fill_common(text, shot):
    readme = json.dumps(README).replace("<", "\\u003c")
    return (text
            .replace("{{CAL_CODE}}", html.escape(read("firmware/servo_calibration/servo_calibration.ino"), quote=False))
            .replace("{{FW_CODE}}", html.escape(read("firmware/robotic_glove/robotic_glove.ino"), quote=False))
            .replace("{{PY_CODE}}", html.escape(read("pc_app/glove_control.py"), quote=False))
            .replace("{{APP_SHOT}}", "data:image/png;base64," + shot)
            .replace("{{README_JSON}}", readme))


def main():
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    beg = open(os.path.join(HERE, "beginner.html"), encoding="utf-8").read()
    shot = base64.b64encode(open(os.path.join(HERE, "app_screenshot.png"), "rb").read()).decode()
    full, s1 = totals()
    assert s1 == sum(p for (_e, _a, p) in SHOP), "shopping list and budget disagree"

    reference = (fill_common(tpl, shot)
                 .replace("{{STAGES}}", stages_html())
                 .replace("{{GANTT}}", gantt_html())
                 .replace("{{BUDGET_ROWS}}", budget_rows())
                 .replace("{{BUDGET_JSON}}", budget_json()))
    beginner = (fill_common(beg, shot)
                .replace("{{TEST_BOARD_SVG}}", test_board_svg(tpl))
                .replace("{{SHOP_ROWS}}", shop_rows()))
    for name, page in (("reference", reference), ("beginner", beginner)):
        assert "{{" not in page, "unfilled placeholder in " + name
    print("budget: full v1 = {:,} IQD, stage 1 = {:,} IQD".format(full, s1))

    # zip with the code
    zpath = os.path.join(ROOT, "robotic-glove-project.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in ("firmware/servo_calibration/servo_calibration.ino",
                    "firmware/robotic_glove/robotic_glove.ino",
                    "pc_app/glove_control.py", "pc_app/requirements.txt"):
            z.write(os.path.join(ROOT, rel), "robotic-glove/" + rel)
        z.writestr("robotic-glove/README.txt", README)

    # standalone pages for the repository / GitHub Pages
    for fname, page in (("index.html", beginner), ("reference.html", reference)):
        with open(os.path.join(ROOT, fname), "w", encoding="utf-8") as f:
            f.write(standalone(page))

    if len(sys.argv) > 1:
        out = sys.argv[1]
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
            f.write(beginner.replace("<!--BODY-->", ""))
        with open(os.path.join(out, "reference.html"), "w", encoding="utf-8") as f:
            f.write(standalone(reference))
    print("beginner page {:,} bytes, reference page {:,} bytes".format(len(beginner.encode()), len(reference.encode())))


if __name__ == "__main__":
    main()
