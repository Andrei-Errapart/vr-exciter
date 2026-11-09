import math

import pytest
from build123d import Box, Compound, Cylinder, Pos, Vector, extrude

from housing import joint
from housing import params as P
from housing import reference
from housing.base import floor_slot_centres
from housing.checks import min_clearance, overlap_volume

END_WALL_Y = -(P.TRAY_END_GAP + P.TRAY_WALL / 2)                 # middle of the tray's end wall
RIGHT_WALL_X = P.DRIVE_X_HALF + P.TRAY_GAP + P.TRAY_WALL / 2      # middle of its right side wall


def test_base_fits_bed(base):
    s = base.bounding_box().size
    assert s.X <= P.BED - 2 * P.BED_MARGIN and s.Y <= P.BED - 2 * P.BED_MARGIN
    assert base.bounding_box().min.Z == pytest.approx(P.FLOOR_UNDER_Z, abs=1e-3)


def test_base_is_one_valid_solid(base):
    assert base.is_valid and len(base.solids()) == 1


def test_base_clears_drive_and_touches_only_at_bosses(base, drive):
    assert overlap_volume(base, drive) == pytest.approx(0, abs=1e-3)
    for x, y in P.HOLES:
        assert overlap_volume(base, Pos(x, y, -0.05) * Box(9, 9, 0.1)) > 0      # boss reaches Z 0
        assert not base.is_inside(Vector(x, y, -10))                              # bore open from below


def test_seat_is_top_of_wall(base):
    ring = Pos(*P.SPINDLE, 0.05) * (Cylinder(117.5, 0.1) - Cylinder(112.5, 0.1))
    assert overlap_volume(base, ring) == pytest.approx(0, abs=1e-3)
    seat = Pos(*P.pol(114, 200), -0.05) * Box(1, 1, 0.1)
    assert overlap_volume(base, seat) > 0


def test_lip_zone_is_free(base):
    """Nothing of the base where the cover's lip comes down outside r 115, flat included."""
    h = P.SEAT_Z - P.BASE_OUTER_TOP_Z - 0.05
    outer = extrude(P.drum_outline(P.DRUM_R_IN + P.DRUM_WALL + 0.5, P.FLAT_Y_IN - P.DRUM_WALL - 0.5), h)
    inner = extrude(P.drum_outline(P.DRUM_R_MID, P.FLAT_Y_IN - P.DRUM_WALL / 2), h)
    zone = Pos(0, 0, P.BASE_OUTER_TOP_Z + 0.05) * (outer - inner)
    assert overlap_volume(base, zone) == pytest.approx(0, abs=1e-3)


def test_cover_tabs_and_key_fit_the_base(base):
    for phi in P.TAB_ANGLES:
        assert overlap_volume(base, joint.tab_solid(phi)) == pytest.approx(0, abs=1e-3)
    assert overlap_volume(base, joint.key_tab()) == pytest.approx(0, abs=1e-3)


def test_tab_solid_shape():
    tab = joint.tab_solid(P.TAB_ANGLES[1])
    bb = tab.bounding_box()
    assert (bb.min.Z, bb.max.Z) == pytest.approx((P.TAB_BOTTOM_Z, P.TAB_THICK_TOP_Z), abs=1e-3)

    def at(r, z, t=0.0):
        return Vector(*P.pol(r, P.TAB_ANGLES[1], t), z)

    assert not tab.is_inside(at(P.TAB_R_OUT - 1, P.SCREW_Z))                      # screw hole
    assert tab.is_inside(at(P.TAB_R_OUT - 1, P.SCREW_Z - P.M4_CLEAR_D / 2 - 0.5))
    beside_hole = P.TAB_WIDTH / 4
    assert tab.is_inside(at(P.DRUM_R_MID + 0.5, P.LIP_BOTTOM_Z - 0.5, beside_hole))     # lip continuation
    assert not tab.is_inside(at(P.DRUM_R_MID + 0.5, P.LIP_BOTTOM_Z + 0.5, beside_hole))  # (the lip is the cover's)
    assert tab.is_inside(at(P.TAB_R_OUT - 1.8, P.TAB_THICK_TOP_Z - 0.5))           # 45° chamfer
    assert not tab.is_inside(at(P.TAB_R_OUT - 0.2, P.TAB_THICK_TOP_Z - 0.5))
    assert tab.is_inside(at(P.TAB_R_OUT - 1, P.TAB_BOTTOM_Z + 1, P.TAB_WIDTH / 2 - 0.2))
    assert not tab.is_inside(at(P.TAB_R_OUT - 1, P.TAB_BOTTOM_Z + 1, P.TAB_WIDTH / 2 + 0.2))


def test_insert_bosses_and_holes(base):
    for phi in P.TAB_ANGLES:
        def at(r, z):
            return Vector(*P.pol(r, phi), z)

        assert not base.is_inside(at(P.DRUM_R_MID + 1.0, P.SCREW_Z))                      # recess
        assert not base.is_inside(at(P.DRUM_R_MID - 0.5, P.SCREW_Z))                      # hole mouth
        assert not base.is_inside(at(P.DRUM_R_MID - P.M4_INSERT_HOLE_DEPTH + 0.3, P.SCREW_Z))
        assert base.is_inside(at(P.DRUM_R_MID - P.M4_INSERT_HOLE_DEPTH - 0.3, P.SCREW_Z))  # blind
        assert base.is_inside(at(P.INSERT_BOSS_R_IN + 1, P.SCREW_Z + P.M4_INSERT_HOLE_D / 2 + 1))


def test_key_notch(base):
    x, y = P.pol(P.DRUM_R_IN + 1, P.KEY_ANGLE)
    assert not base.is_inside(Vector(x, y, P.SEAT_Z - P.KEY_DEPTH + 0.3))
    assert base.is_inside(Vector(x, y, P.SEAT_Z - P.KEY_DEPTH - 0.3))
    for side in (-1, 1):
        x, y = P.pol(P.DRUM_R_IN + 1, P.KEY_ANGLE, side * (P.KEY_WIDTH / 2 + 0.5))
        assert base.is_inside(Vector(x, y, P.SEAT_Z - 1.0))


def test_feet_insert_holes(base):
    for phi in P.FEET_ANGLES:
        x, y = P.pol(P.FEET_R, phi)
        assert not base.is_inside(Vector(x, y, P.FLOOR_UNDER_Z + 0.5)) and base.is_inside(
            Vector(x + 3.5, y, P.FLOOR_UNDER_Z + 0.5))
        assert not base.is_inside(Vector(x, y, P.FLOOR_UNDER_Z + P.M3_INSERT_HOLE_DEPTH - 0.3))
        assert base.is_inside(Vector(x, y, P.FLOOR_UNDER_Z + P.M3_INSERT_HOLE_DEPTH + 0.5))   # capped


def test_usb_tunnel_open_and_walled(base):
    assert overlap_volume(base, reference.usb_plug_probe()) == pytest.approx(0, abs=1e-3)
    x, z = P.USB_CENTRE_XZ
    assert base.is_inside(Vector(x - 8.0, -6.0, z)) and base.is_inside(Vector(x + 8.0, -6.0, z))


def test_usb_tunnel_sealed_top_and_bottom(base):
    x, z = P.USB_CENTRE_XZ
    half_h = P.USB_WINDOW[1] / 2 + P.USB_TUNNEL_WALL / 2
    assert base.is_inside(Vector(x, -6.0, z - half_h)) and base.is_inside(Vector(x, -6.0, z + half_h))
    assert not base.is_inside(Vector(x, P.FLAT_Y_IN - P.DRUM_WALL + 0.2, z + P.USB_FLARE[1] / 2 - 0.3))  # flare


def test_psu_slot_width(base):
    assert not base.is_inside(Vector(P.PSU_SLOT_X, -12, P.J1_WIRE_Z))
    assert base.is_inside(Vector(P.PSU_SLOT_X - 3.6, -12, P.J1_WIRE_Z))
    assert base.is_inside(Vector(P.PSU_SLOT_X + 3.6, -12, P.J1_WIRE_Z))


def test_psu_and_j1_slot_depths(base):
    assert not base.is_inside(Vector(P.PSU_SLOT_X, -12, P.PSU_SLOT_BOTTOM_Z + 0.3))
    assert base.is_inside(Vector(P.PSU_SLOT_X, -12, P.PSU_SLOT_BOTTOM_Z - 0.3))
    x = sum(P.J1_SLOT_X) / 2
    assert not base.is_inside(Vector(x, END_WALL_Y, P.TRAY_WALL_TOP_Z - 0.3))      # open from the top
    assert not base.is_inside(Vector(x, END_WALL_Y, P.J1_SLOT_BOTTOM_Z + 0.3))
    assert base.is_inside(Vector(x, END_WALL_Y, P.J1_SLOT_BOTTOM_Z - 0.3))


def test_end_wall_closed_at_j3(base):
    x, _, _ = reference.footprint_positions(reference.SOURCE_PCB.read_text())["J3"]
    probe = Pos(x + 1.27, END_WALL_Y, -5.5) * Box(12.0, P.TRAY_WALL - 0.2, 9.0)   # J3's span ± 3
    assert overlap_volume(base, probe) == pytest.approx(probe.volume, rel=1e-6)


def test_j3_cable_slot_in_right_wall(base):
    y = P.J3_CABLE_SLOT_Y
    assert P.CABLE_SLOT_W <= 6.0
    assert not base.is_inside(Vector(RIGHT_WALL_X, y, P.TRAY_WALL_TOP_Z - 0.3))
    assert not base.is_inside(Vector(RIGHT_WALL_X, y, P.J3_WIRE_Z))
    assert not base.is_inside(Vector(RIGHT_WALL_X, y, P.J3_SLOT_BOTTOM_Z + 0.3))
    assert base.is_inside(Vector(RIGHT_WALL_X, y, P.J3_SLOT_BOTTOM_Z - 0.3))
    assert base.is_inside(Vector(RIGHT_WALL_X, y - 3.05, P.J3_WIRE_Z))
    assert base.is_inside(Vector(RIGHT_WALL_X, y + 3.05, P.J3_WIRE_Z))


def test_j3_cable_path_is_clear(board):
    """A Ø4 cable from the right-wall slot, and its two Ø2 wires to J3's +Y entries, miss the board."""
    x_in = P.DRIVE_X_HALF + P.TRAY_GAP                                # inner face of the right wall
    pin1, _, _ = reference.footprint_positions(reference.SOURCE_PCB.read_text())["J3"]
    x_split, y = pin1 + 2.54 + 1.0, P.J3_CABLE_SLOT_Y
    cable = Pos((x_split + x_in) / 2, y, P.J3_WIRE_Z - 0.6) * Box(x_in - x_split, 4.0, 4.0)
    j3_face_y = 7.81                                                   # 0.1 off J3's +Y face
    wires = Pos(pin1 + 1.27, (j3_face_y + y + 2.0) / 2, P.J3_WIRE_Z) * Box(4.6, y + 2.0 - j3_face_y, 2.0)
    path = cable + wires
    pb = path.bounding_box()

    def near_path(bb, margin=1.0):                     # a boolean against the whole board takes minutes
        return all(a_lo < b_hi + margin and b_lo < a_hi + margin for a_lo, a_hi, b_lo, b_hi in (
            (bb.min.X, bb.max.X, pb.min.X, pb.max.X), (bb.min.Y, bb.max.Y, pb.min.Y, pb.max.Y),
            (bb.min.Z, bb.max.Z, pb.min.Z, pb.max.Z)))

    near = [s for s in board.solids() if near_path(s.bounding_box())]
    assert len(near) >= 3                              # J3, and SMD parts the wires pass under
    assert overlap_volume(Compound(near), path) == pytest.approx(0, abs=1e-6)


def test_poke_holes_open(base):
    for x, y in (*P.WEACT_BUTTONS, P.MT3608_TRIMMER):
        assert not base.is_inside(Vector(x, y, P.FLOOR_UNDER_Z + 1.5))
        assert not base.is_inside(Vector(x + P.POKE_D / 2 - 0.3, y, P.FLOOR_UNDER_Z + 1.5))
        assert base.is_inside(Vector(x + P.POKE_D / 2 + 0.3, y, P.FLOOR_UNDER_Z + 1.5))


def _rect_to_circle(cx, cy, w, h, px, py, r):
    dx = max(abs(px - cx) - w / 2, 0.0)
    dy = max(abs(py - cy) - h / 2, 0.0)
    return math.hypot(dx, dy) - r


def test_floor_slots(base):
    centres = floor_slot_centres()
    assert len(centres) == 6 and P.FLOOR_SLOT_W <= 4.0
    for cx, cy in centres:
        assert not base.is_inside(Vector(cx, cy, P.FLOOR_UNDER_Z + 1.5))
        assert not base.is_inside(Vector(cx, cy + P.FLOOR_SLOT_LEN / 2 - 0.3, P.FLOOR_UNDER_Z + 1.5))
        assert base.is_inside(Vector(cx, cy + P.FLOOR_SLOT_LEN / 2 + 0.3, P.FLOOR_UNDER_Z + 1.5))
        for px, py in (*P.WEACT_BUTTONS, P.MT3608_TRIMMER):
            assert _rect_to_circle(cx, cy, P.FLOOR_SLOT_W, P.FLOOR_SLOT_LEN, px, py, P.POKE_D / 2) >= 3.0
        for px, py in P.HOLES:
            assert _rect_to_circle(cx, cy, P.FLOOR_SLOT_W, P.FLOOR_SLOT_LEN, px, py, P.BOSS_OD / 2) >= 3.0


def test_cable_hooks(base):
    x_wall = P.DRIVE_X_HALF + P.TRAY_GAP + P.TRAY_WALL
    z = (P.FLOOR_TOP_Z + P.CABLE_HOOK_TOP_Z) / 2
    b_tower_end_y = P.pol(P.B_FACE_R - P.B_WALL_T, P.B_PHI, -P.B_HALF_T)[1]   # B's end nearest the slot
    for y in P.CABLE_HOOK_Y:
        assert P.J3_CABLE_SLOT_Y + P.CABLE_SLOT_W / 2 < y - P.CABLE_HOOK_W / 2      # between the slot
        assert y + P.CABLE_HOOK_W / 2 < b_tower_end_y                                 # and B
        assert base.is_inside(Vector(x_wall + P.CABLE_HOOK_GAP + P.CABLE_HOOK_T / 2, y, z))     # post
        assert not base.is_inside(Vector(x_wall + P.CABLE_HOOK_GAP / 2, y, z))                 # channel
        assert base.is_inside(Vector(x_wall + P.CABLE_HOOK_GAP - P.CABLE_HOOK_LIP / 2, y,
                                     P.CABLE_HOOK_TOP_Z - 0.3))                                 # lip


def test_base_clears_board(base, board):
    assert min_clearance(base, board) >= 2.0
