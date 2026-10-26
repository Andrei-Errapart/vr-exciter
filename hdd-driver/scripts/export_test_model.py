"""Make the fit-test variant of hdd-driver.kicad_pcb (run by export-test-model).

The copy keeps the board outline, mounting holes and all drilled holes, but
replaces the copper pads of the HDD spring-contact footprint with through-slots
of the same size and angle. Printed and screwed onto the drive, the slots show
whether the motor springs land where the pads will be.

    export_test_model.py IN.kicad_pcb OUT.kicad_pcb [--thickness MM] [--slot-width MM]
"""
import argparse
import math

import pcbnew


def stadium(board, centre, angle_deg, width, length):
    """Edge.Cuts stadium (slot) centred on centre, long axis = pad local Y."""
    a = math.radians(angle_deg)
    u = (math.sin(a), math.cos(a))          # pad local +Y on the board (KiCad: CCW, Y down)
    n = (u[1], -u[0])
    r = width / 2
    h = max(length / 2 - r, 0)
    cx, cy = centre

    def pt(s, t):
        return pcbnew.VECTOR2I_MM(cx + u[0] * s + n[0] * t, cy + u[1] * s + n[1] * t)

    def add(shape):
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetWidth(pcbnew.FromMM(0.05))
        board.Add(shape)

    for t in (-r, r):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(-h, t))
        s.SetEnd(pt(h, t))
        add(s)
    for sgn in (-1, 1):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(pt(sgn * h, -r), pt(sgn * (h + r), 0), pt(sgn * h, r))
        add(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--thickness", type=float, default=None)
    ap.add_argument("--slot-width", type=float, default=None)
    args = ap.parse_args()

    board = pcbnew.LoadBoard(args.src)
    if args.thickness:
        board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(args.thickness))

    found = 0
    for fp in board.GetFootprints():
        if not str(fp.GetFPID().GetLibItemName()).startswith("HDD_SpringContacts"):
            continue
        for pad in list(fp.Pads()):
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue                       # keep the screw hole
            pos = pad.GetPosition()
            size = pad.GetSize(pcbnew.B_Cu) if hasattr(pad, "GetSize") else pad.GetSize()
            w = args.slot_width or pcbnew.ToMM(size.x)
            stadium(board, (pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)),
                    pad.GetOrientation().AsDegrees(), w, pcbnew.ToMM(size.y))
            fp.Remove(pad)
            found += 1
    if not found:
        raise SystemExit("no HDD_SpringContacts pads found")
    board.Save(args.dst)
    print(f"{found} contact pads replaced by slots -> {args.dst}")


if __name__ == "__main__":
    main()
