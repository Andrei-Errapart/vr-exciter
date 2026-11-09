"""The base: tray round the electronics, drum floor and lower wall, joint, feet, openings,
and the lower tower of sensor B's mount.

Modelled in the drive frame in its position of use (floor down at FLOOR_UNDER_Z).
"""
from build123d import (Align, Box, Cylinder, Kind, Part, Plane, Polygon, Pos, Rectangle, extrude, loft,
                       offset)

from housing import joint
from housing import params as P
from housing.b_frame import b_block, b_post, b_prism, rail_spans

_MIN = (Align.CENTER, Align.CENTER, Align.MIN)
_OVER = 1.0                              # cutting tools run on past the faces they open

_R_OUT = P.DRUM_R_IN + P.DRUM_WALL       # drum wall outer face, 117
_FLAT_Y_OUT = P.FLAT_Y_IN - P.DRUM_WALL  # the flat's outer face, -14
_FLAT_Y_MID = P.FLAT_Y_IN - P.DRUM_WALL / 2

# Tray: the drive footprint plus TRAY_GAP (TRAY_END_GAP at the connector end), walls outside it.
_TRAY_X_IN = P.DRIVE_X_HALF + P.TRAY_GAP
_TRAY_X_OUT = _TRAY_X_IN + P.TRAY_WALL
_TRAY_Y_IN = (-P.TRAY_END_GAP, P.DRIVE_LEN + P.TRAY_GAP)
_TRAY_Y_OUT = (_TRAY_Y_IN[0] - P.TRAY_WALL, _TRAY_Y_IN[1] + P.TRAY_WALL)


def _box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def _post(x: float, y: float, d: float, z0: float, z1: float) -> Part:
    return Pos(x, y, z0) * Cylinder(d / 2, z1 - z0, align=_MIN)


def _drum() -> Part:
    """Floor over the whole drum outline, wall r 113–117 to BASE_OUTER_TOP_Z, inner half to the seat.

    The inner half ends at BASE_JOINT_R (at the flat, JOINT_RADIAL_CLEAR short of the
    flat's mid-line), clear of the cover's lip.
    """
    def prism(r: float, flat_y: float, z0: float, z1: float) -> Part:
        return Pos(0, 0, z0) * extrude(P.drum_outline(r, flat_y), z1 - z0)

    return (prism(_R_OUT, _FLAT_Y_OUT, P.FLOOR_UNDER_Z, P.BASE_OUTER_TOP_Z)
            + prism(P.BASE_JOINT_R, _FLAT_Y_MID + P.JOINT_RADIAL_CLEAR, P.FLOOR_UNDER_Z, P.SEAT_Z)
            - prism(P.DRUM_R_IN, P.FLAT_Y_IN, P.FLOOR_TOP_Z, P.SEAT_Z + _OVER))


def _tray_outer() -> Part:
    return _box(-_TRAY_X_OUT, _TRAY_X_OUT, *_TRAY_Y_OUT, P.FLOOR_UNDER_Z, P.DRIVE_UNDER_Z)


def _tray() -> Part:
    walls = _box(-_TRAY_X_OUT, _TRAY_X_OUT, *_TRAY_Y_OUT, P.FLOOR_UNDER_Z, P.TRAY_WALL_TOP_Z)
    return walls - _box(-_TRAY_X_IN, _TRAY_X_IN, *_TRAY_Y_IN, P.FLOOR_TOP_Z, P.TRAY_WALL_TOP_Z + _OVER)


def _screw_bosses() -> Part:
    """The four bosses under holes 4, 5, 9, 10, up to the drive, trimmed to the tray's outside."""
    bosses = [_post(x, y, P.BOSS_OD, P.FLOOR_UNDER_Z, P.DRIVE_UNDER_Z) for x, y in P.HOLES]
    return _fuse(bosses) & _tray_outer()


def _screw_bores() -> list[Part]:
    """Each boss is open from below up to its ledge, with a clearance hole through the ledge."""
    ledge_z = P.DRIVE_UNDER_Z - P.BOSS_LEDGE
    cuts = []
    for x, y in P.HOLES:
        cuts.append(_post(x, y, P.BOSS_BORE_D, P.FLOOR_UNDER_Z - _OVER, ledge_z))
        cuts.append(_post(x, y, P.BOSS_CLEAR_D, P.FLOOR_UNDER_Z - _OVER, P.DRIVE_UNDER_Z + _OVER))
    return cuts


def _feet_pads() -> list[Part]:
    top = P.FLOOR_UNDER_Z + P.M3_INSERT_HOLE_DEPTH + P.FOOT_PAD_CAP
    return [_post(*P.pol(P.FEET_R, phi), P.FOOT_PAD_D, P.FLOOR_UNDER_Z, top) for phi in P.FEET_ANGLES]


def _feet_holes() -> list[Part]:
    top = P.FLOOR_UNDER_Z + P.M3_INSERT_HOLE_DEPTH
    return [_post(*P.pol(P.FEET_R, phi), P.M3_INSERT_HOLE_D, P.FLOOR_UNDER_Z - _OVER, top)
            for phi in P.FEET_ANGLES]


def _usb_tube() -> Part:
    """The USB tunnel's walls: a block from the flat's outer face to the tray's inner face.

    It stands on the floor, so its bottom is closed and needs no bridge; the tunnel
    through it opens only at the flat's outer face and into the tray.
    """
    x, z = P.USB_CENTRE_XZ
    w, h = P.USB_WINDOW
    t = P.USB_TUNNEL_WALL
    return _box(x - w / 2 - t, x + w / 2 + t, _FLAT_Y_OUT, _TRAY_Y_IN[0],
                P.FLOOR_UNDER_Z, z + h / 2 + t)


def _usb_opening() -> list[Part]:
    """USB_WINDOW through the tube and the end wall, flared to USB_FLARE across the flat."""
    x, z = P.USB_CENTRE_XZ
    w, h = P.USB_WINDOW
    fw, fh = P.USB_FLARE

    def section(y: float, sw: float, sh: float):
        return Plane(origin=(x, y, z), x_dir=(1, 0, 0), z_dir=(0, 1, 0)) * Rectangle(sw, sh)

    flare = loft([section(_FLAT_Y_OUT, fw, fh), section(P.FLAT_Y_IN, w, h)])
    mouth = _box(x - fw / 2, x + fw / 2, _FLAT_Y_OUT - _OVER, _FLAT_Y_OUT, z - fh / 2, z + fh / 2)
    bore = _box(x - w / 2, x + w / 2, _FLAT_Y_OUT - _OVER, _TRAY_Y_IN[0] + _OVER, z - h / 2, z + h / 2)
    return [flare, mouth, bore]


def _wire_slots() -> list[Part]:
    """J1's slot in the end wall, the 12 V slot in the flat and B's cable slot in the right wall.

    Each is open from the top of its wall, so the wires drop in as the base is fitted.
    """
    j1 = _box(*P.J1_SLOT_X, _TRAY_Y_OUT[0] - _OVER, _TRAY_Y_IN[0] + _OVER,
              P.J1_SLOT_BOTTOM_Z, P.TRAY_WALL_TOP_Z + _OVER)
    psu = _box(P.PSU_SLOT_X - P.PSU_SLOT_W / 2, P.PSU_SLOT_X + P.PSU_SLOT_W / 2,
               _FLAT_Y_OUT - _OVER, P.FLAT_Y_IN + _OVER, P.PSU_SLOT_BOTTOM_Z, P.SEAT_Z + _OVER)
    j3 = _box(_TRAY_X_IN - _OVER, _TRAY_X_OUT + _OVER,
              P.J3_CABLE_SLOT_Y - P.CABLE_SLOT_W / 2, P.J3_CABLE_SLOT_Y + P.CABLE_SLOT_W / 2,
              P.J3_SLOT_BOTTOM_Z, P.TRAY_WALL_TOP_Z + _OVER)
    return [j1, psu, j3]


def floor_slot_centres() -> list[tuple[float, float]]:
    """Centres of the vent slots: three side by side round each of FLOOR_SLOT_GROUPS."""
    return [(gx + k * P.FLOOR_SLOT_PITCH, gy) for gx, gy in P.FLOOR_SLOT_GROUPS for k in (-1, 0, 1)]


def _floor_holes() -> list[Part]:
    """Poke holes under the WeAct's buttons and the MT3608's trimmer, and the vent slots."""
    z0, z1 = P.FLOOR_UNDER_Z - _OVER, P.FLOOR_TOP_Z + _OVER
    pokes = [_post(x, y, P.POKE_D, z0, z1) for x, y in (*P.WEACT_BUTTONS, P.MT3608_TRIMMER)]
    slots = [_box(x - P.FLOOR_SLOT_W / 2, x + P.FLOOR_SLOT_W / 2,
                  y - P.FLOOR_SLOT_LEN / 2, y + P.FLOOR_SLOT_LEN / 2, z0, z1)
             for x, y in floor_slot_centres()]
    return pokes + slots


def _cable_hooks() -> list[Part]:
    """Hooks for B's cable on the outside of the right tray wall.

    A post stands on the floor CABLE_HOOK_GAP out from the wall; a lip at its top reaches
    back towards the wall, its underside chamfered at 45° so that it prints.
    """
    x = _TRAY_X_OUT + P.CABLE_HOOK_GAP
    t, lip, top = P.CABLE_HOOK_T, P.CABLE_HOOK_LIP, P.CABLE_HOOK_TOP_Z
    profile = Plane.XZ * Polygon(
        (x, P.FLOOR_UNDER_Z), (x + t, P.FLOOR_UNDER_Z), (x + t, top),
        (x - lip, top), (x - lip, top - t), (x, top - t - lip),
        align=None,
    )
    hook = extrude(profile, P.CABLE_HOOK_W / 2, both=True)
    return [Pos(0, y, 0) * hook for y in P.CABLE_HOOK_Y]


def _insert_boss_gussets() -> list[Part]:
    """A 45° gusset under each insert boss, so that its underside prints without support.

    It runs from the boss's inner bottom edge (r INSERT_BOSS_R_IN) down and out to the
    wall's inner face, and on into the wall to fuse with it.
    """
    r0, z0 = P.INSERT_BOSS_R_IN, P.INSERT_BOSS_Z[0]
    r1 = P.DRUM_R_IN + _OVER
    gusset = joint.radial_profile([(r0, z0), (r1, z0), (r1, z0 - (r1 - r0))], P.INSERT_BOSS_W)
    return [joint.at_phi(gusset, phi) for phi in P.TAB_ANGLES]


def _b_tower_holes() -> list[Part]:
    """The screw holes of B's lower tower, from below the floor up through the tower's top.

    Pull (B_PULL_POINTS): an M4 clearance bore, counterbored from below for the socket head.
    Push (B_PUSH_POINTS): an insert hole B_PUSH_RECESS up a recess, with a clearance bore on up
    for the set screw.
    """
    below, above = P.FLOOR_UNDER_Z - _OVER, P.B_LOWER_TOP_Z + _OVER
    insert_z = P.FLOOR_UNDER_Z + P.B_PUSH_RECESS
    cuts = []
    for r, t in P.B_PULL_POINTS:
        cuts += [
            b_post(r, t, P.M4_CLEAR_D, below, above),
            b_post(r, t, P.B_PULL_CBORE_D, below, P.FLOOR_UNDER_Z + P.B_PULL_CBORE_DEPTH),
        ]
    for r, t in P.B_PUSH_POINTS:
        cuts += [
            b_post(r, t, P.B_PUSH_RECESS_D, below, insert_z),
            b_post(r, t, P.M4_INSERT_HOLE_D, below, insert_z + P.M4_INSERT_HOLE_DEPTH),
            b_post(r, t, P.M4_CLEAR_D, below, above),
        ]
    return cuts


def lower_tower() -> Part:
    """B's lower tower, on the floor from FLOOR_TOP_Z up to B_LOWER_TOP_Z, under the head.

    - The head's wall footprint (r B_FACE_R - B_WALL_T…B_FACE_R, ±B_HALF_T), which carries the
      tongue that runs in the head's groove (b_frame.rail_spans).
    - The plinth: the push triangle (B_PUSH_POINTS) grown by B_TOWER_PAD, one solid block round
      all four screws (_b_tower_holes), so the screws' loads close through it and not through
      the floor.
    """
    z0, z1 = P.FLOOR_TOP_Z, P.B_LOWER_TOP_Z
    wall = b_block(P.B_FACE_R - P.B_WALL_T, P.B_FACE_R, -P.B_HALF_T, P.B_HALF_T, z0, z1)
    plinth = b_prism(offset(Polygon(*P.B_PUSH_POINTS, align=None), P.B_TOWER_PAD, kind=Kind.ARC), z0, z1)
    r0, r1 = P.B_GROOVE_R[0] + P.B_TONGUE_CLEAR, P.B_GROOVE_R[1] - P.B_TONGUE_CLEAR
    tongue = [b_block(r0, r1, t0, t1, z1, z1 + P.B_TONGUE_H) for t0, t1 in rail_spans(P.B_TONGUE_CLEAR)]
    return Part([_fuse([wall, plinth, *tongue]).cut(*_b_tower_holes()).clean()])


def _fuse(parts: list[Part]) -> Part:
    return parts[0].fuse(*parts[1:])


def build_base() -> Part:
    """The base in its position of use."""
    body = _fuse([_drum(), _tray(), _screw_bosses(), *_feet_pads(), _usb_tube(), *_cable_hooks(),
                  lower_tower()])
    body = body.cut(
        *_screw_bores(),
        *_feet_holes(),
        *(joint.recess_cut(phi) for phi in P.TAB_ANGLES),
        joint.key_notch(),
        *_usb_opening(),
        *_wire_slots(),
        *_floor_holes(),
        *_b_tower_holes(),
    )
    # The insert bosses share the wall's r BASE_JOINT_R face, as do the recesses; cutting a
    # recess after fusing the bosses leaves an invalid solid, so the bosses (and their
    # gussets) go on last and their holes are cut again through the wall they were fused to.
    body = body.fuse(*(joint.insert_boss(phi) for phi in P.TAB_ANGLES), *_insert_boss_gussets())
    body = body.cut(*(joint.insert_hole(phi) for phi in P.TAB_ANGLES))
    return Part([body.clean()])
