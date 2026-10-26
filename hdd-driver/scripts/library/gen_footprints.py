"""Generate the project footprints in lib/hdd-driver.pretty.

Run with KiCad's bundled Python:

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
        scripts/library/gen_footprints.py

The footprints were generated once with this script and may since have been
edited in KiCad; rerunning it overwrites them.

Footprints
- WeAct_STM32G474_CoreBoard_Socketed: two 2x12 female sockets on WeAct's
  25.4 mm grid. Pad "P1.n" = header P1 pin n, pad "P2.n" = header P2 pin n.
  Origin = module centre.
- SimpleFOC_Mini_v1.0_Socketed: 2x5 logic header (pads 1-10 = module H1 pins),
  "+" (11), "-" (12), M1 (13), M2 (14), M3 (15). Positions from the
  upstream v1.0 drill file. Origin = module centre.
- MT3608_Boost_Module: VIN+ (1), VIN- (2), VOUT+ (3), VOUT- (4) after the
  components101 drawing. Check against the actual module.
- HDD_SpringContacts_3P_P2.0mm: the drive's 3 spring contacts as SMD pads on
  B.Cu, plus the M2 screw of the contact block (pad 4). Origin = that screw.
  Pad positions were measured from a rectified photo (+-0.5 mm).
- MountingHole_2.4mm_M2_Pad: M2 clearance hole, plated, 4.2 mm pad.
- MountingHole_3.2mm_M3_Pad: M3 hole, plated, 6.4 mm pad (corner holes for
  feet or spacers).

Each socketed module footprint carries the socket models and the module model
raised to sit on the sockets: socket 8.5 mm + male header plastic 2.54 mm.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, "../.."))
sys.path.insert(0, os.path.join(PROJ, "scripts/module-models"))
import build_sources as bs  # noqa: E402  (SimpleFOC Gerber parsing)

LIB = os.path.join(PROJ, "lib/hdd-driver.pretty")
KICAD_FP = bs.KICAD_FP
MODULE_Z = 8.5 + 2.54          # module PCB underside above the carrier
IO = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)
BOARD = pcbnew.BOARD()


def mm(x, y):
    return pcbnew.VECTOR2I_MM(x, y)


def new_fp(name, descr, keywords, smd=False):
    fp = pcbnew.FOOTPRINT(BOARD)
    fp.SetFPID(pcbnew.LIB_ID("hdd-driver", name))
    fp.SetLibDescription(descr)
    fp.SetKeywords(keywords)
    fp.SetAttributes(pcbnew.FP_SMD if smd else pcbnew.FP_THROUGH_HOLE)
    fp.SetReference("REF**")
    fp.SetValue(name)
    return fp


def text_pos(fp, ref_xy, val_xy):
    fp.Reference().SetPosition(mm(*ref_xy))
    fp.Reference().SetLayer(pcbnew.F_SilkS)
    fp.Value().SetPosition(mm(*val_xy))
    fp.Value().SetLayer(pcbnew.F_Fab)


def line(fp, layer, x0, y0, x1, y1, w):
    s = pcbnew.PCB_SHAPE(fp)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(layer)
    s.SetStart(mm(x0, y0))
    s.SetEnd(mm(x1, y1))
    s.SetWidth(pcbnew.FromMM(w))
    fp.Add(s)


def rect(fp, layer, x0, y0, x1, y1, w):
    s = pcbnew.PCB_SHAPE(fp)
    s.SetShape(pcbnew.SHAPE_T_RECTANGLE)
    s.SetLayer(layer)
    s.SetStart(mm(x0, y0))
    s.SetEnd(mm(x1, y1))
    s.SetWidth(pcbnew.FromMM(w))
    fp.Add(s)


def circle(fp, layer, x, y, r, w):
    s = pcbnew.PCB_SHAPE(fp)
    s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetLayer(layer)
    s.SetCenter(mm(x, y))
    s.SetEnd(mm(x + r, y))
    s.SetWidth(pcbnew.FromMM(w))
    fp.Add(s)


def fab_text(fp, txt, x, y, size=1.0, layer=pcbnew.F_Fab):
    t = pcbnew.PCB_TEXT(fp)
    t.SetText(txt)
    t.SetLayer(layer)
    t.SetPosition(mm(x, y))
    t.SetTextSize(mm(size, size))
    t.SetTextThickness(pcbnew.FromMM(size * 0.15))
    if layer in (pcbnew.B_Fab, pcbnew.B_SilkS):
        t.SetMirrored(True)
    fp.Add(t)


def tht_pad(fp, num, x, y, drill=1.0, size=1.7, square=False):
    p = pcbnew.PAD(fp)
    p.SetNumber(str(num))
    p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    p.SetShape(pcbnew.PAD_SHAPE_RECTANGLE if square else pcbnew.PAD_SHAPE_CIRCLE)
    p.SetSize(mm(size, size))
    p.SetDrillSize(mm(drill, drill))
    p.SetLayerSet(pcbnew.PAD.PTHMask())
    p.SetPosition(mm(x, y))
    fp.Add(p)
    return p


def model(fp, path, x=0.0, y=0.0, z=0.0, rot=0.0):
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = path
    m.m_Offset = pcbnew.VECTOR3D(x, -y, z)       # model offsets are Y-up
    m.m_Rotation = pcbnew.VECTOR3D(0, 0, rot)
    fp.Models().push_back(m)


def stock_model_on_pads(fp, lib, name, pins):
    """Add the 3D model of a stock footprint so that its pads land on `pins`
    (footprint-local coordinates, any pin order)."""
    stock = pcbnew.FootprintLoad(os.path.join(KICAD_FP, lib + ".pretty"), name)
    sp = [(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)) for p in stock.Pads()]
    want = sorted((round(x, 2), round(y, 2)) for x, y in pins)
    wcx = sum(x for x, _ in pins) / len(pins)
    wcy = sum(y for _, y in pins) / len(pins)
    for rot in (0, 90, 180, 270):
        a = math.radians(rot)
        # KiCad rotation, CCW on screen with Y down
        rp = [(x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)) for x, y in sp]
        cx = sum(x for x, _ in rp) / len(rp)
        cy = sum(y for _, y in rp) / len(rp)
        dx, dy = wcx - cx, wcy - cy
        got = sorted((round(x + dx, 2), round(y + dy, 2)) for x, y in rp)
        if all(abs(g[0] - w[0]) < 0.02 and abs(g[1] - w[1]) < 0.02 for g, w in zip(got, want)):
            for m in stock.Models():
                # a 3D model's Z rotation turns the opposite way to a footprint rotation
                model(fp, m.m_Filename, dx, dy, 0.0, -rot)
            return
    sys.exit(f"{name} does not fit the given pins")


def courtyard(fp, x0, y0, x1, y1, layer=pcbnew.F_CrtYd):
    rect(fp, layer, x0, y0, x1, y1, 0.05)


def save(fp):
    IO.FootprintSave(LIB, fp)
    print("wrote", fp.GetFPID().GetLibItemName())


# --------------------------------------------------------------------------
def weact():
    name = "WeAct_STM32G474_CoreBoard_Socketed"
    fp = new_fp(name,
                "WeAct Studio STM32G474CEU6 Core Board (36.28x28.14 mm) on two 2x12 female sockets. "
                "Pad P1.n = header P1 pin n (VCC side), pad P2.n = header P2 pin n (3V3 side). "
                "USB-C on the left (-X), SWD header on the right (+X).",
                "WeAct STM32G474 STM32G474CEU6 core board module socket")
    w, h = bs.W_W, bs.W_H
    cols, rows = bs.weact_pins()
    p1 = {}
    p2 = {}
    for c, x in enumerate(cols):
        # P1 (bottom edge): odd pins outer row, even pins inner row
        p1[2 * c + 1] = (x, h / 2 - 1.37)
        p1[2 * c + 2] = (x, h / 2 - 1.37 - 2.54)
        # P2 (top edge): odd pins inner row, even pins outer row
        p2[2 * c + 1] = (x, -h / 2 + 1.37 + 2.54)
        p2[2 * c + 2] = (x, -h / 2 + 1.37)
    for n, (x, y) in p1.items():
        tht_pad(fp, f"P1.{n}", x, y, square=(n == 1))
    for n, (x, y) in p2.items():
        tht_pad(fp, f"P2.{n}", x, y, square=(n == 1))
    for layer, wd in ((pcbnew.F_SilkS, 0.12), (pcbnew.F_Fab, 0.1)):
        rect(fp, layer, -w / 2, -h / 2, w / 2, h / 2, wd)
    courtyard(fp, -w / 2 - 0.5, -h / 2 - 0.5, w / 2 + 0.5, h / 2 + 0.5)
    fab_text(fp, "USB-C", -w / 2 + 3.5, 0, 1.0, pcbnew.F_SilkS)
    fab_text(fp, "SWD", w / 2 - 2.0, 0, 0.8, pcbnew.F_SilkS)
    fab_text(fp, "P2 (3V3)", 0, -h / 2 + 5.5, 1.0)
    fab_text(fp, "P1 (VCC)", 0, h / 2 - 5.5, 1.0)
    fab_text(fp, "${REFERENCE}", 0, 0, 1.0)
    text_pos(fp, (0, -h / 2 - 1.2), (0, 2.0))
    sock = "Connector_PinSocket_2.54mm"
    stock_model_on_pads(fp, sock, "PinSocket_2x12_P2.54mm_Vertical", list(p1.values()))
    stock_model_on_pads(fp, sock, "PinSocket_2x12_P2.54mm_Vertical", list(p2.values()))
    model(fp, "${KIPRJMOD}/lib/3d/WeAct_STM32G474_CoreBoard.step", 0, 0, MODULE_Z)
    save(fp)


# --------------------------------------------------------------------------
SFM_H1 = {  # module H1 pin -> (gerber x, gerber y): from Drill_PTH_Through.DRL and the EasyEDA nets
    1: (9.017, -3.937), 3: (6.477, -3.937), 5: (3.937, -3.937), 7: (1.397, -3.937), 9: (-1.143, -3.937),
    2: (9.017, -6.477), 4: (6.477, -6.477), 6: (3.937, -6.477), 8: (1.397, -6.477), 10: (-1.143, -6.477),
}
SFM_OTHER = {11: (16.256, -12.700),   # "+"  VM
             12: (16.256, -7.747),    # "-"  GND
             13: (2.413, -21.590),    # M1 = OUT1
             14: (4.953, -21.590),    # M2 = OUT2
             15: (7.493, -21.590)}    # M3 = OUT3


def simplefoc():
    name = "SimpleFOC_Mini_v1.0_Socketed"
    fp = new_fp(name,
                "SimpleFOC Mini v1.0 (DRV8313) BLDC driver module, 26.1x21.0 mm, on female sockets. "
                "Pads 1-10 = module header H1 pins 1-10 (1 GND, 2 3V3, 3 IN1, 4 GND, 5 IN2, 6 nRT, 7 IN3, "
                "8 nSP, 9 EN, 10 nFT); 11 = + (VM); 12 = - (GND); 13-15 = M1-M3. "
                "Positions from the upstream v1.0 Gerber drill file.",
                "SimpleFOC Mini DRV8313 BLDC driver module socket")
    segs, T = bs.sfm_frame()

    def L(x, y):
        X, Y = T(x, y)
        return X - bs.CX, Y - bs.CY
    for n, p in SFM_H1.items():
        tht_pad(fp, n, *L(*p), square=(n == 1))
    tht_pad(fp, 11, *L(*SFM_OTHER[11]), drill=1.1, size=2.0)
    tht_pad(fp, 12, *L(*SFM_OTHER[12]), drill=1.1, size=2.0)
    for n in (13, 14, 15):
        tht_pad(fp, n, *L(*SFM_OTHER[n]), square=(n == 15))
    # outline (F.Fab, silk) from the Gerber outline
    for s in segs:
        if s[0] == "L":
            for layer, wd in ((pcbnew.F_Fab, 0.1), (pcbnew.F_SilkS, 0.12)):
                line(fp, layer, *L(*s[1]), *L(*s[2]), wd)
        else:
            _, p0, p1, c = s
            r = math.hypot(p0[0] - c[0], p0[1] - c[1])
            a0 = math.atan2(p0[1] - c[1], p0[0] - c[0])
            a1 = math.atan2(p1[1] - c[1], p1[0] - c[0])
            while a1 <= a0:
                a1 += 2 * math.pi
            am = (a0 + a1) / 2
            for layer, wd in ((pcbnew.F_Fab, 0.1), (pcbnew.F_SilkS, 0.12)):
                a = pcbnew.PCB_SHAPE(fp)
                a.SetShape(pcbnew.SHAPE_T_ARC)
                a.SetLayer(layer)
                a.SetArcGeometry(mm(*L(*p0)), mm(*L(c[0] + r * math.cos(am), c[1] + r * math.sin(am))), mm(*L(*p1)))
                a.SetWidth(pcbnew.FromMM(wd))
                fp.Add(a)
    # the module's own M2 mounting holes, for reference only (not drilled)
    for x, y, d in bs.drill_holes(os.path.join(bs.SFM, "Gerber/Drill_PTH_Through.DRL")):
        if d >= 1.9:
            circle(fp, pcbnew.F_Fab, *L(x, y), d / 2, 0.1)
    courtyard(fp, -13.6, -11.0, 13.6, 11.0)
    for n, txt in ((11, "+"), (12, "-"), (13, "M1"), (14, "M2"), (15, "M3")):
        x, y = L(*SFM_OTHER[n])
        fab_text(fp, txt, x + (2.0 if n in (11, 12) else 0), y - (1.8 if n >= 13 else 0), 0.8)
    for n, txt in ((9, "EN"), (7, "IN3"), (5, "IN2"), (3, "IN1"), (1, "GND"),
                   (10, "nFT"), (8, "nSP"), (6, "nRT"), (4, "GND"), (2, "3V3")):
        x, y = L(*SFM_H1[n])
        fab_text(fp, txt, x, y + (-1.6 if n % 2 else 1.6), 0.6)
    fab_text(fp, "${REFERENCE}", 0, 1.5, 1.0)
    text_pos(fp, (0, -11.8), (0, 4.0))
    sock = "Connector_PinSocket_2.54mm"
    stock_model_on_pads(fp, sock, "PinSocket_2x05_P2.54mm_Vertical", [L(*p) for p in SFM_H1.values()])
    stock_model_on_pads(fp, sock, "PinSocket_1x03_P2.54mm_Vertical", [L(*SFM_OTHER[n]) for n in (13, 14, 15)])
    stock_model_on_pads(fp, sock, "PinSocket_1x01_P2.54mm_Vertical", [L(*SFM_OTHER[11])])
    stock_model_on_pads(fp, sock, "PinSocket_1x01_P2.54mm_Vertical", [L(*SFM_OTHER[12])])
    model(fp, "${KIPRJMOD}/lib/3d/SimpleFOC_Mini_v1.0.step", 0, 0, MODULE_Z)
    save(fp)


# --------------------------------------------------------------------------
def mt3608():
    name = "MT3608_Boost_Module"
    fp = new_fp(name,
                "MT3608 2 A boost module, 37.2x17.3 mm (components101 drawing), soldered on pin headers. "
                "Pads: 1 VIN+, 2 VIN-, 3 VOUT+, 4 VOUT-. Pad positions vary between vendors: check them "
                "against the actual module before ordering.",
                "MT3608 boost step-up module")
    pads = {1: bs.MT_PADS["VIN+"], 2: bs.MT_PADS["VIN-"], 3: bs.MT_PADS["VOUT+"], 4: bs.MT_PADS["VOUT-"]}
    for n, (x, y) in pads.items():
        tht_pad(fp, n, x, y, drill=1.0, size=2.0, square=(n == 1))
    w, h = bs.MT_W, bs.MT_H
    for layer, wd in ((pcbnew.F_SilkS, 0.12), (pcbnew.F_Fab, 0.1)):
        rect(fp, layer, -w / 2, -h / 2, w / 2, h / 2, wd)
    courtyard(fp, -w / 2 - 0.5, -h / 2 - 0.5, w / 2 + 0.5, h / 2 + 0.5)
    for n, txt in ((1, "VIN+"), (2, "VIN-"), (3, "VOUT+"), (4, "VOUT-")):
        x, y = pads[n]
        fab_text(fp, txt, x + (3.2 if x < 0 else -3.4), y, 0.8, pcbnew.F_SilkS)
    fab_text(fp, "${REFERENCE}", 0, 0, 1.0)
    text_pos(fp, (0, -h / 2 - 1.2), (0, 2.0))
    model(fp, "${KIPRJMOD}/lib/3d/MT3608_Module.step", 0, 0, 2.54)
    save(fp)


# --------------------------------------------------------------------------
# Spring contacts, in the frame of the contact block: origin = M2 screw
# (hole 7), +Y along the springs towards their free ends (towards the motor).
CONTACT_X = (-4.13, -2.13, -0.13)   # 2.0 mm pitch; measured -4.19 / -2.13 / -0.08
CONTACT_Y = 6.0                     # spring tip (dimple) distance from the screw axis
CONTACT_PAD = (1.4, 4.0)            # pad width x length (along the spring)


def springs():
    name = "HDD_SpringContacts_3P_P2.0mm"
    fp = new_fp(name,
                "Motor spring contacts of a 3.5in HDD (3 springs, 2.0 mm pitch) as gold pads on B.Cu, "
                "with the M2 screw of the contact block (pad 4). Origin = screw axis; springs run along +Y. "
                "Measured from a photo, +-0.5 mm: verify with scripts/export-test-model.",
                "HDD spindle motor spring contact pads")
    for i, x in enumerate(CONTACT_X):
        p = pcbnew.PAD(fp)
        p.SetNumber(str(i + 1))
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
        p.SetRoundRectRadiusRatio(0.25)
        p.SetSize(mm(*CONTACT_PAD))
        ls = pcbnew.LSET()
        ls.AddLayer(pcbnew.B_Cu)
        ls.AddLayer(pcbnew.B_Mask)
        p.SetLayerSet(ls)
        p.SetPosition(mm(x, CONTACT_Y))
        fp.Add(p)
    tht_pad(fp, 4, 0, 0, drill=2.4, size=4.2)
    # contact block outline on the drive side (approximate), and the screw head
    rect(fp, pcbnew.B_Fab, -5.6, -2.6, 1.6, 9.5, 0.1)
    circle(fp, pcbnew.F_Fab, 0, 0, 2.0, 0.1)
    for i, x in enumerate(CONTACT_X):
        fab_text(fp, str(i + 1), x, CONTACT_Y + 3.0, 0.8, pcbnew.B_Fab)
        fab_text(fp, str(i + 1), x, CONTACT_Y + 3.0, 0.8, pcbnew.B_SilkS)
    courtyard(fp, -5.9, -2.9, 2.4, 9.8, pcbnew.B_CrtYd)
    circle(fp, pcbnew.F_CrtYd, 0, 0, 2.6, 0.05)
    fab_text(fp, "${REFERENCE}", -2.1, 11.0, 0.8, pcbnew.B_Fab)
    fp.Reference().SetLayer(pcbnew.B_SilkS)
    fp.Reference().SetMirrored(True)
    fp.Reference().SetPosition(mm(-2.1, -3.8))
    fp.Value().SetLayer(pcbnew.B_Fab)
    fp.Value().SetMirrored(True)
    fp.Value().SetPosition(mm(-2.1, 12.5))
    save(fp)


def mounting_hole(name, descr, keywords, drill, pad, crtyd_r, head_r):
    fp = new_fp(name, descr, keywords)
    tht_pad(fp, 1, 0, 0, drill=drill, size=pad)
    circle(fp, pcbnew.F_CrtYd, 0, 0, crtyd_r, 0.05)
    circle(fp, pcbnew.B_CrtYd, 0, 0, crtyd_r, 0.05)
    circle(fp, pcbnew.Cmts_User, 0, 0, head_r, 0.12)    # screw head
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    text_pos(fp, (0, -crtyd_r - 0.8), (0, crtyd_r + 0.8))
    save(fp)


def mounting_holes():
    mounting_hole("MountingHole_2.4mm_M2_Pad",
                  "M2 mounting hole, 2.4 mm clearance (ISO 273 medium), plated, 4.2 mm pad",
                  "mounting hole M2", drill=2.4, pad=4.2, crtyd_r=2.6, head_r=1.9)
    mounting_hole("MountingHole_3.2mm_M3_Pad",
                  "M3 mounting hole, 3.2 mm clearance (ISO 273 fine), plated, 6.4 mm pad",
                  "mounting hole M3", drill=3.2, pad=6.4, crtyd_r=3.45, head_r=2.75)


if __name__ == "__main__":
    os.makedirs(LIB, exist_ok=True)
    weact()
    simplefoc()
    mt3608()
    springs()
    mounting_holes()
