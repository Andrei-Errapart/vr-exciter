"""Sensor B's local frame, shared by the head (b_head.py) and the lower tower (base.py).

B's parts are built with r along +X (radial) and t along +Y (tangential), then turned to B_PHI
about the spindle like params.pol(). Also here: the tongue and groove's spans, which both parts
need.
"""
from build123d import Box, Cylinder, Face, Part, Pos, Rot, Sketch, extrude

from housing import params as P
from housing.joint import at_phi


def b_block(r0: float, r1: float, t0: float, t1: float, z0: float, z1: float) -> Part:
    """A box r0…r1, t0…t1, z0…z1 in B's local frame, turned to B_PHI."""
    return at_phi(Pos((r0 + r1) / 2, (t0 + t1) / 2, (z0 + z1) / 2) * Box(r1 - r0, t1 - t0, z1 - z0),
                  P.B_PHI)


def b_post(r: float, t: float, d: float, z0: float, z1: float) -> Part:
    """A vertical cylinder of diameter d on B's local (r, t), z0…z1."""
    return at_phi(Pos(r, t, (z0 + z1) / 2) * Cylinder(d / 2, z1 - z0), P.B_PHI)


def b_radial_cylinder(d: float, r0: float, r1: float, t: float, z: float) -> Part:
    """A cylinder of diameter d along the radius, r0…r1, on B's local t at height z."""
    return at_phi(Pos((r0 + r1) / 2, t, z) * Rot(0, 90, 0) * Cylinder(d / 2, r1 - r0), P.B_PHI)


def b_prism(outline: Face | Sketch, z0: float, z1: float) -> Part:
    """A 2D outline drawn in B's local (r, t), extruded z0…z1 and turned to B_PHI.

    Upwards whichever way round the outline runs (a clockwise one faces down).
    """
    return at_phi(Pos(0, 0, z0) * extrude(outline, z1 - z0, dir=(0, 0, 1)), P.B_PHI)


def rail_spans(inset: float) -> list[tuple[float, float]]:
    """Tangential spans of the groove (inset 0) or the tongue (inset B_TONGUE_CLEAR).

    The groove runs ±B_GROOVE_HALF_T but stops B_PULL_LAND_HALF_T either side of each pull
    screw, which crosses its line; the tongue keeps `inset` inside it at every end.
    """
    lands = sorted((t - P.B_PULL_LAND_HALF_T, t + P.B_PULL_LAND_HALF_T) for _, t in P.B_PULL_POINTS)
    spans, start = [], -P.B_GROOVE_HALF_T
    for lo, hi in lands:
        spans.append((start, lo))
        start = hi
    spans.append((start, P.B_GROOVE_HALF_T))
    return [(t0 + inset, t1 - inset) for t0, t1 in spans if t1 - t0 > 2 * inset]
