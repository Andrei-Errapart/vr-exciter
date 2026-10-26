"""Build the KiCad source boards from which the module 3D models are exported.

Run with KiCad's bundled Python (it needs the pcbnew module); see
make-module-models. Each module is drawn centred on (100, 100) mm with the
parts it carries, and male pin headers on the bottom side, pins pointing
down. kicad-cli then exports it as STEP with the origin at the module centre
and z = 0 at the underside of the module PCB.

    build_sources.py <output dir>

Inputs:
- WeAct STM32G474 Core Board: WeAct's own STEP with the pins-up headers removed
  (lib/3d/src/weact-stm32g474-coreboard-v10_no-headers.step), outline and pin
  grid from WeAct's outline drawing (datasheets/weact_stm32G474/README.md).
- SimpleFOC Mini v1.0: outline, holes and part positions from the upstream
  Gerbers and pick-and-place file (datasheets/drv8313/simplefocmini-v1.0/),
  with KiCad library parts standing in for the real ones.
- MT3608 boost module: generic 37.2 x 17.3 mm layout after the components101
  drawing; positions are approximate.
"""
import csv
import math
import os
import re
import sys

import pcbnew

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
OUT = None
KICAD_FP = os.environ.get(
    "KICAD10_FOOTPRINT_DIR",
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
CX, CY = 100.0, 100.0


def mm(x, y):
    return pcbnew.VECTOR2I_MM(x, y)


def new_board(thickness):
    b = pcbnew.BOARD()
    b.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(thickness))
    return b


def edge_line(b, x0, y0, x1, y1):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(mm(x0, y0))
    s.SetEnd(mm(x1, y1))
    s.SetWidth(pcbnew.FromMM(0.1))
    b.Add(s)


def edge_arc(b, start, mid, end):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetArcGeometry(mm(*start), mm(*mid), mm(*end))
    s.SetWidth(pcbnew.FromMM(0.1))
    b.Add(s)


def edge_rounded_rect(b, w, h, r):
    x0, y0, x1, y1 = CX - w / 2, CY - h / 2, CX + w / 2, CY + h / 2
    edge_line(b, x0 + r, y0, x1 - r, y0)
    edge_line(b, x1, y0 + r, x1, y1 - r)
    edge_line(b, x1 - r, y1, x0 + r, y1)
    edge_line(b, x0, y1 - r, x0, y0 + r)
    k = r * (1 - math.sqrt(0.5))
    edge_arc(b, (x1 - r, y0), (x1 - k, y0 + k), (x1, y0 + r))
    edge_arc(b, (x1, y1 - r), (x1 - k, y1 - k), (x1 - r, y1))
    edge_arc(b, (x0 + r, y1), (x0 + k, y1 - k), (x0, y1 - r))
    edge_arc(b, (x0, y0 + r), (x0 + k, y0 + k), (x0 + r, y0))


def npth(b, x, y, d):
    fp = pcbnew.FOOTPRINT(b)
    fp.SetReference("H")
    fp.Reference().SetVisible(False)
    p = pcbnew.PAD(fp)
    p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    p.SetSize(mm(d, d))
    p.SetDrillSize(mm(d, d))
    p.SetLayerSet(pcbnew.PAD.UnplatedHoleMask())
    fp.Add(p)
    fp.SetPosition(mm(x, y))
    b.Add(fp)


def part(b, lib, name, ref, x, y, rot=0.0, bottom=False):
    fp = pcbnew.FootprintLoad(os.path.join(KICAD_FP, lib + ".pretty"), name)
    if fp is None:
        sys.exit(f"footprint not found: {lib}:{name}")
    fp.SetReference(ref)
    b.Add(fp)
    if bottom:
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(mm(x, y))
    return fp


def header_on_grid(b, name, ref, pins):
    """Bottom-side male header whose pads land exactly on the given pin
    positions (any pin order). Tries the four orientations."""
    want = sorted((round(x, 2), round(y, 2)) for x, y in pins)
    wcx = sum(x for x, _ in pins) / len(pins)
    wcy = sum(y for _, y in pins) / len(pins)
    for rot in (0, 90, 180, 270):
        fp = part(b, "Connector_PinHeader_2.54mm", name, ref, 0, 0, rot, bottom=True)
        pads = [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in fp.Pads()]
        pcx = sum(x for x, _ in pads) / len(pads)
        pcy = sum(y for _, y in pads) / len(pads)
        fp.SetPosition(mm(wcx - pcx, wcy - pcy))
        got = sorted((round(pcbnew.ToMM(p.GetPosition().x), 2), round(pcbnew.ToMM(p.GetPosition().y), 2))
                     for p in fp.Pads())
        if all(abs(a[0] - c[0]) < 0.02 and abs(a[1] - c[1]) < 0.02 for a, c in zip(got, want)):
            return fp
        b.Remove(fp)
    sys.exit(f"{ref}: {name} does not fit the pin grid")


def save(b, name):
    path = os.path.join(OUT, name + ".kicad_pcb")
    b.Save(path)
    print("wrote", path)


# --------------------------------------------------------------------------
# WeAct STM32G474 Core Board: 36.28 x 28.14 mm, 1.59 mm PCB.
# Pin grid (top view, USB-C on the left): first column 6.97 mm from the left
# edge, outer rows 1.37 mm from the top/bottom edges, 2.54 mm pitch.
W_W, W_H = 36.28, 28.14


def weact_pins():
    cols = [-W_W / 2 + 6.97 + 2.54 * i for i in range(12)]
    rows = {"P2": (-W_H / 2 + 1.37, -W_H / 2 + 1.37 + 2.54), "P1": (W_H / 2 - 1.37 - 2.54, W_H / 2 - 1.37)}
    return cols, rows


def build_weact():
    b = new_board(1.59)
    edge_rounded_rect(b, W_W, W_H, 0.5)     # only used for framing; exported without board body
    fp = pcbnew.FOOTPRINT(b)
    fp.SetReference("BODY")
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = "${KIPRJMOD}/weact-stm32g474-coreboard-v10_no-headers.step"
    # WeAct's model: origin at the lower-left board corner, board top at z = 0.
    m.m_Offset = pcbnew.VECTOR3D(-W_W / 2, -W_H / 2, 0.0)
    fp.Models().push_back(m)
    fp.SetPosition(mm(CX, CY))
    b.Add(fp)
    cols, rows = weact_pins()
    for ref, (r0, r1) in rows.items():
        pins = [(CX + c, CY + r) for c in cols for r in (r0, r1)]
        header_on_grid(b, "PinHeader_2x12_P2.54mm_Vertical", ref, pins)
    save(b, "weact_stm32g474_coreboard")


# --------------------------------------------------------------------------
# SimpleFOC Mini v1.0, from the upstream EasyEDA Gerbers (mm, Y up).
SFM = os.path.join(ROOT, "datasheets/drv8313/simplefocmini-v1.0")


def gerber_outline(path):
    """Segments ('L', p0, p1) and CCW arcs ('A', p0, p1, centre) of an EasyEDA outline."""
    segs, cur, mode = [], None, "G01"
    for line in open(path):
        line = line.strip()
        if line.startswith("G01"):
            mode = "G01"
            continue
        if line.startswith("G03"):
            mode = "G03"
        m = re.match(r"(?:G0[13])?X(-?\d+)Y(-?\d+)(?:I(-?\d+)J(-?\d+))?D0([12])\*", line)
        if not m:
            continue
        p = (int(m[1]) / 1e5, int(m[2]) / 1e5)
        if m[5] == "2":
            cur = p
            continue
        if mode == "G03" and m[3] is not None:
            segs.append(("A", cur, p, (cur[0] + int(m[3]) / 1e5, cur[1] + int(m[4]) / 1e5)))
        else:
            segs.append(("L", cur, p))
        cur = p
    return snap_endpoints(segs)


def snap_endpoints(segs, tol=0.2):
    """EasyEDA leaves gaps of a few hundredths of a mm between outline pieces.
    Move endpoints that lie within tol of each other onto their mean."""
    ends = [p for s in segs for p in (s[1], s[2])]
    groups = []
    for p in ends:
        for g in groups:
            if math.hypot(p[0] - g[0][0], p[1] - g[0][1]) < tol:
                g.append(p)
                break
        else:
            groups.append([p])
    where = {}
    for g in groups:
        m = (sum(q[0] for q in g) / len(g), sum(q[1] for q in g) / len(g))
        for q in g:
            where[q] = m
    return [(s[0], where[s[1]], where[s[2]]) + tuple(s[3:]) for s in segs]


def drill_holes(path):
    holes, tools, t = [], {}, None
    for line in open(path):
        line = line.strip()
        m = re.match(r"T(\d+)C([\d.]+)", line)
        if m:
            tools[m[1]] = float(m[2])
            continue
        m = re.match(r"T(\d+)$", line)
        if m:
            t = m[1]
            continue
        m = re.match(r"X(-?\d+)Y(-?\d+)", line)
        if m and t:
            holes.append((int(m[1]) / 1e3, int(m[2]) / 1e3, tools[t]))
    return holes


def sfm_frame():
    """Gerber -> board transform: module bbox centre to (CX, CY), Y flipped."""
    segs = gerber_outline(os.path.join(SFM, "Gerber/Gerber_BoardOutlineLayer.GKO"))
    pts = []
    for s in segs:
        if s[0] == "L":
            pts += [s[1], s[2]]
        else:
            _, p0, p1, c = s
            r = math.hypot(p0[0] - c[0], p0[1] - c[1])
            a0 = math.atan2(p0[1] - c[1], p0[0] - c[0])
            a1 = math.atan2(p1[1] - c[1], p1[0] - c[0])
            while a1 <= a0:
                a1 += 2 * math.pi
            pts += [(c[0] + r * math.cos(a0 + (a1 - a0) * k / 64), c[1] + r * math.sin(a0 + (a1 - a0) * k / 64))
                    for k in range(65)]
    gx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    gy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    return segs, (lambda x, y: (CX + x - gx, CY - (y - gy)))


def build_simplefoc():
    b = new_board(1.6)
    segs, T = sfm_frame()
    for s in segs:
        if s[0] == "L":
            edge_line(b, *T(*s[1]), *T(*s[2]))
        else:
            _, p0, p1, c = s
            r = math.hypot(p0[0] - c[0], p0[1] - c[1])
            a0 = math.atan2(p0[1] - c[1], p0[0] - c[0])
            a1 = math.atan2(p1[1] - c[1], p1[0] - c[0])
            while a1 <= a0:
                a1 += 2 * math.pi
            am = (a0 + a1) / 2
            edge_arc(b, T(*p0), T(c[0] + r * math.cos(am), c[1] + r * math.sin(am)), T(*p1))
    holes = drill_holes(os.path.join(SFM, "Gerber/Drill_PTH_Through.DRL"))
    for x, y, d in holes:
        if d >= 1.9:
            npth(b, *T(x, y), d)
    hdr = [T(x, y) for x, y, d in holes if abs(d - 1.101) < 0.01 and x < 12]
    pwr = [T(x, y) for x, y, d in holes if abs(d - 1.101) < 0.01 and x > 12]
    mot = [T(x, y) for x, y, d in holes if abs(d - 1.021) < 0.01]
    header_on_grid(b, "PinHeader_2x05_P2.54mm_Vertical", "H1", hdr)
    header_on_grid(b, "PinHeader_1x03_P2.54mm_Vertical", "P1", mot)
    for i, p in enumerate(pwr):
        header_on_grid(b, "PinHeader_1x01_P2.54mm_Vertical", f"PWR{i + 1}", [p])

    # Top-side parts from the pick-and-place file (EasyEDA rotation, CCW).
    lib = {
        "C0603": ("Capacitor_SMD", "C_0603_1608Metric", 0),
        "R0603": ("Resistor_SMD", "R_0603_1608Metric", 0),
        "LED0603-R-RD": ("LED_SMD", "LED_0603_1608Metric", 0),
        "CAP-SMD_BD6.3-L6.6-W6.6-FD": ("Capacitor_SMD", "CP_Elec_6.3x7.7", 0),
        # EasyEDA draws the HTSSOP with its pin rows horizontal at 0 degrees.
        "HTSSOP-28_L9.8-W4.5-P0.65-LS6.6-BL-EP": ("Package_SO", "HTSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP3.4x9.5mm", 90),
    }
    pnp = os.path.join(SFM, "Pick and Place/PickAndPlace_simplefocmini_2022-04-20.csv")
    raw = open(pnp, "rb").read()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8")
    for row in csv.DictReader(text.splitlines(), delimiter="\t"):
        fpname = row["Footprint"]
        if fpname not in lib:
            continue                              # headers and terminal are handled above
        l, n, extra = lib[fpname]
        x, y = float(row["Mid X"].rstrip("m")), float(row["Mid Y"].rstrip("m"))
        part(b, l, n, row["Designator"], *T(x, y), float(row["Rotation"]) + extra)
    save(b, "simplefoc_mini_v1")


# --------------------------------------------------------------------------
# MT3608 boost module, 37.2 x 17.3 mm (components101 drawing). Approximate.
MT_W, MT_H = 37.21, 17.27
MT_PADS = {"VIN-": (-15.6, -4.5), "VIN+": (-15.6, 3.4), "VOUT-": (15.6, -4.5), "VOUT+": (15.6, 3.4)}


def build_mt3608():
    b = new_board(1.2)
    edge_rounded_rect(b, MT_W, MT_H, 1.0)
    for name, (x, y) in MT_PADS.items():
        header_on_grid(b, "PinHeader_1x01_P2.54mm_Vertical", name, [(CX + x, CY + y)])
    part(b, "Package_TO_SOT_SMD", "SOT-23-6", "U1", CX - 6.5, CY - 5.6, 90)
    part(b, "Inductor_SMD", "L_Changjiang_FNR6045S", "L1", CX - 5.5, CY + 2.3)
    part(b, "Diode_SMD", "D_SMA", "D1", CX + 6.1, CY + 6.0)
    part(b, "Capacitor_SMD", "C_1206_3216Metric", "C1", CX - 11.0, CY - 4.2, 90)
    part(b, "Capacitor_SMD", "C_1206_3216Metric", "C2", CX - 1.6, CY - 4.6, 90)
    part(b, "Resistor_SMD", "R_0603_1608Metric", "R1", CX + 0.9, CY - 6.4, 90)
    part(b, "Potentiometer_THT", "Potentiometer_Bourns_3296W_Vertical", "RV1", CX + 4.2, CY - 3.3)
    save(b, "mt3608_module")


if __name__ == "__main__":
    OUT = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    build_weact()
    build_simplefoc()
    build_mt3608()
