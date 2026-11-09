"""The joint between base and cover: screw tabs, their recesses and insert bosses, the key.

Each solid is modelled about the spindle with +X radial and +Y tangential, then turned
to its angle phi the same way as params.pol(). Widths are straight (chord) widths.

The cover's parts (tab_solid, key_tab) have their inner faces at DRUM_R_MID; the base's
parts stop at BASE_JOINT_R, JOINT_RADIAL_CLEAR inside it.
"""
from build123d import Align, Axis, Box, Cylinder, Part, Plane, Polygon, Pos, Rot, revolve

from housing import params as P

_MIN = (Align.CENTER, Align.CENTER, Align.MIN)
_R_OUT = P.DRUM_R_IN + P.DRUM_WALL      # 117, outer face of the drum wall
_OVER = 1.0                             # cutting tools run on past the faces they open
_ARC = 30.0                             # revolve span, wider than any tab, trimmed to width


def at_phi(shape: Part, phi: float) -> Part:
    """Turn a shape modelled about the origin (+X radial) to angle phi about the spindle."""
    return Pos(*P.SPINDLE) * Rot(0, 0, -phi) * shape


def _slab(r_in: float, r_out: float, width: float, z0: float, z1: float) -> Part:
    """Box r_in - 1 … r_out + 1 along +X, ±width/2 in Y, z0…z1."""
    return Pos((r_in + r_out) / 2, 0, z0) * Box(r_out - r_in + 2.0, width, z1 - z0, align=_MIN)


def _sector(r_in: float, r_out: float, width: float, z0: float, z1: float) -> Part:
    """The ring r_in…r_out about the origin, z0…z1, cut to a slab `width` wide about +X."""
    h = z1 - z0
    ring = Pos(0, 0, z0) * (Cylinder(r_out, h, align=_MIN) - Cylinder(r_in, h, align=_MIN))
    return ring & _slab(r_in, r_out, width, z0, z1)


def radial_profile(points: list[tuple[float, float]], width: float) -> Part:
    """An (r, z) polygon revolved about the origin's Z axis, trimmed to a slab `width` wide about +X.

    Its faces stay concentric with the drum, so it meets the wall and lip without slivers.
    """
    profile = Plane.XZ * Polygon(*points, align=None)
    rs, zs = [p[0] for p in points], [p[1] for p in points]
    ring = Rot(0, 0, -_ARC / 2) * revolve(profile, Axis.Z, _ARC)
    return ring & _slab(min(rs), max(rs), width, min(zs), max(zs))


def _radial_hole(d: float, r_in: float, r_out: float, z: float) -> Part:
    return Pos((r_in + r_out) / 2, 0, z) * Rot(0, 90, 0) * Cylinder(d / 2, r_out - r_in)


def tab_solid(phi: float) -> Part:
    """The cover's screw tab at phi, as positive material.

    The lip continues down (r DRUM_R_MID…117, LIP_BOTTOM_Z to TAB_BOTTOM_Z) and is
    thickened outwards to TAB_R_OUT from TAB_THICK_TOP_Z down, the thickening's top edge
    chamfered at 45°; TAB_WIDTH wide, with an M4 clearance hole on SCREW_Z.
    """
    chamfer = P.TAB_R_OUT - _R_OUT
    tab = radial_profile([
        (P.DRUM_R_MID, P.LIP_BOTTOM_Z),
        (P.DRUM_R_MID, P.TAB_BOTTOM_Z),
        (P.TAB_R_OUT, P.TAB_BOTTOM_Z),
        (P.TAB_R_OUT, P.TAB_THICK_TOP_Z - chamfer),
        (_R_OUT, P.TAB_THICK_TOP_Z),
        (_R_OUT, P.LIP_BOTTOM_Z),
    ], P.TAB_WIDTH)
    tab -= _radial_hole(P.M4_CLEAR_D, P.DRUM_R_MID - _OVER, P.TAB_R_OUT + _OVER, P.SCREW_Z)
    return at_phi(tab, phi)


def recess_cut(phi: float) -> Part:
    """The base's pocket for a tab: its wall cut away outside BASE_JOINT_R round the tab.

    RECESS_SIDE_CLEAR wider each side than the tab and JOINT_END_CLEAR beyond its
    thickening, from BASE_OUTER_TOP_Z down to RECESS_BOTTOM_Z.
    """
    return at_phi(_sector(P.BASE_JOINT_R, P.TAB_R_OUT + P.JOINT_END_CLEAR,
                          P.TAB_WIDTH + 2 * P.RECESS_SIDE_CLEAR,
                          P.RECESS_BOTTOM_Z, P.BASE_OUTER_TOP_Z), phi)


def insert_hole(phi: float) -> Part:
    """The radial M4 insert hole on SCREW_Z, M4_INSERT_HOLE_DEPTH in from the recess face.

    It runs on into the recess so that it cuts the face cleanly; the base cuts it again
    after fusing the boss to the wall, which would otherwise refill it.
    """
    return at_phi(_radial_hole(P.M4_INSERT_HOLE_D, P.BASE_JOINT_R - P.M4_INSERT_HOLE_DEPTH,
                               P.BASE_JOINT_R + _OVER, P.SCREW_Z), phi)


def insert_boss(phi: float) -> Part:
    """The boss inside the base wall that holds a tab's insert: r INSERT_BOSS_R_IN…BASE_JOINT_R."""
    boss = at_phi(_sector(P.INSERT_BOSS_R_IN, P.BASE_JOINT_R, P.INSERT_BOSS_W, *P.INSERT_BOSS_Z), phi)
    return boss - insert_hole(phi)


def key_notch() -> Part:
    """The base's key notch at KEY_ANGLE: the inner wall half, KEY_WIDTH wide, KEY_DEPTH deep."""
    return at_phi(_sector(P.DRUM_R_IN, P.DRUM_R_MID, P.KEY_WIDTH,
                          P.SEAT_Z - P.KEY_DEPTH, P.SEAT_Z), P.KEY_ANGLE)


def key_tab() -> Part:
    """The cover's key: the notch less KEY_SIDE_CLEAR each side and JOINT_END_CLEAR short."""
    return at_phi(_sector(P.DRUM_R_IN, P.DRUM_R_MID, P.KEY_WIDTH - 2 * P.KEY_SIDE_CLEAR,
                          P.SEAT_Z - P.KEY_DEPTH + P.JOINT_END_CLEAR, P.SEAT_Z), P.KEY_ANGLE)
