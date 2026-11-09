"""The joint between base and cover: screw tabs, their recesses and insert bosses, the key.

Each solid is modelled about the spindle with +X radial and +Y tangential, then turned
to its angle phi the same way as params.pol(). Widths are straight (chord) widths.
"""
from build123d import Align, Axis, Box, Cylinder, Part, Plane, Polygon, Pos, Rot, revolve

from housing import params as P

_MIN = (Align.CENTER, Align.CENTER, Align.MIN)
_R_OUT = P.DRUM_R_IN + P.DRUM_WALL      # 117, outer face of the drum wall
_OVER = 1.0                             # cutting tools run on past the faces they open
_ARC = 30.0                             # revolve span, wider than any tab, trimmed to width


def _at_phi(shape: Part, phi: float) -> Part:
    return Pos(*P.SPINDLE) * Rot(0, 0, -phi) * shape


def _slab(r_in: float, r_out: float, width: float, z0: float, z1: float) -> Part:
    """Box r_in - 1 … r_out + 1 along +X, ±width/2 in Y, z0…z1."""
    return Pos((r_in + r_out) / 2, 0, z0) * Box(r_out - r_in + 2.0, width, z1 - z0, align=_MIN)


def _sector(r_in: float, r_out: float, width: float, z0: float, z1: float) -> Part:
    """The ring r_in…r_out about the origin, z0…z1, cut to a slab `width` wide about +X."""
    h = z1 - z0
    ring = Pos(0, 0, z0) * (Cylinder(r_out, h, align=_MIN) - Cylinder(r_in, h, align=_MIN))
    return ring & _slab(r_in, r_out, width, z0, z1)


def _radial_hole(d: float, r_in: float, r_out: float, z: float) -> Part:
    return Pos((r_in + r_out) / 2, 0, z) * Rot(0, 90, 0) * Cylinder(d / 2, r_out - r_in)


def tab_solid(phi: float) -> Part:
    """The cover's screw tab at phi, as positive material.

    The lip continues down (r DRUM_R_MID…117, LIP_BOTTOM_Z to TAB_BOTTOM_Z) and is
    thickened outwards to TAB_R_OUT from TAB_THICK_TOP_Z down, the thickening's top edge
    chamfered at 45°; TAB_WIDTH wide, with an M4 clearance hole on SCREW_Z.
    """
    chamfer = P.TAB_R_OUT - _R_OUT
    profile = Plane.XZ * Polygon(
        (P.DRUM_R_MID, P.LIP_BOTTOM_Z),
        (P.DRUM_R_MID, P.TAB_BOTTOM_Z),
        (P.TAB_R_OUT, P.TAB_BOTTOM_Z),
        (P.TAB_R_OUT, P.TAB_THICK_TOP_Z - chamfer),
        (_R_OUT, P.TAB_THICK_TOP_Z),
        (_R_OUT, P.LIP_BOTTOM_Z),
        align=None,
    )
    ring = Rot(0, 0, -_ARC / 2) * revolve(profile, Axis.Z, _ARC)
    tab = ring & _slab(P.DRUM_R_MID, P.TAB_R_OUT, P.TAB_WIDTH, P.TAB_BOTTOM_Z, P.TAB_THICK_TOP_Z)
    tab -= _radial_hole(P.M4_CLEAR_D, P.DRUM_R_MID - _OVER, P.TAB_R_OUT + _OVER, P.SCREW_Z)
    return _at_phi(tab, phi)


def recess_cut(phi: float) -> Part:
    """The base's pocket for a tab: its outer wall half cut away round the tab, with clearance."""
    return _at_phi(_sector(P.DRUM_R_MID, P.TAB_R_OUT + P.JOINT_END_CLEAR,
                           P.TAB_WIDTH + 2 * P.JOINT_SIDE_CLEAR,
                           P.RECESS_BOTTOM_Z, P.BASE_OUTER_TOP_Z), phi)


def insert_hole(phi: float) -> Part:
    """The radial M4 insert hole on SCREW_Z, M4_INSERT_HOLE_DEPTH in from r DRUM_R_MID.

    It runs on JOINT_END_CLEAR into the recess so that it cuts the wall cleanly; the base
    cuts it again after fusing the boss to the wall, which would otherwise refill it.
    """
    return _at_phi(_radial_hole(P.M4_INSERT_HOLE_D, P.DRUM_R_MID - P.M4_INSERT_HOLE_DEPTH,
                                P.DRUM_R_MID + P.JOINT_END_CLEAR, P.SCREW_Z), phi)


def insert_boss(phi: float) -> Part:
    """The boss inside the base wall that holds a tab's insert: r INSERT_BOSS_R_IN…DRUM_R_MID."""
    boss = _at_phi(_sector(P.INSERT_BOSS_R_IN, P.DRUM_R_MID, P.INSERT_BOSS_W, *P.INSERT_BOSS_Z), phi)
    return boss - insert_hole(phi)


def key_notch() -> Part:
    """The base's key notch at KEY_ANGLE: the inner wall half, KEY_WIDTH wide, KEY_DEPTH deep."""
    return _at_phi(_sector(P.DRUM_R_IN, P.DRUM_R_MID, P.KEY_WIDTH,
                           P.SEAT_Z - P.KEY_DEPTH, P.SEAT_Z), P.KEY_ANGLE)


def key_tab() -> Part:
    """The cover's key: the notch less JOINT_SIDE_CLEAR each side and JOINT_END_CLEAR short."""
    return _at_phi(_sector(P.DRUM_R_IN, P.DRUM_R_MID, P.KEY_WIDTH - 2 * P.JOINT_SIDE_CLEAR,
                           P.SEAT_Z - P.KEY_DEPTH + P.JOINT_END_CLEAR, P.SEAT_Z), P.KEY_ANGLE)
