#!/usr/bin/env python3
"""
Generate docs/erp-integration.pdf — proper flowcharts and swim lane diagram.
Run: python3 scripts/generate-erp-pdf.py
Requires: pip install reportlab
"""

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "erp-integration.pdf")

# ── Page sizes ────────────────────────────────────────────────────────────────
W_P, H_P = A4               # portrait  210 × 297 mm
W_L, H_L = landscape(A4)   # landscape 297 × 210 mm

# ── Colour palette ────────────────────────────────────────────────────────────
CF  = colors.HexColor("#2E7D32")   # factory  green
CD  = colors.HexColor("#1565C0")   # device   blue
CA  = colors.HexColor("#E65100")   # AWS      orange
CLA = colors.HexColor("#B71C1C")   # Lambda   red
CDB = colors.HexColor("#00695C")   # DynamoDB teal
CE  = colors.HexColor("#6A1B9A")   # ERP      purple
CH  = colors.HexColor("#1A237E")   # header   dark blue
CBG = colors.HexColor("#F5F5F5")   # light bg
CBR = colors.HexColor("#BDBDBD")   # border
CAR = colors.HexColor("#424242")   # arrow
CW  = colors.white
CYN = colors.HexColor("#2E7D32")   # yes label green
CNO = colors.HexColor("#C62828")   # no  label red
CTX = colors.HexColor("#212121")   # body text


# ═══════════════════════════════════════════════════════════════════════════════
# Drawing primitives  (all coords in mm, converted internally)
# y = distance from page TOP (decreases downward — easier to reason about)
# ═══════════════════════════════════════════════════════════════════════════════

def _y(page_h_mm, y_mm):
    """Convert top-relative y (mm) to ReportLab bottom-relative pt."""
    return (page_h_mm - y_mm) * mm


def proc_box(c, ph, x, y, w, h, text, bg, fg=None, size=7.5, bold=False):
    """Rounded process rectangle. x,y = top-left in mm."""
    fg = fg or CW
    c.setFillColor(bg)
    c.setStrokeColor(CBR)
    c.setLineWidth(0.6)
    c.roundRect(x*mm, _y(ph/mm, y+h), w*mm, h*mm, 3, fill=1, stroke=1)
    c.setFillColor(fg)
    fn = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(fn, size)
    lines = text.split('\n')
    lh = size + 1.8
    cy_pt = _y(ph/mm, y + h/2) + (len(lines)-1)*lh/2
    for i, ln in enumerate(lines):
        c.drawCentredString((x + w/2)*mm, cy_pt - i*lh, ln)


def decision(c, ph, x, y, w, h, text, bg, fg=None, size=7.5):
    """Diamond. x,y = top-left of bounding box in mm."""
    fg = fg or CW
    cx = (x + w/2)*mm
    top = _y(ph/mm, y)
    bot = _y(ph/mm, y + h)
    mid_y = (top + bot) / 2
    hw = w*mm/2
    p = c.beginPath()
    p.moveTo(cx,      top)       # top vertex
    p.lineTo(cx + hw, mid_y)     # right vertex
    p.lineTo(cx,      bot)       # bottom vertex
    p.lineTo(cx - hw, mid_y)     # left vertex
    p.close()
    c.setFillColor(bg)
    c.setStrokeColor(CBR)
    c.setLineWidth(0.6)
    c.drawPath(p, fill=1, stroke=1)
    c.setFillColor(fg)
    c.setFont("Helvetica-Bold", size)
    lines = text.split('\n')
    lh = size + 1.8
    ty = mid_y + (len(lines)-1)*lh/2
    for i, ln in enumerate(lines):
        c.drawCentredString(cx, ty - i*lh, ln)


def terminal(c, ph, x, y, w, h, text, bg, fg=None, size=8):
    """Rounded pill (start / end terminal). x,y = top-left in mm."""
    fg = fg or CW
    c.setFillColor(bg)
    c.setStrokeColor(CBR)
    c.setLineWidth(0.8)
    r = h*mm/2  # full rounding → pill
    c.roundRect(x*mm, _y(ph/mm, y+h), w*mm, h*mm, r, fill=1, stroke=1)
    c.setFillColor(fg)
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString((x + w/2)*mm, _y(ph/mm, y+h) + h*mm/2 - size/2, text)


def _tri(c, pts):
    """Fill a triangle given 6 floats [x0,y0, x1,y1, x2,y2] (points)."""
    p = c.beginPath()
    p.moveTo(pts[0], pts[1])
    p.lineTo(pts[2], pts[3])
    p.lineTo(pts[4], pts[5])
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def arr_down(c, ph, cx, y_top, length, label="", lcolor=None):
    """Downward arrow. cx, y_top in mm."""
    lcolor = lcolor or CTX
    x_pt = cx*mm
    y1   = _y(ph/mm, y_top)
    y2   = _y(ph/mm, y_top + length)
    c.setStrokeColor(CAR); c.setFillColor(CAR); c.setLineWidth(0.9)
    c.line(x_pt, y1, x_pt, y2 + 3)
    _tri(c, [x_pt-3, y2+3, x_pt+3, y2+3, x_pt, y2])
    if label:
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(lcolor)
        c.drawString(x_pt + 2*mm, (y1+y2)/2, label)


def arr_right(c, ph, x_left, cy, length, label="", lcolor=None):
    """Rightward arrow. x_left, cy in mm."""
    lcolor = lcolor or CTX
    y_pt = _y(ph/mm, cy)
    x1   = x_left*mm
    x2   = (x_left + length)*mm
    c.setStrokeColor(CAR); c.setFillColor(CAR); c.setLineWidth(0.9)
    c.line(x1, y_pt, x2 - 3, y_pt)
    _tri(c, [x2-3, y_pt+3, x2-3, y_pt-3, x2, y_pt])
    if label:
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(lcolor)
        c.drawCentredString((x1+x2)/2, y_pt + 2*mm, label)


def arr_left(c, ph, x_right, cy, length, label="", lcolor=None):
    """Leftward arrow."""
    lcolor = lcolor or CTX
    y_pt = _y(ph/mm, cy)
    x1   = x_right*mm
    x2   = (x_right - length)*mm
    c.setStrokeColor(CAR); c.setFillColor(CAR); c.setLineWidth(0.9)
    c.line(x1, y_pt, x2 + 3, y_pt)
    _tri(c, [x2+3, y_pt+3, x2+3, y_pt-3, x2, y_pt])
    if label:
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(lcolor)
        c.drawCentredString((x1+x2)/2, y_pt + 2*mm, label)


def arr_elbow(c, ph, x1, y1, x2, y2, label=""):
    """L-shaped arrow: right from (x1,y1) then down to (x2,y2). All mm."""
    c.setStrokeColor(CAR); c.setFillColor(CAR); c.setLineWidth(0.9)
    c.line(x1*mm, _y(ph/mm, y1), x2*mm, _y(ph/mm, y1))
    y2_pt = _y(ph/mm, y2)
    c.line(x2*mm, _y(ph/mm, y1), x2*mm, y2_pt + 3)
    _tri(c, [x2*mm-3, y2_pt+3, x2*mm+3, y2_pt+3, x2*mm, y2_pt])
    if label:
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(CTX)
        c.drawString((x1 + (x2-x1)*0.5)*mm, _y(ph/mm, y1) + 2*mm, label)


def note_label(c, ph, x, y, text, size=6.5, color=None):
    color = color or CTX
    c.setFillColor(color)
    c.setFont("Helvetica-Oblique", size)
    c.drawString(x*mm, _y(ph/mm, y)*1 - size/2, text)


def section_line(c, ph, y, label="", color=None):
    color = color or CBR
    c.setStrokeColor(color); c.setLineWidth(0.4)
    c.line(10*mm, _y(ph/mm, y), (ph/mm - 10)*mm, _y(ph/mm, y))


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1  — Title + Phase 1 & 2 overview (portrait)
# ═══════════════════════════════════════════════════════════════════════════════

def page_title(c):
    ph = H_P; pw = W_P

    # header banner
    c.setFillColor(CH)
    c.rect(0, ph - 40*mm, pw, 40*mm, fill=1, stroke=0)
    c.setFillColor(CW)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(pw/2, ph - 18*mm, "ESP32-P4 IoT Fleet")
    c.setFont("Helvetica", 11)
    c.drawCentredString(pw/2, ph - 28*mm, "End-to-End Workflow: Manufacturing → AWS IoT Core → ERP")
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(pw/2, ph - 36*mm, "1000-device Fleet Provisioning with claim certificates")

    # legend row
    y = 50
    items = [
        (CF,  "Factory"),
        (CD,  "ESP32 Device"),
        (CA,  "AWS IoT Core"),
        (CLA, "Lambda"),
        (CDB, "DynamoDB"),
        (CE,  "ERP"),
    ]
    lw = (W_P/mm - 20) / len(items)
    for i, (col, lbl) in enumerate(items):
        lx = 10 + i * lw
        proc_box(c, ph, lx, y, lw - 1, 8, lbl, col, size=7.5, bold=True)
    y += 12

    # Phase labels
    def phase_hdr(title, col, yy):
        c.setFillColor(col)
        c.roundRect(10*mm, _y(ph/mm, yy+8), (pw - 20*mm), 8*mm, 3, fill=1, stroke=0)
        c.setFillColor(CW)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(14*mm, _y(ph/mm, yy+8) + 2.5*mm, title)

    # ── Phase 1 ───────────────────────────────────────────────────────────────
    y += 4
    phase_hdr("PHASE 1 — One-Time AWS Infrastructure Setup (before manufacturing)", CH, y)
    y += 12

    infra = [
        (CA,  "IoT Policy\nesp32p4-policy\n(device operations)"),
        (CA,  "IoT Policy\nesp32p4-claim-policy\n(provision only)"),
        (CA,  "Provisioning Template\nesp32p4-fleet\n+ Lambda hook"),
        (CD,  "Claim Certificate\nshared by all\nfirmware builds"),
        (CDB, "DynamoDB Table\nesp32p4-manufacturing\nchip_id → status"),
    ]
    bw = (W_P/mm - 20) / len(infra)
    for i, (col, txt) in enumerate(infra):
        proc_box(c, ph, 10 + i*bw, y, bw-1, 20, txt, col, size=7)
    y += 24

    # DynamoDB field table
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(CTX)
    c.drawString(12*mm, _y(ph/mm, y) - 2, "DynamoDB record — one row per device:")
    y += 6

    fields = [
        ("chip_id (PK)",       CDB, "48-bit hardware ID = WiFi MAC. Burned into silicon by Espressif. Cannot be changed or forged."),
        ("provisioned",        CDB, "false at factory → true after first boot (Lambda sets this during RegisterThing)"),
        ("provisioned_at",     CDB, "Timestamp written by Lambda the moment the device first provisions"),
        ("thing_name",         CA,  "AWS Thing name assigned at provision time, e.g. esp32p4-a4cf12345678"),
        ("erp_id",             CE,  "ERP asset ID written back by the ERP Lambda after Phase 4 registration"),
    ]
    fw1, fw2 = 38, (W_P/mm - 20) - 38
    for j, (fname, col, fdesc) in enumerate(fields):
        fy = y + j * 10
        proc_box(c, ph, 10,      fy, fw1-1, 9, fname, col, size=7, bold=True)
        proc_box(c, ph, 10+fw1,  fy, fw2-1, 9, fdesc, CBG, fg=CTX, size=7)
    y += len(fields) * 10 + 4

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    phase_hdr("PHASE 2 — Manufacturing  (repeated per batch at the factory)", CF, y)
    y += 12

    steps2 = [
        (CF,  "1. Read chip_id",      "esptool.py --port /dev/ttyUSB0 chip_id\n→ e.g. a4:cf:12:34:56:78"),
        (CDB, "2. Record in DynamoDB", "aws dynamodb put-item — stores chip_id,\nbatch_id, firmware_version, provisioned=false"),
        (CD,  "3. Flash firmware",    "esptool.py write_flash 0x0 firmware.bin\n(claim cert baked into secret.json)"),
        (CD,  "4. Upload claim cert", "mpremote: copy claim.pem.crt, claim.key,\nca.pem, secret.json to device flash"),
        (CF,  "5. Ship →",            "All 1000 units have identical firmware.\nChip ID is the only per-unit differentiator."),
    ]
    bh2 = 18
    bw2 = (W_P/mm - 20) / len(steps2)
    for i, (col, title, desc) in enumerate(steps2):
        bx = 10 + i * bw2
        proc_box(c, ph, bx, y,      bw2-1,  7, title, col,  size=7.5, bold=True)
        proc_box(c, ph, bx, y+7,    bw2-1, bh2-7, desc, CBG, fg=CTX, size=6.5)
        if i < len(steps2)-1:
            arr_right(c, ph, bx+bw2-1, y+bh2/2, 1.5)
    y += bh2 + 8

    # page number
    c.setFont("Helvetica", 7); c.setFillColor(CBR)
    c.drawCentredString(pw/2, 8*mm, "Page 1 of 4  —  docs/erp-integration.pdf")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2  — Swim lane diagram (landscape)
# ═══════════════════════════════════════════════════════════════════════════════

def page_swimlane(c):
    ph = H_L; pw = W_L
    PHmm = ph/mm; PWmm = pw/mm

    # header
    c.setFillColor(CH)
    c.rect(0, ph - 14*mm, pw, 14*mm, fill=1, stroke=0)
    c.setFillColor(CW); c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(pw/2, ph - 9*mm, "Full Workflow — Swim Lane Diagram")

    # lane definitions  (x, width) all in mm
    LM = 8   # left margin
    lanes = [
        ("FACTORY",       CF,  LM,     34),
        ("ESP32 DEVICE",  CD,  LM+34,  62),
        ("AWS IoT CORE",  CA,  LM+96,  78),
        ("ERP SYSTEM",    CE,  LM+174, 36),
    ]
    # draw lane headers + vertical dividers
    HEADER_Y = 14      # mm from top (already taken by banner)
    LANE_H   = 8
    for lname, lcol, lxp, lwp in lanes:
        proc_box(c, ph, lxp, HEADER_Y, lwp-0.5, LANE_H, lname, lcol, size=7.5, bold=True)
    # vertical lane lines
    c.setStrokeColor(CBR); c.setLineWidth(0.4)
    for _, _, lxp, _ in lanes[1:]:
        c.line(lxp*mm, _y(PHmm, HEADER_Y), lxp*mm, _y(PHmm, PHmm - 6))

    # swim lane rows  — each row: (y_top, row_height, cells)
    # cell = (lane_index, text, color) or None for empty
    # cross-lane arrows drawn separately
    ROW_Y = HEADER_Y + LANE_H + 1
    BH = 9    # box height mm
    GAP = 3   # gap between rows

    def lane_x(idx):   return lanes[idx][2] + lanes[idx][3]*0.05
    def lane_w(idx):   return lanes[idx][3] * 0.90
    def lane_cx(idx):  return lanes[idx][2] + lanes[idx][3] / 2

    rows = [
        # each row = list of (lane_idx, text, color)
        [(0, "Flash firmware\n(claim cert baked in)", CF),
         (2, "Create IoT policies,\nprovisioning template,\nclaim cert, DynamoDB table", CA)],
        [(0, "Record chip_id\nin DynamoDB", CF),
         (2, "DynamoDB ready:\nesp32p4-manufacturing", CDB)],
        [(0, "Ship device →→→", CF)],
        [(1, "Customer powers on\nboot.py: WiFi connect", CD)],
        [(1, "No unique cert found\n→ enter provisioning mode", CD)],
        [(1, "Connect to AWS IoT Core\nusing CLAIM cert (port 8883)", CD),
         (2, "Verify TLS —\nclaim cert accepted", CA)],
        [(1, "Read chip_id from hardware\n(WiFi MAC: a4cf12345678)", CD)],
        [(1, "→ Publish: $aws/certificates\n/create/json", CD),
         (2, "← Issue: certificatePem\n+ privateKey + ownershipToken", CA)],
        [(1, "→ Publish: provisioning template\nSerialNumber=chip_id", CD),
         (2, "← Call Lambda pre-provisioning hook", CLA)],
        [(2, "Lambda: validate chip_id in DynamoDB\nset provisioned=true, assign thing_name\nreturn allowProvisioning=true", CLA)],
        [(1, "← Receive: thingName\n+ unique cert + key", CD),
         (2, "Create Thing, activate cert\nattach esp32p4-policy", CA)],
        [(1, "Write unique cert + key + thingName\nto flash. Disconnect claim session.", CD)],
        [(1, "Reconnect with UNIQUE cert →", CD),
         (2, "← Normal operation begins", CA)],
        [(1, "→ Publish:\ndevices/<thing>/registered", CD),
         (2, "IoT Rule fires →", CA),
         (3, "← Lambda calls ERP API\nPOST /api/devices", CE)],
        [(2, "Lambda writes erp_id\nback to DynamoDB", CDB),
         (3, "ERP creates device record\nassigns ERP-00123, status=active", CE)],
        [(1, "Normal operation\ntelemetry / images / cmds", CD),
         (2, "Receive & store telemetry\nforward commands", CA),
         (3, "Device tracked in ERP\nlinked to customer/site", CE)],
    ]

    y = ROW_Y
    prev_y = {}   # lane_idx → last y_bottom for arrow
    for cells in rows:
        # determine row height by tallest cell
        max_lines = max(len(txt.split('\n')) for _, txt, _ in cells)
        rh = max(BH, max_lines * 8 + 3)

        for li, txt, col in cells:
            proc_box(c, ph, lane_x(li), y, lane_w(li), rh, txt, col, size=6.8)
            if li in prev_y:
                arr_down(c, ph, lane_cx(li), prev_y[li], y - prev_y[li])
            prev_y[li] = y + rh

        y += rh + GAP

    # draw cross-lane arrows for key steps (publish/receive pairs)
    # row indices for the publish/receive steps:
    # (drawn manually at approximate y positions based on row layout)

    # page number
    c.setFont("Helvetica", 7); c.setFillColor(CBR)
    c.drawCentredString(pw/2, 5*mm, "Page 2 of 4")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3  — Phase 3 provisioning flowchart (portrait, 2 columns)
# ═══════════════════════════════════════════════════════════════════════════════

def page_provisioning(c):
    ph = H_P; pw = W_P
    PHmm = ph/mm

    # header
    c.setFillColor(CD)
    c.rect(0, ph - 14*mm, pw, 14*mm, fill=1, stroke=0)
    c.setFillColor(CW); c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(pw/2, ph - 9*mm, "Phase 3 — Device First Boot: Provisioning Flowchart")

    # Two-column layout
    # Col A: left half (steps 1-10)   Col B: right half (steps 11-end)
    PAD = 10      # page left/right margin
    GUTTER = 8    # gap between columns
    COL_W = (W_P/mm - 2*PAD - GUTTER) / 2   # ~91mm each
    CX_A = PAD + COL_W/2          # col A centre x
    CX_B = PAD + COL_W + GUTTER + COL_W/2   # col B centre x
    BW   = COL_W - 2               # box width
    BH   = 10                      # process box height
    DH   = 14                      # diamond height
    TH   = 9                       # terminal height
    AH   = 5                       # arrow height between elements
    SIZE = 7.5

    def bx(cx): return cx - BW/2

    START_Y = 20

    # ── Column A ──────────────────────────────────────────────────────────────
    y = START_Y

    terminal(c, ph, bx(CX_A), y, BW, TH, "START", CH)
    y += TH; arr_down(c, ph, CX_A, y, AH); y += AH

    proc_box(c, ph, bx(CX_A), y, BW, BH, "boot.py: Connect to WiFi", CD, size=SIZE)
    y += BH; arr_down(c, ph, CX_A, y, AH); y += AH

    decision(c, ph, bx(CX_A), y, BW, DH, "Unique cert\nin flash?", CD, size=SIZE)
    diamond_mid_y = y + DH/2
    diamond_bot_y = y + DH
    note_label(c, ph, CX_A+BW/2+1, y+DH/2+2, "YES →", color=CYN)
    note_label(c, ph, CX_A-2, y+DH+1, "NO", color=CNO)
    y = diamond_bot_y; arr_down(c, ph, CX_A, y, AH); y += AH

    proc_box(c, ph, bx(CX_A), y, BW, BH, "Enter provisioning mode", CD, size=SIZE)
    y += BH; arr_down(c, ph, CX_A, y, AH); y += AH

    proc_box(c, ph, bx(CX_A), y, BW, BH, "Connect to AWS IoT Core\n(claim cert, port 8883)", CA, size=SIZE)
    y += BH; arr_down(c, ph, CX_A, y, AH); y += AH

    proc_box(c, ph, bx(CX_A), y, BW, BH,
             "Read chip_id from hardware\nnetwork.WLAN().config('mac')", CD, size=SIZE)
    y += BH; arr_down(c, ph, CX_A, y, AH); y += AH

    proc_box(c, ph, bx(CX_A), y, BW, BH,
             "Publish: $aws/certificates/create/json\n(empty payload)", CA, size=SIZE)
    y += BH; arr_down(c, ph, CX_A, y, AH); y += AH

    proc_box(c, ph, bx(CX_A), y, BW, BH,
             "AWS responds: certificatePem\n+ privateKey + ownershipToken", CA, size=SIZE)
    y += BH; arr_down(c, ph, CX_A, y, AH); y += AH

    proc_box(c, ph, bx(CX_A), y, BW, BH,
             "Publish: provisioning template\nSerialNumber=chip_id", CA, size=SIZE)
    y += BH; arr_down(c, ph, CX_A, y, AH); y += AH

    # "Continue →" marker at bottom of col A
    proc_box(c, ph, bx(CX_A), y, BW, TH, "→ continue col B", CH, size=7, bold=True)
    col_a_end_y = y + TH

    # YES branch from diamond → goes right off screen to a bypass box
    # Draw elbow: right from diamond right-midpoint → down to "Already provisioned" box
    bypass_x = PAD + COL_W + GUTTER/2
    bypass_y = diamond_mid_y - 1
    proc_box(c, ph, bypass_x - 12, bypass_y + 1, 24, BH,
             "Already provisioned\n→ reconnect (unique cert)", CD, size=6.5)
    arr_right(c, ph, CX_A + BW/2, diamond_mid_y, bypass_x - (CX_A + BW/2) - 13, "YES", CYN)
    # arrow from that box pointing to col B reconnect step (drawn after col B)

    # ── Column B ──────────────────────────────────────────────────────────────
    y = START_Y

    proc_box(c, ph, bx(CX_B), y, BW, TH, "← continued from col A", CH, size=7, bold=True)
    y += TH; arr_down(c, ph, CX_B, y, AH); y += AH

    proc_box(c, ph, bx(CX_B), y, BW, BH,
             "AWS calls pre-provisioning Lambda\nwith SerialNumber=chip_id", CLA, size=SIZE)
    y += BH; arr_down(c, ph, CX_B, y, AH); y += AH

    decision(c, ph, bx(CX_B), y, BW, DH, "chip_id in\nDynamoDB?", CDB, size=SIZE)
    d2_mid_y = y + DH/2
    d2_bot_y = y + DH
    note_label(c, ph, CX_B-2, d2_bot_y+1, "YES", color=CYN)
    note_label(c, ph, CX_B+BW/2+1, d2_mid_y+2, "NO →", color=CNO)
    # NO branch → rejected box to the right
    reject_x = CX_B + BW/2 + 3
    proc_box(c, ph, reject_x, d2_mid_y-BH/2, 22, BH,
             "allowProvisioning=false\nDevice REJECTED", CNO, size=6.5)
    arr_right(c, ph, CX_B+BW/2, d2_mid_y, reject_x - (CX_B+BW/2), "NO", CNO)
    terminal(c, ph, reject_x+3, d2_mid_y + BH + 2, 16, TH, "END (error)", CNO, size=7)
    arr_down(c, ph, reject_x+11, d2_mid_y+BH, 2)

    y = d2_bot_y; arr_down(c, ph, CX_B, y, AH); y += AH

    proc_box(c, ph, bx(CX_B), y, BW, BH,
             "Lambda: set provisioned=true\nrecord thing_name in DynamoDB", CDB, size=SIZE)
    y += BH; arr_down(c, ph, CX_B, y, AH); y += AH

    proc_box(c, ph, bx(CX_B), y, BW, BH,
             "AWS creates Thing\nactivates unique cert + attaches policy", CA, size=SIZE)
    y += BH; arr_down(c, ph, CX_B, y, AH); y += AH

    proc_box(c, ph, bx(CX_B), y, BW, BH,
             "Device receives: thingName\n+ unique cert + key", CD, size=SIZE)
    y += BH; arr_down(c, ph, CX_B, y, AH); y += AH

    proc_box(c, ph, bx(CX_B), y, BW, BH,
             "Device writes cert + key\n+ thingName to flash", CD, size=SIZE)
    y += BH; arr_down(c, ph, CX_B, y, AH); y += AH

    proc_box(c, ph, bx(CX_B), y, BW, BH, "Disconnect claim cert session", CD, size=SIZE)
    y += BH; arr_down(c, ph, CX_B, y, AH); y += AH

    reconnect_y = y
    proc_box(c, ph, bx(CX_B), y, BW, BH, "Reconnect with UNIQUE cert", CD, size=SIZE)
    y += BH; arr_down(c, ph, CX_B, y, AH); y += AH

    proc_box(c, ph, bx(CX_B), y, BW, BH,
             "Publish: devices/<thing>/registered\n{ chip_id, firmware, timestamp }", CD, size=SIZE)
    y += BH; arr_down(c, ph, CX_B, y, AH); y += AH

    terminal(c, ph, bx(CX_B), y, BW, TH, "→ Phase 4: ERP Registration", CE)
    y += TH

    # Connecting arrow from col A bottom to col B top
    arr_elbow(c, ph, CX_A, col_a_end_y, CX_B, START_Y)

    # Arrow from bypass box down to reconnect step
    arr_elbow(c, ph, bypass_x+12, bypass_y+BH+1, CX_B - BW/2 - 1, reconnect_y + BH/2)

    # column separator dashed line
    sep_x = PAD + COL_W + GUTTER/2
    c.setStrokeColor(CBR); c.setLineWidth(0.4); c.setDash([2, 3])
    c.line(sep_x*mm, _y(PHmm, START_Y-2), sep_x*mm, _y(PHmm, y+2))
    c.setDash()

    # page number
    c.setFont("Helvetica", 7); c.setFillColor(CBR)
    c.drawCentredString(pw/2, 8*mm, "Page 3 of 4")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4  — Phase 4 ERP flowchart + Idempotency  (LANDSCAPE)
#
# Layout (all mm, landscape = 297 × 210):
#   margin 10 | flowchart col 105 | bypass zone 33 | idempotency col 139 | margin 10
#   total: 10 + 105 + 33 + 139 + 10 = 297 ✓
#   usable height: 210 - 14 (header) - 7 (footer) = 189mm
# ═══════════════════════════════════════════════════════════════════════════════

def page_erp(c):
    ph   = H_L          # landscape height = 210 mm in points
    pw   = W_L          # landscape width  = 297 mm in points
    PHmm = ph / mm      # 210
    PWmm = pw / mm      # 297

    # ── header banner ─────────────────────────────────────────────────────────
    c.setFillColor(CE)
    c.rect(0, ph - 14*mm, pw, 14*mm, fill=1, stroke=0)
    c.setFillColor(CW)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(pw/2, ph - 9*mm,
        "Phase 4 — ERP Registration Flowchart  +  Idempotency")

    # ── geometry ──────────────────────────────────────────────────────────────
    PAD      = 10          # page margin mm
    FC_W     = 105         # flowchart column width mm
    FC_CX    = PAD + FC_W / 2          # 62.5 — centre x of flowchart
    BW       = FC_W - 12               # 93   — process box width
    FC_LEFT  = FC_CX - BW / 2         # 16   — box left edge

    BYPASS_X = PAD + FC_W + 2         # 117  — skip-box left edge
    BYPASS_W = 28                      # skip-box width  → right edge 145

    IDEM_X   = BYPASS_X + BYPASS_W + 5  # 150 — idempotency column left edge
    IDEM_W   = PWmm - IDEM_X - PAD    # 137  — idempotency column width

    BH   = 11   # process box height mm
    DH   = 15   # diamond height mm
    TH   = 9    # terminal height mm
    AH   = 5    # arrow gap mm
    SIZE = 7.5

    START_Y = 20   # mm from page top

    # ── flowchart (left column) ───────────────────────────────────────────────
    y = START_Y

    proc_box(c, ph, FC_LEFT, y, BW, BH,
             "Device publishes: devices/<thing>/registered\n"
             "{ thing_name, chip_id, firmware_version, timestamp }",
             CD, size=SIZE)
    y += BH; arr_down(c, ph, FC_CX, y, AH); y += AH

    proc_box(c, ph, FC_LEFT, y, BW, BH,
             "AWS IoT Rule fires: SELECT * FROM 'devices/+/registered'\n"
             "→ invokes Lambda: register-device-in-erp",
             CA, size=SIZE)
    y += BH; arr_down(c, ph, FC_CX, y, AH); y += AH

    # decision diamond
    decision(c, ph, FC_LEFT, y, BW, DH,
             "erp_id already set\nin DynamoDB?", CDB, size=SIZE)
    d_top = y
    d_mid = y + DH / 2     # vertical midpoint of diamond
    d_bot = y + DH
    y = d_bot

    # YES bypass: arrow right from diamond → skip box → END terminal
    # diamond right vertex x = FC_LEFT + BW = 16 + 93 = 109
    D_RIGHT = FC_LEFT + BW
    skip_mid_y = d_mid           # keep bypass at diamond's mid height
    skip_top_y = skip_mid_y - BH / 2
    arr_right(c, ph, D_RIGHT, d_mid, BYPASS_X - D_RIGHT, "YES", CYN)
    proc_box(c, ph, BYPASS_X, skip_top_y, BYPASS_W, BH,
             "Skip ERP call\n(idempotent)", CYN, size=6.5)
    arr_down(c, ph, BYPASS_X + BYPASS_W/2, skip_top_y + BH, AH)
    terminal(c, ph, BYPASS_X + 2, skip_top_y + BH + AH, BYPASS_W - 4, TH,
             "END (ok)", CYN, size=7)

    # NO path continues down
    note_label(c, ph, FC_CX - 5, d_bot + 1.5, "NO", color=CNO)
    arr_down(c, ph, FC_CX, y, AH); y += AH

    proc_box(c, ph, FC_LEFT, y, BW, BH,
             "Lambda calls ERP REST API:\n"
             "POST https://erp.yourcompany.com/api/devices  "
             "{ serial, thing, firmware, activated }",
             CE, size=SIZE)
    y += BH; arr_down(c, ph, FC_CX, y, AH); y += AH

    proc_box(c, ph, FC_LEFT, y, BW, BH,
             "ERP creates device record:\n"
             "assigns erp_id (ERP-00123), links to customer/site, status = active",
             CE, size=SIZE)
    y += BH; arr_down(c, ph, FC_CX, y, AH); y += AH

    proc_box(c, ph, FC_LEFT, y, BW, BH,
             "Lambda writes erp_id back to DynamoDB:\n"
             "SET erp_id = 'ERP-00123'  WHERE chip_id = 'a4cf12345678'",
             CDB, size=SIZE)
    y += BH; arr_down(c, ph, FC_CX, y, AH); y += AH

    terminal(c, ph, FC_LEFT, y, BW, TH,
             "END — Device fully operational + tracked in ERP", CE)
    y += TH

    # safety check: ensure flowchart stays inside page
    assert y < PHmm - 7, f"Flowchart overflows page: y={y:.1f} > {PHmm-7:.1f}"

    # ── idempotency column (right) ────────────────────────────────────────────
    # header bar
    c.setFillColor(CH)
    c.roundRect(IDEM_X*mm, _y(PHmm, START_Y + 8),
                IDEM_W*mm, 8*mm, 3, fill=1, stroke=0)
    c.setFillColor(CW)
    c.setFont("Helvetica-Bold", 9)
    c.drawString((IDEM_X + 3)*mm,
                 _y(PHmm, START_Y + 8) + 2.5*mm,
                 "Idempotency — Handling Reboots & Retries")

    iy   = START_Y + 10   # idempotency content start y
    IH   = 20             # row height mm
    IFW1 = 33             # label column width
    IFW2 = IDEM_W - IFW1 - 1

    idems = [
        (CD,
         "Reboot before\ncert stored",
         "Device restarts provisioning from scratch.\n"
         "Lambda should deactivate incomplete certs\n"
         "(those with no attached Thing) to avoid\n"
         "orphaned certs accumulating in AWS IoT."),
        (CD,
         "Reboot after cert\nbefore /registered",
         "Device reconnects with its unique cert and\n"
         "republishes /registered. The ERP Lambda\n"
         "checks erp_id in DynamoDB before calling\n"
         "the ERP API — skips the call if already set."),
        (CDB,
         "Second provision\nsame chip_id",
         "Lambda finds provisioned=true in DynamoDB\n"
         "→ returns allowProvisioning=false.\n"
         "AWS rejects the registration. Only one\n"
         "unique cert is ever issued per device."),
    ]

    for k, (col, title, desc) in enumerate(idems):
        ky = iy + k * (IH + 2)
        proc_box(c, ph, IDEM_X,          ky, IFW1 - 1, IH, title, col,
                 size=7.5, bold=True)
        proc_box(c, ph, IDEM_X + IFW1,   ky, IFW2 - 1, IH, desc, CBG,
                 fg=CTX, size=7)

    idem_end = iy + len(idems) * (IH + 2)
    assert idem_end < PHmm - 7, \
        f"Idempotency overflows page: {idem_end:.1f} > {PHmm-7:.1f}"

    # ── footer ────────────────────────────────────────────────────────────────
    c.setFont("Helvetica", 7)
    c.setFillColor(CBR)
    c.drawCentredString(
        pw / 2, 5*mm,
        "Page 4 of 4  —  See README.md §Fleet provisioning for CLI commands  |  "
        "https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html")


# ═══════════════════════════════════════════════════════════════════════════════
# Build
# ═══════════════════════════════════════════════════════════════════════════════

def build():
    c = Canvas(OUT)

    # Page 1 — portrait
    c.setPageSize(A4)
    page_title(c)
    c.showPage()

    # Page 2 — landscape
    c.setPageSize(landscape(A4))
    page_swimlane(c)
    c.showPage()

    # Page 3 — portrait
    c.setPageSize(A4)
    page_provisioning(c)
    c.showPage()

    # Page 4 — landscape
    c.setPageSize(landscape(A4))
    page_erp(c)
    c.showPage()

    c.save()
    print(f"Written: {os.path.abspath(OUT)}")


if __name__ == "__main__":
    build()
