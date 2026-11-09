"""Sensor B's head: the upper part of B's tower, which carries the coil and moves up and down.

Modelled in the drive frame in its position of use, in B's local frame (b_frame.py).

The head stands on the base's lower tower (base.lower_tower) on three push set screws, which
bear on its underside at B_PUSH_POINTS; one pull screw comes up from below into an insert in its
bottom at B_PULL_POINTS, inside the push triangle. The lower tower's tongue runs in its bottom
groove.
"""
from build123d import Kind, Part, Polygon, offset

from housing import params as P
from housing.b_frame import b_block, b_post, b_prism, b_radial_cylinder, rail_spans

_OVER = 1.0                              # cutting tools run on past the faces they open
_WALL_R_IN = P.B_FACE_R - P.B_WALL_T


def head_bottom_z(bar_top_z: float) -> float:
    """Z of the head's underside when the coil's bar top is at bar_top_z."""
    return bar_top_z - P.B_HEAD_H


def _rear_block(z0: float, z1: float) -> Part:
    """Behind the wall: the pads the back pushes bear on, joined into one block round the pull.

    The rectangle from the back pushes' radius to the wall's inner face, ±B_BACK_PUSH_T, grown by
    half B_PUSH_PAD_D: its back corners are the pads, round about the push points, and its front
    corners lie inside the wall.
    """
    r0, r1, t = P.B_BACK_PUSH_R, _WALL_R_IN, P.B_BACK_PUSH_T
    outline = offset(Polygon((r0, -t), (r1, -t), (r1, t), (r0, t), align=None),
                     P.B_PUSH_PAD_D / 2, kind=Kind.ARC)
    return b_prism(outline, z0, z1)


def build_b_head(bar_top_z: float = P.B_BAR_TOP_NOM) -> Part:
    """The head in its position of use, with the coil's bar top at bar_top_z.

    - Wall r B_FACE_R - B_WALL_T…B_FACE_R, ±B_HALF_T, from head_bottom_z up to
      B_HEAD_TOP_BELOW_BAR under the bar top.
    - The bar's two M4 inserts: radial holes from the face at t ±B_HOLE_SPACING/2,
      B_HOLE_BELOW_TOP under the bar top, M4_INSERT_HOLE_DEPTH deep, in Ø B_BAR_BOSS_D bosses
      that reach back just as far, so the holes open at the back (a closed end would bring
      the boss nearer the drive than B_DRIVE_CLEARANCE). The bosses stop at the head's top.
    - The rear block behind the wall (_rear_block): the back pushes' pads, and the back of the
      pull insert. It reaches B_MIN_PLASTIC above the pull's run-out.
    - The ledge: B_LEDGE_T thick on the bottom, from the face out under the coil body to
      half B_PUSH_PAD_D past the front push, which bears on its underside.
    - The pull insert: a vertical hole from the bottom at each B_PULL_POINTS, with a
      B_PULL_RUNOUT clearance run-out above for the screw's tip.
    - The bottom groove (rail_spans), and the relief pocket in the face behind the coil body.
    """
    z0, z1 = head_bottom_z(bar_top_z), bar_top_z - P.B_HEAD_TOP_BELOW_BAR
    bar_z = bar_top_z - P.B_HOLE_BELOW_TOP
    bar_ts = (-P.B_HOLE_SPACING / 2, P.B_HOLE_SPACING / 2)
    bar_back_r = P.B_FACE_R - P.M4_INSERT_HOLE_DEPTH
    pull_top = z0 + P.M4_INSERT_HOLE_DEPTH + P.B_PULL_RUNOUT

    wall = b_block(_WALL_R_IN, P.B_FACE_R, -P.B_HALF_T, P.B_HALF_T, z0, z1)
    clip = b_block(bar_back_r - _OVER, P.B_FACE_R, -P.B_HALF_T, P.B_HALF_T, z0, z1)
    bar_bosses = [b_radial_cylinder(P.B_BAR_BOSS_D, bar_back_r, P.B_FACE_R, t, bar_z) & clip
                  for t in bar_ts]
    rear = _rear_block(z0, pull_top + P.B_MIN_PLASTIC)
    ledge = b_block(P.B_FACE_R - _OVER, P.B_FRONT_PUSH_R + P.B_PUSH_PAD_D / 2,
                    -P.B_LEDGE_HALF_T, P.B_LEDGE_HALF_T, z0, z0 + P.B_LEDGE_T)
    body = wall.fuse(*bar_bosses, rear, ledge)

    bar_holes = [b_radial_cylinder(P.M4_INSERT_HOLE_D, bar_back_r - _OVER, P.B_FACE_R + _OVER, t, bar_z)
                 for t in bar_ts]
    pull_holes = [b_post(r, t, P.M4_INSERT_HOLE_D, z0 - _OVER, z0 + P.M4_INSERT_HOLE_DEPTH)
                  for r, t in P.B_PULL_POINTS]
    runouts = [b_post(r, t, P.M4_CLEAR_D, z0, pull_top) for r, t in P.B_PULL_POINTS]
    groove = [b_block(*P.B_GROOVE_R, t0, t1, z0 - _OVER, z0 + P.B_GROOVE_DEPTH)
              for t0, t1 in rail_spans(0.0)]
    pocket_top = bar_top_z - P.B_POCKET_TOP_BELOW
    pocket = b_block(P.B_FACE_R - P.B_POCKET_DEPTH, P.B_FACE_R + _OVER,
                     -P.B_POCKET_HALF_T, P.B_POCKET_HALF_T, pocket_top - P.B_POCKET_H, pocket_top)
    body = body.cut(*bar_holes, *pull_holes, *runouts, *groove, pocket)
    return Part([body.clean()])
