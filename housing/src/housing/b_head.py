"""Sensor B's head: the upper part of B's tower, which carries the coil and moves up and down.

Modelled in the drive frame in its position of use. B's parts are built in a local frame,
r along +X (radial) and t along +Y (tangential), and turned to B_PHI like params.pol().

The head stands on the base's lower tower (base.lower_tower). Two pull screws come up from
below into inserts in its bottom; two push set screws in the lower tower bear on the underside
of a ledge further out; the lower tower's tongue runs in its bottom groove.
"""
from build123d import Box, Cylinder, Part, Pos, Rot

from housing import params as P
from housing.joint import at_phi

_OVER = 1.0                              # cutting tools run on past the faces they open
_WALL_R_IN = P.B_FACE_R - P.B_WALL_T


def head_bottom_z(bar_top_z: float) -> float:
    """Z of the head's underside when the coil's bar top is at bar_top_z."""
    return bar_top_z - P.B_HEAD_H


def b_block(r0: float, r1: float, t0: float, t1: float, z0: float, z1: float) -> Part:
    """A box r0…r1, t0…t1, z0…z1 in B's local frame, turned to B_PHI."""
    return at_phi(Pos((r0 + r1) / 2, (t0 + t1) / 2, (z0 + z1) / 2) * Box(r1 - r0, t1 - t0, z1 - z0),
                  P.B_PHI)


def b_post(r: float, t: float, d: float, z0: float, z1: float) -> Part:
    """A vertical cylinder of diameter d on B's local (r, t), z0…z1."""
    return at_phi(Pos(r, t, (z0 + z1) / 2) * Cylinder(d / 2, z1 - z0), P.B_PHI)


def rail_spans(inset: float) -> list[tuple[float, float]]:
    """Tangential spans of the groove (inset 0) or the tongue (inset B_TONGUE_CLEAR).

    The groove runs ±B_GROOVE_HALF_T but stops over the pull bosses (B_PULL_T ± B_BOSS_W/2);
    the tongue keeps `inset` inside it.
    """
    end = P.B_GROOVE_HALF_T - inset
    near = P.B_PULL_T - P.B_BOSS_W / 2 - inset
    far = P.B_PULL_T + P.B_BOSS_W / 2 + inset
    return [(-end, -far), (-near, near), (far, end)]


def _radial_cylinder(d: float, r0: float, r1: float, t: float, z: float) -> Part:
    return at_phi(Pos((r0 + r1) / 2, t, z) * Rot(0, 90, 0) * Cylinder(d / 2, r1 - r0), P.B_PHI)


def build_b_head(bar_top_z: float = P.B_BAR_TOP_NOM) -> Part:
    """The head in its position of use, with the coil's bar top at bar_top_z.

    - Wall r B_FACE_R - B_WALL_T…B_FACE_R, ±B_HALF_T, from head_bottom_z up to
      B_HEAD_TOP_BELOW_BAR under the bar top.
    - The bar's two M4 inserts: radial holes from the face at t ±B_HOLE_SPACING/2,
      B_HOLE_BELOW_TOP under the bar top, M4_INSERT_HOLE_DEPTH deep, in Ø B_BOSS_W bosses
      that reach back just as far, so the holes open at the back (a closed end would bring
      the boss nearer the drive than B_DRIVE_CLEARANCE). The bosses stop at the head's top.
    - The pull inserts: vertical holes from the bottom at (B_SCREW_R, ±B_PULL_T), with a
      B_PULL_RUNOUT clearance run-out above for the screw's tip, in full-height bosses
      r B_BOSS_R_IN…B_FACE_R that are also the ribs on the back.
    - The ledge: B_LEDGE_T thick on the bottom, from the face out under the coil body to past
      the push screws (B_PUSH_R, ±B_PUSH_T), which bear on its underside.
    - The bottom groove (rail_spans), and the relief pocket in the face behind the coil body.
    """
    z0, z1 = head_bottom_z(bar_top_z), bar_top_z - P.B_HEAD_TOP_BELOW_BAR
    bar_z = bar_top_z - P.B_HOLE_BELOW_TOP
    bar_ts = (-P.B_HOLE_SPACING / 2, P.B_HOLE_SPACING / 2)
    pull_ts = (-P.B_PULL_T, P.B_PULL_T)
    bar_back_r = P.B_FACE_R - P.M4_INSERT_HOLE_DEPTH

    wall = b_block(_WALL_R_IN, P.B_FACE_R, -P.B_HALF_T, P.B_HALF_T, z0, z1)
    pull_bosses = [b_block(P.B_BOSS_R_IN, P.B_FACE_R, t - P.B_BOSS_W / 2, t + P.B_BOSS_W / 2, z0, z1)
                   for t in pull_ts]
    clip = b_block(bar_back_r - _OVER, P.B_FACE_R, -P.B_HALF_T, P.B_HALF_T, z0, z1)
    bar_bosses = [_radial_cylinder(P.B_BOSS_W, bar_back_r, P.B_FACE_R, t, bar_z) & clip
                  for t in bar_ts]
    reach = P.B_PUSH_BOSS_W / 2
    ledge = b_block(P.B_FACE_R - _OVER, P.B_PUSH_R + reach, -(P.B_PUSH_T + reach), P.B_PUSH_T + reach,
                    z0, z0 + P.B_LEDGE_T)
    body = wall.fuse(*pull_bosses, *bar_bosses, ledge)

    bar_holes = [_radial_cylinder(P.M4_INSERT_HOLE_D, bar_back_r - _OVER, P.B_FACE_R + _OVER, t, bar_z)
                 for t in bar_ts]
    pull_holes = [b_post(P.B_SCREW_R, t, P.M4_INSERT_HOLE_D, z0 - _OVER, z0 + P.M4_INSERT_HOLE_DEPTH)
                  for t in pull_ts]
    runouts = [b_post(P.B_SCREW_R, t, P.M4_CLEAR_D, z0, z0 + P.M4_INSERT_HOLE_DEPTH + P.B_PULL_RUNOUT)
               for t in pull_ts]
    groove = [b_block(*P.B_GROOVE_R, t0, t1, z0 - _OVER, z0 + P.B_GROOVE_DEPTH)
              for t0, t1 in rail_spans(0.0)]
    pocket_top = bar_top_z - P.B_POCKET_TOP_BELOW
    pocket = b_block(P.B_FACE_R - P.B_POCKET_DEPTH, P.B_FACE_R + _OVER,
                     -P.B_POCKET_HALF_T, P.B_POCKET_HALF_T, pocket_top - P.B_POCKET_H, pocket_top)
    body = body.cut(*bar_holes, *pull_holes, *runouts, *groove, pocket)
    return Part([body.clean()])
