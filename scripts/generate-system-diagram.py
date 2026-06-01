#!/usr/bin/env python3
"""
Generate docs/system.entity.diagram.pdf
Run: python3 scripts/generate-system-diagram.py
Requires: pip install reportlab
"""

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "system.entity.diagram.pdf")

W, H  = landscape(A4)   # 297 × 210 mm (points)
Wmm   = W / mm           # 297
Hmm   = H / mm           # 210

# ── Colours ──────────────────────────────────────────────────────────────────
CW    = colors.HexColor("#2E7D32")   # Windows green
CD    = colors.HexColor("#1565C0")   # Docker / QEMU blue
CA    = colors.HexColor("#E65100")   # AWS / LocalStack orange
CDEV  = colors.HexColor("#1A237E")   # Developer dark blue
CFS   = colors.HexColor("#607D8B")   # filesystem grey-blue
CHW   = colors.HexColor("#6A1B9A")   # hardware purple
CBLD  = colors.HexColor("#37474F")   # builder dark grey
CQEMU = colors.HexColor("#0277BD")   # QEMU light blue
CBRD  = colors.HexColor("#B0BEC5")   # border
CBGA  = colors.HexColor("#FAFAFA")   # box background
CARR  = colors.HexColor("#424242")   # arrow
CTX   = colors.HexColor("#212121")   # text
CW2   = colors.white

def _y(y_mm):
    """Top-relative mm → ReportLab bottom-relative points."""
    return (Hmm - y_mm) * mm

# ── Drawing helpers ───────────────────────────────────────────────────────────

def box(c, x, y, w, h, title, bg, fg=None, size=7.5, bold=True, subtitle=""):
    """Rounded box. x,y,w,h in mm. y = top."""
    fg = fg or CW2
    c.setFillColor(bg)
    c.setStrokeColor(CBRD)
    c.setLineWidth(0.6)
    c.roundRect(x*mm, _y(y+h), w*mm, h*mm, 3, fill=1, stroke=1)
    c.setFillColor(fg)
    fn = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(fn, size)
    lines = title.split("\n")
    lh = size + 1.8
    ty = _y(y + h/2) + (len(lines)-1)*lh/2
    if subtitle:
        ty = _y(y + h/2) + lh/2 + 1
    for i, ln in enumerate(lines):
        c.drawCentredString((x + w/2)*mm, ty - i*lh, ln)
    if subtitle:
        c.setFont("Helvetica", size - 1.5)
        c.setFillColor(fg)
        c.drawCentredString((x + w/2)*mm, _y(y + h/2) - lh/2, subtitle)

def group_box(c, x, y, w, h, label, bg, alpha=0.08):
    """Lightly filled group boundary with label at top-left."""
    r, g, b = bg.red, bg.green, bg.blue
    fill = colors.HexColor(
        "#%02x%02x%02x" % (
            int(r*255*(1-alpha) + 255*alpha),
            int(g*255*(1-alpha) + 255*alpha),
            int(b*255*(1-alpha) + 255*alpha),
        )
    )
    c.setFillColor(fill)
    c.setStrokeColor(bg)
    c.setLineWidth(1.0)
    c.roundRect(x*mm, _y(y+h), w*mm, h*mm, 5, fill=1, stroke=1)
    c.setFillColor(bg)
    c.setFont("Helvetica-Bold", 7)
    c.drawString((x + 2)*mm, _y(y) - 2*mm, label)

def _tri(c, pts):
    p = c.beginPath()
    p.moveTo(pts[0], pts[1])
    p.lineTo(pts[2], pts[3])
    p.lineTo(pts[4], pts[5])
    p.close()
    c.drawPath(p, fill=1, stroke=0)

def arrow(c, x1, y1, x2, y2, label="", color=None, dashed=False):
    """Straight arrow from (x1,y1) to (x2,y2) in mm."""
    color = color or CARR
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(0.9)
    if dashed:
        c.setDash([3, 2])
    else:
        c.setDash()
    # direction
    dx = x2 - x1; dy = y2 - y1
    import math
    length = math.sqrt(dx*dx + dy*dy)
    if length < 0.01:
        return
    ux = dx/length; uy = dy/length
    # stop 3mm before endpoint for arrowhead
    ex = (x2 - ux*3)*mm; ey = _y(y2 + uy*3)
    c.line(x1*mm, _y(y1), ex, ey)
    c.setDash()
    # arrowhead
    ax = x2*mm; ay = _y(y2)
    px = -uy*mm*2; py = ux*mm*2
    _tri(c, [ax, ay, ex+px, ey+py, ex-px, ey-py])
    if label:
        mx = (x1 + x2)/2; my = (y1 + y2)/2
        c.setFont("Helvetica", 5.5)
        c.setFillColor(color)
        offset = 3 if abs(dx) > abs(dy) else -3
        c.drawCentredString(mx*mm, _y(my) + offset, label)

def elbow_arrow(c, x1, y1, x2, y2, label="", color=None, via_x=None, via_y=None):
    """L-shaped arrow. via_x or via_y sets the bend point."""
    color = color or CARR
    if via_x is not None:
        arrow(c, x1, y1, via_x, y1, color=color)
        arrow(c, via_x, y1, x2, y2, label=label, color=color)
    elif via_y is not None:
        arrow(c, x1, y1, x1, via_y, color=color)
        arrow(c, x1, via_y, x2, y2, label=label, color=color)

def label(c, x, y, text, size=6, color=None, align="left"):
    color = color or CTX
    c.setFillColor(color)
    c.setFont("Helvetica", size)
    if align == "center":
        c.drawCentredString(x*mm, _y(y), text)
    elif align == "right":
        c.drawRightString(x*mm, _y(y), text)
    else:
        c.drawString(x*mm, _y(y), text)

def port_tag(c, x, y, text, bg):
    """Small port label pill."""
    tw = len(text)*3.8 + 4
    c.setFillColor(bg)
    c.setStrokeColor(CBRD)
    c.setLineWidth(0.3)
    c.roundRect(x*mm, _y(y+3.5), tw, 3.5*mm, 1.5, fill=1, stroke=1)
    c.setFillColor(CW2)
    c.setFont("Helvetica-Bold", 5.5)
    c.drawCentredString(x*mm + tw/2, _y(y+3.5) + 1.2*mm, text)
    return tw/mm

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Full system overview
# ═══════════════════════════════════════════════════════════════════════════════

def page_overview(c):
    # ── header ────────────────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#1A237E"))
    c.rect(0, H - 12*mm, W, 12*mm, fill=1, stroke=0)
    c.setFillColor(CW2)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W/2, H - 8*mm, "ESP32-P4 IoT System — Entity Interaction Diagram")

    # ── geometry ──────────────────────────────────────────────────────────────
    M      = 8    # page margin mm
    TOP    = 16   # below header
    BOTTOM = 205  # above footer

    # column x positions
    WIN_X  = M;         WIN_W  = 44
    DOC_X  = WIN_X + WIN_W + 4;  DOC_W = 175
    DEV_X  = DOC_X + DOC_W + 4;  DEV_W = Wmm - DEV_X - M

    # row y positions
    MAIN_Y  = TOP + 6   # top of main content rows
    MAIN_H  = 62
    EMU_Y   = MAIN_Y + MAIN_H + 4
    EMU_H   = 44
    FS_Y    = EMU_Y + EMU_H + 4
    FS_H    = 18
    HW_Y    = FS_Y + FS_H + 4
    HW_H    = 16

    # ── group outlines ────────────────────────────────────────────────────────
    group_box(c, WIN_X, MAIN_Y-5, WIN_W, MAIN_H+10, "WINDOWS HOST", CW, alpha=0.12)
    group_box(c, DOC_X, MAIN_Y-5, DOC_W, MAIN_H+EMU_H+14,
              "DOCKER  iot-net  (WSL2)", CD, alpha=0.07)
    group_box(c, DEV_X, MAIN_Y-5, DEV_W, MAIN_H+EMU_H+14,
              "DEVELOPER TOOLS", CDEV, alpha=0.12)
    group_box(c, M, FS_Y-1, Wmm-2*M, FS_H+2,
              "HOST FILESYSTEM  (bind-mounted into containers)", CFS, alpha=0.12)
    c.setDash([4, 3])
    c.setStrokeColor(CHW)
    c.setLineWidth(0.8)
    c.roundRect(M*mm, _y(HW_Y+HW_H), (Wmm-2*M)*mm, HW_H*mm, 5, fill=0, stroke=1)
    c.setDash()
    label(c, M+2, HW_Y, "PHYSICAL HARDWARE  (optional — real ESP32-P4)", size=7, color=CHW)

    # ── WINDOWS HOST entities ─────────────────────────────────────────────────
    WCX = WIN_X + 2; WCW = WIN_W - 4
    box(c, WCX, MAIN_Y+2,  WCW, 12, "Windows\nCamera", CW, size=7)
    box(c, WCX, MAIN_Y+22, WCW, 16,
        "windows.camera\nserver/server.py",
        CW, size=6.5, subtitle=":8081")

    # arrow: win camera → server.py
    arrow(c, WCX+WCW/2, MAIN_Y+14, WCX+WCW/2, MAIN_Y+22,
          "DirectShow", CW)

    # ── DOCKER entities ───────────────────────────────────────────────────────
    # localstack
    LS_X = DOC_X + 3;  LS_W = 46
    box(c, LS_X, MAIN_Y+2, LS_W, MAIN_H-4,
        "localstack",
        CA, size=8, bold=True)
    # port tags on localstack
    px = LS_X + 2
    py = MAIN_Y + MAIN_H - 3
    for ptxt in [":4566 API", ":1883 MQTT", ":8883 TLS"]:
        pw = port_tag(c, px, py, ptxt, CA)
        px += pw + 1

    # camera-proxy
    CP_X = LS_X + LS_W + 4;  CP_W = 52
    box(c, CP_X, MAIN_Y+2, CP_W, MAIN_H-4,
        "camera-proxy\ncamera.proxy/server.py",
        CD, size=7, bold=True)
    # backends sub-labels
    label(c, CP_X+2, MAIN_Y+26, "backends/", size=6, color=CW2)
    for i, be in enumerate(["network.py", "v4l2.py", "pattern.py"]):
        label(c, CP_X+5, MAIN_Y+31+i*7, "• "+be, size=5.8, color=CW2)
    port_tag(c, CP_X+2, MAIN_Y+MAIN_H-3, ":8080", CD)

    # micropython-builder
    BLD_X = CP_X + CP_W + 4;  BLD_W = 42
    box(c, BLD_X, MAIN_Y+2, BLD_W, 26,
        "micropython\n-builder",
        CBLD, size=7)
    label(c, BLD_X+2, MAIN_Y+32, "Builds firmware.bin", size=6, color=CW2)
    label(c, BLD_X+2, MAIN_Y+38, "IDF + MicroPython", size=5.8, color=CW2)

    # ── esp32p4-emulator (QEMU) ───────────────────────────────────────────────
    EMU_BOX_X = DOC_X + 3
    EMU_BOX_W = DOC_W - 6
    group_box(c, EMU_BOX_X, EMU_Y, EMU_BOX_W, EMU_H,
              "esp32p4-emulator  —  QEMU ESP32-P4 machine  (run-qemu.sh)", CQEMU, alpha=0.10)

    # QEMU internals
    QX = EMU_BOX_X + 3; QY = EMU_Y + 9; QH = 22; QSW = 34
    for i, (name, sub) in enumerate([
        ("boot.py",   "WiFi connect"),
        ("main.py",   "Camera + MQTT"),
        ("secret.py", "Config reader"),
    ]):
        bx = QX + i*(QSW+3)
        box(c, bx, QY, QSW, QH, name, CQEMU, size=7.5)
        label(c, bx+QSW/2, QY+QH-5, sub, size=5.8, color=CW2, align="center")

    # port tags inside emulator
    px2 = QX + 3*(QSW+3) + 4
    port_tag(c, px2, QY+4, "TCP:2323 serial", CQEMU)
    port_tag(c, px2, QY+11, "TCP:1234 GDB", CQEMU)
    label(c, px2, QY+20, "SLiRP net", size=6, color=CQEMU)
    label(c, px2, QY+26, "10.0.2.0/24", size=5.5, color=CQEMU)

    # ── DEVELOPER TOOLS ───────────────────────────────────────────────────────
    DV_X = DEV_X + 2; DV_W = DEV_W - 4
    dev_items = [
        ("mpremote", "serial REPL →\n:2323"),
        ("mosquitto_sub", "MQTT subscribe\n→ :1883"),
        ("browser", "MJPEG preview\n→ :8080"),
        ("aws cli /\nsetup-localstack.sh", "IoT provision\n→ :4566"),
    ]
    dy = MAIN_Y + 2
    for name, sub in dev_items:
        box(c, DV_X, dy, DV_W, 16, name+"\n"+sub, CDEV, size=6)
        dy += 18

    # ── HOST FILESYSTEM entities ──────────────────────────────────────────────
    fs_items = [
        ("secret.json",         CFS),
        ("firmware-out/\nfirmware.bin", CFS),
        ("certs/",              CFS),
        ("micropython/src/\n(scripts bind mount)", CFS),
    ]
    fw = (Wmm - 2*M - 4) / len(fs_items)
    for i, (name, col) in enumerate(fs_items):
        fx = M + 2 + i*(fw+1)
        box(c, fx, FS_Y+2, fw-1, FS_H-4, name, col, size=6.5)

    # ── PHYSICAL HARDWARE ─────────────────────────────────────────────────────
    hw_items = [
        ("ESP32-P4 + MIPI\nCSI-2 Camera",    CHW),
        ("WiFi Network",                       CHW),
        ("AWS IoT Core\n:8883 TLS (real AWS)", CHW),
        ("localstack :8883\nTLS (dev)",        CA),
    ]
    hw_fw = (Wmm - 2*M - 4) / len(hw_items)
    for i, (name, col) in enumerate(hw_items):
        hx = M + 2 + i*(hw_fw+1)
        box(c, hx, HW_Y+2, hw_fw-1, HW_H-4, name, col, size=6.5)

    # ── ARROWS ────────────────────────────────────────────────────────────────

    # win.cam.server → camera-proxy (network mode, horizontal)
    arrow(c, WCX+WCW, MAIN_Y+30, CP_X, MAIN_Y+30,
          "HTTP :8081 /frame.jpg\n(CAMERA_SOURCE=network)", CW)

    # camera-proxy → localstack (not direct, but QEMU does via main.py)
    # main.py → camera-proxy (HTTP fetch)
    arrow(c, QX+QSW, QY+11, CP_X+CP_W/2, EMU_Y,
          "HTTP :8080\n/frame.jpg", CD)

    # main.py → localstack (MQTT publish)
    arrow(c, QX+QSW/2, QY, LS_X+LS_W/2, MAIN_Y+MAIN_H-4,
          "MQTT :1883/:8883\npublish", CA)

    # micropython-builder → firmware.bin (host FS)
    arrow(c, BLD_X+BLD_W/2, MAIN_Y+28,
          M+2+1*(fw+1)+fw/2, FS_Y+2,
          "build output", CBLD)

    # firmware.bin → emulator (bind mount, dashed)
    arrow(c, M+2+1*(fw+1)+fw/2, FS_Y+FS_H-2,
          EMU_BOX_X + EMU_BOX_W*0.35, EMU_Y+EMU_H,
          "bind mount :ro", CFS, dashed=True)

    # secret.json → emulator (bind mount, dashed)
    arrow(c, M+2+fw/2, FS_Y+FS_H-2,
          EMU_BOX_X + 5, EMU_Y+EMU_H,
          "bind mount :ro", CFS, dashed=True)

    # scripts bind mount → emulator
    arrow(c, M+2+3*(fw+1)+fw/2, FS_Y+FS_H-2,
          EMU_BOX_X + EMU_BOX_W*0.65, EMU_Y+EMU_H,
          "bind mount :ro", CFS, dashed=True)

    # mpremote → emulator serial port
    arrow(c, DV_X, MAIN_Y+10, EMU_BOX_X+EMU_BOX_W, EMU_Y+8,
          "TCP :2323", CDEV)

    # mosquitto_sub → localstack
    arrow(c, DV_X, MAIN_Y+28, LS_X+LS_W, MAIN_Y+28,
          "MQTT :1883", CDEV)

    # browser → camera-proxy
    arrow(c, DV_X, MAIN_Y+46, CP_X+CP_W, MAIN_Y+22,
          "HTTP :8080\n/stream", CDEV)

    # aws cli → localstack
    arrow(c, DV_X, MAIN_Y+62, LS_X+LS_W, MAIN_Y+50,
          "HTTP :4566", CDEV)

    # V4L2 path label on camera-proxy (no arrow — internal note)
    label(c, CP_X+2, MAIN_Y+56, "USB webcam via /dev/video0", size=5.5, color=CW2)
    label(c, CP_X+2, MAIN_Y+60, "(CAMERA_SOURCE=v4l2)", size=5.5, color=CW2)

    # physical hardware → AWS/LocalStack (dashed)
    arrow(c, M+2+hw_fw/2, HW_Y+2,
          M+2+3*(hw_fw+1)+hw_fw/2, HW_Y+2,
          "WiFi → MQTT TLS :8883", CHW, dashed=True)

    # ── legend ────────────────────────────────────────────────────────────────
    lx = M + 2; ly = 199
    label(c, lx, ly, "Legend:", size=6.5, color=CTX)
    items = [
        (CW,   "Windows host"),
        (CD,   "Docker/QEMU (WSL2)"),
        (CA,   "AWS / LocalStack"),
        (CDEV, "Developer tools"),
        (CFS,  "Host filesystem"),
        (CHW,  "Physical hardware"),
    ]
    for i, (col, txt) in enumerate(items):
        bx = lx + 16 + i * 38
        c.setFillColor(col)
        c.setStrokeColor(CBRD)
        c.setLineWidth(0.4)
        c.roundRect(bx*mm, _y(ly+4), 5*mm, 4*mm, 1, fill=1, stroke=1)
        label(c, bx+6, ly+0.5, txt, size=5.8, color=CTX)

    # dashed line legend
    bx = lx + 16 + len(items)*38
    c.setStrokeColor(CFS)
    c.setLineWidth(0.9)
    c.setDash([3, 2])
    c.line(bx*mm, _y(ly+2), (bx+5)*mm, _y(ly+2))
    c.setDash()
    label(c, bx+6, ly+0.5, "bind mount", size=5.8, color=CTX)

    # ── page footer ───────────────────────────────────────────────────────────
    c.setFont("Helvetica", 6)
    c.setFillColor(CBRD)
    c.drawCentredString(W/2, 5*mm,
        "docs/system.entity.diagram.pdf  —  regenerate: python3 scripts/generate-system-diagram.py")


# ═══════════════════════════════════════════════════════════════════════════════
# Build
# ═══════════════════════════════════════════════════════════════════════════════

def build():
    c = Canvas(OUT)
    c.setPageSize(landscape(A4))
    page_overview(c)
    c.showPage()
    c.save()
    print(f"Written: {os.path.abspath(OUT)}")


if __name__ == "__main__":
    build()
