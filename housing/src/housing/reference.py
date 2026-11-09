"""Reference solids for the fit checks, and the driver board from its KiCad export.

Everything is in the drive frame (see params), in its position of use.
"""
import math
import re
from functools import reduce
from pathlib import Path

from build123d import (
    Align,
    BoundBox,
    Box,
    Compound,
    Cylinder,
    Location,
    Part,
    Pos,
    RegularPolygon,
    Rot,
    Shape,
    extrude,
    import_step,
)

from housing import params as P

ROOT = Path(__file__).resolve().parents[3]          # housing/src/housing/ -> repo root
SOURCE_PCB = ROOT / "hdd-driver/hdd-driver.kicad_pcb"
BOARD_STEP = ROOT / "hdd-driver/build/test-model/test-assembly.step"
BOARD_TEST_PCB = ROOT / "hdd-driver/build/test-model/hdd-driver-test.kicad_pcb"

KICAD_ORIGIN = (150.0, 40.0)                         # drive frame = KiCad PCB coordinates minus this
CHECKED_REFS = ("J1", "J3", "U1", "U2", "U3")
STALE_MESSAGE = "board export is stale or missing; run hdd-driver/scripts/export-test-model"

# KiCad's STEP export: Y flipped (STEP y = -KiCad y), B.Cu at z 0, parts on top at z > 0.
# In use B.Cu lies on the drive and the parts hang down, so turn it 180 deg about X:
# (x, y, z) -> (x, -y, -z).
BOARD_POSE = Rot(180, 0, 0)

_CENTRE_MIN = (Align.CENTER, Align.CENTER, Align.MIN)


def drive_box() -> Part:
    """The drive's envelope: X ±DRIVE_X_HALF, Y 0…DRIVE_LEN, Z 0…DRIVE_TOP_Z."""
    return Box(2 * P.DRIVE_X_HALF, P.DRIVE_LEN, P.DRIVE_TOP_Z,
               align=(Align.CENTER, Align.MIN, Align.MIN))


def disc_envelope() -> Part:
    """The disc at its extremes: r DISC_R about the spindle, lowest underside to highest top."""
    return Pos(*P.SPINDLE, P.DISC_UNDER_Z[0]) * Cylinder(
        P.DISC_R, P.DISC_TOP_Z[1] - P.DISC_UNDER_Z[0], align=_CENTRE_MIN)


def _at_phi(shape: Shape, phi: float) -> Shape:
    """Place a shape built with +X radial and +Y tangential about the spindle at angle phi."""
    return Pos(*P.SPINDLE) * Rot(0, 0, -phi) * shape


def coil_b(bar_top_z: float) -> Part:
    """Pickup coil B: its bar flat on the tower face at r B_FACE_R, the body pointing outwards."""
    bar_l, bar_t, bar_h = P.B_BAR
    depth, width, height = P.B_BODY
    bar = Pos(P.B_FACE_R + bar_t / 2, 0, bar_top_z - bar_h / 2) * Box(bar_t, bar_l, bar_h)
    body = Pos(P.B_FACE_R + depth / 2, 0, bar_top_z - height / 2) * Box(depth, width, height)
    return Part(_at_phi(bar + body, P.B_PHI))


def sensor_c(gap: float) -> Part:
    """Sensor C with its tip `gap` above the highest disc top, and its lock nut on the plate."""
    x, y = P.pol(P.MAGNET_R, P.C_PHI)
    shank = Pos(x, y, P.DISC_TOP_Z[1] + gap) * Cylinder(
        P.C_SENSOR_D / 2, P.C_SENSOR_LEN, align=_CENTRE_MIN)
    nut = Pos(x, y, P.PLATE_Z[1]) * extrude(
        RegularPolygon(P.C_NUT_AF / 2, 6, major_radius=False), P.C_NUT_H)
    return Part(shank + nut)


def usb_plug_probe() -> Part:
    """A USB-C plug overmold on its way in: USB_PLUG across, along Y over USB_PLUG_Y."""
    (w, h), (y0, y1) = P.USB_PLUG, P.USB_PLUG_Y
    x, z = P.USB_CENTRE_XZ
    return Pos(x, (y0 + y1) / 2, z) * Box(w, y1 - y0, h)


_FOOTPRINT = re.compile(r'\(footprint\s+"')
_AT = re.compile(r"\(at\s+(-?[\d.]+)\s+(-?[\d.]+)(?:\s+(-?[\d.]+))?\s*\)")
_REFERENCE = re.compile(r'\(property\s+"Reference"\s+"([^"]+)"')


def footprint_positions(pcb_text: str) -> dict[str, tuple[float, float, float]]:
    """Reference -> (X, Y, rotation) of every footprint in a .kicad_pcb, in the drive frame.

    A footprint's own (at …) is the first one in its block, before its properties.
    """
    positions = {}
    for block in _FOOTPRINT.split(pcb_text)[1:]:
        at, ref = _AT.search(block), _REFERENCE.search(block)
        if at is None or ref is None:
            continue
        x, y, rot = at.groups()
        positions[ref.group(1)] = (float(x) - KICAD_ORIGIN[0], float(y) - KICAD_ORIGIN[1],
                                   float(rot or 0.0))
    return positions


def _same_place(a: tuple[float, float, float], b: tuple[float, float, float]) -> bool:
    turn = (a[2] - b[2] + 180.0) % 360.0 - 180.0
    return math.dist(a[:2], b[:2]) < 1e-3 and abs(turn) < 1e-3


def check_board_export() -> None:
    """Raise RuntimeError unless the 3D export exists and matches the current PCB."""
    if not BOARD_STEP.is_file() or not BOARD_TEST_PCB.is_file():
        raise RuntimeError(STALE_MESSAGE)
    current = footprint_positions(SOURCE_PCB.read_text())
    exported = footprint_positions(BOARD_TEST_PCB.read_text())
    for ref in CHECKED_REFS:
        if ref not in current or ref not in exported or not _same_place(current[ref], exported[ref]):
            raise RuntimeError(STALE_MESSAGE)


def load_board() -> Compound:
    """The board with its modules from BOARD_STEP, in its position of use."""
    check_board_export()
    return import_step(BOARD_STEP).move(BOARD_POSE)


def named_bboxes(step_path: Path) -> dict[str, BoundBox]:
    """Label -> bounding box of every node in a STEP assembly, posed like load_board().

    Labels are the STEP product names (model names, or the reference designators
    inside a vendor model, e.g. the WeAct board's own "J1" is its USB-C). A label
    used by several nodes maps to the box round all of them.
    """
    boxes: dict[str, BoundBox] = {}

    def walk(node: Shape, parent: Location) -> BoundBox | None:
        if node.is_null:
            return None
        loc = parent * node.location
        if node.children:
            child_boxes = [b for b in (walk(c, loc) for c in node.children) if b is not None]
            bb = reduce(BoundBox.add, child_boxes) if child_boxes else None
        else:
            # TopoDS Located() shares the geometry; build123d's located() would deep-copy
            # the whole assembly tree for every leaf.
            bb = BoundBox(node.wrapped.Located(loc.wrapped))
            if bb.wrapped is None:              # a leaf without geometry
                bb = None
        if bb is not None:
            boxes[node.label] = boxes[node.label].add(bb) if node.label in boxes else bb
        return bb

    walk(import_step(step_path), BOARD_POSE)
    return boxes
