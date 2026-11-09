"""The cover: top plate, drum wall down to the seat, the joint's lip, screw tabs and key, the
internal ridges with their central ring, and the threaded boss that holds sensor C.

Modelled in the drive frame in its position of use (plate on top). It is printed top face
down, so the wall, ridges, ring and boss all build upwards from the plate.
"""
from build123d import Align, Box, Cylinder, Part, Pos, extrude

from housing import joint
from housing import params as P
from housing.threads import M16X1_5, ThreadSpec, thread_negative

_MIN = (Align.CENTER, Align.CENTER, Align.MIN)
_OVER = 1.0                              # cutting tools run on past the faces they open

_R_OUT = P.DRUM_R_IN + P.DRUM_WALL       # drum wall outer face, 117
_FLAT_Y_OUT = P.FLAT_Y_IN - P.DRUM_WALL  # the flat's outer face, -14
_FLAT_Y_MID = P.FLAT_Y_IN - P.DRUM_WALL / 2
# The parts under the plate reach up to its mid-plane and out to the wall's mid-line, and the
# ridges start on the ring's mid-line, so each overlaps what it joins instead of meeting it
# face to face.
_PLATE_MID_Z = sum(P.PLATE_Z) / 2


def _prism(r: float, flat_y: float, z0: float, z1: float) -> Part:
    return Pos(0, 0, z0) * extrude(P.drum_outline(r, flat_y), z1 - z0)


def _radial_bar(r0: float, r1: float, width: float, z0: float, z1: float, phi: float) -> Part:
    """A bar along the radius at phi: r0…r1, `width` wide, z0…z1."""
    return joint.at_phi(Pos((r0 + r1) / 2, 0, z0) * Box(r1 - r0, width, z1 - z0, align=_MIN), phi)


def _shell() -> Part:
    """The plate, the wall r DRUM_R_IN…117 (with the flat) from the seat up to it, and the lip:
    the wall's outer half, r DRUM_R_MID…117, on down to LIP_BOTTOM_Z."""
    return (_prism(_R_OUT, _FLAT_Y_OUT, P.LIP_BOTTOM_Z, P.PLATE_Z[1])
            - _prism(P.DRUM_R_IN, P.FLAT_Y_IN, P.LIP_BOTTOM_Z - _OVER, P.PLATE_Z[0])
            - _prism(P.DRUM_R_MID, _FLAT_Y_MID, P.LIP_BOTTOM_Z - _OVER, P.SEAT_Z))


def _under_plate() -> Part:
    """Ridges, central ring, and C's boss with its web to the wall, all hanging from the plate.

    RIDGE_N ridges at phi = k * 360 / RIDGE_N run from the ring to the wall, from RIDGE_BOTTOM_Z
    up; the ring at RING_R spans the same heights. C's boss, Ø C_BOSS_D on C's axis, and its
    C_WEB_W web out to the wall come down to C_BOSS_UNDER_Z. Everything is trimmed at the
    wall's mid-line, which keeps the ridge at the flat inside the flat.
    """
    ring_mid = sum(P.RING_R) / 2
    ridges = [_radial_bar(ring_mid, P.DRUM_R_MID, P.RIDGE_T, P.RIDGE_BOTTOM_Z, _PLATE_MID_Z,
                          k * 360 / P.RIDGE_N) for k in range(P.RIDGE_N)]
    h = _PLATE_MID_Z - P.RIDGE_BOTTOM_Z
    ring = Pos(*P.SPINDLE, P.RIDGE_BOTTOM_Z) * (
        Cylinder(P.RING_R[1], h, align=_MIN) - Cylinder(P.RING_R[0], h, align=_MIN))
    boss = Pos(*P.pol(P.MAGNET_R, P.C_PHI), P.C_BOSS_UNDER_Z) * Cylinder(
        P.C_BOSS_D / 2, _PLATE_MID_Z - P.C_BOSS_UNDER_Z, align=_MIN)
    web = _radial_bar(P.MAGNET_R, P.DRUM_R_MID, P.C_WEB_W, P.C_BOSS_UNDER_Z, _PLATE_MID_Z, P.C_PHI)
    inside = _prism(P.DRUM_R_MID, _FLAT_Y_MID, P.C_BOSS_UNDER_Z - _OVER, P.PLATE_Z[1])
    return ring.fuse(*ridges, boss, web) & inside


def build_cover(thread: ThreadSpec = M16X1_5) -> Part:
    """The cover in its position of use, with `thread` through C's boss and the plate.

    The tabs' screw holes reach above the lip's bottom, so they are cut again after the tabs
    are fused to the lip. The thread negative is placed by pure translation with its start at
    C_BOSS_UNDER_Z, like the coupon's, so the hole matches the coupon's at the same height
    above its start.
    """
    body = _shell().fuse(_under_plate(), *(joint.tab_solid(phi) for phi in P.TAB_ANGLES),
                         joint.key_tab())
    c_thread = Pos(*P.pol(P.MAGNET_R, P.C_PHI), P.C_BOSS_UNDER_Z) * thread_negative(
        thread, P.PLATE_Z[1] - P.C_BOSS_UNDER_Z)
    body = body.cut(*(joint.tab_hole(phi) for phi in P.TAB_ANGLES), c_thread)
    return Part([body.clean()])
