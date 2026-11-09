import math
from functools import cache

import pytest
from build123d import Align, Axis, Cylinder, GeomType, Pos, Vector, Vertex

from housing import params as P
from housing import reference
from housing.analysis import convex_hull, support_margin, support_reactions
from housing.b_frame import b_block
from housing.b_head import build_b_head, head_bottom_z
from housing.base import lower_tower
from housing.checks import min_clearance, overlap_volume

_MIN = (Align.CENTER, Align.CENTER, Align.MIN)
_MAX = (Align.CENTER, Align.CENTER, Align.MAX)
_COS, _SIN = math.cos(math.radians(P.B_PHI)), math.sin(math.radians(P.B_PHI))
_RADIAL = Vector(_COS, -_SIN, 0)
_TANGENT = Vector(_SIN, _COS, 0)
_TIP_D = 4.0                     # an M4 set screw's end
_TILT_DEG = 0.3                  # Ruling 21's rotation check
# Standard lengths: ISO 4762 M4 socket head screws, ISO 4026 M4 flat-point set screws.
_ISO_4762_M4 = (5, 6, 8, 10, 12, 16, 20, 25, 30, 35, 40)
_ISO_4026_M4 = (4, 5, 6, 8, 10, 12, 16, 20)
# The radii of B's screw and insert holes: inserts, screw bores, the pull's counterbore, the
# push inserts' recess.
_HOLE_RADII = (P.M4_INSERT_HOLE_D / 2, P.M4_CLEAR_D / 2, P.B_PULL_CBORE_D / 2, P.B_PUSH_RECESS_D / 2)


@cache
def _head(top):
    return build_b_head(top)


@cache
def _tower():
    return lower_tower()


def _at(r, t, z):
    return Vector(*P.pol(r, P.B_PHI, t), z)


def _b_holes(part, radii=_HOLE_RADII):
    """(r, t, radius, z0, z1) of the part's vertical cylindrical faces near B whose radius is one
    of `radii` and whose axis is open (a hole, not a rounded corner)."""
    found = set()
    for f in part.faces().filter_by(GeomType.CYLINDER):
        axis = f.axis_of_rotation
        if (f.radius is None or abs(abs(axis.direction.Z) - 1) > 1e-6
                or not any(abs(f.radius - rad) < 1e-3 for rad in radii)):
            continue
        dx, dy = axis.position.X - P.SPINDLE[0], axis.position.Y - P.SPINDLE[1]
        r, t = dx * _COS - dy * _SIN, dx * _SIN + dy * _COS
        bb = f.bounding_box()
        if not (60 < r < 100 and abs(t) < 30) or part.is_inside(_at(r, t, (bb.min.Z + bb.max.Z) / 2)):
            continue
        found.add((round(r, 3), round(t, 3), round(f.radius, 3), round(bb.min.Z, 3), round(bb.max.Z, 3)))
    return sorted(found)


def _vertical_holes(part, d):
    """B-local (r, t) of the axes of the part's vertical holes of diameter d near B."""
    return sorted({(r, t) for r, t, *_ in _b_holes(part, (d / 2,))})


def _same_points(a, b):
    return len(a) == len(b) and all(math.dist(p, q) < 1e-3 for p, q in zip(sorted(a), sorted(b)))


@pytest.mark.parametrize("top", [21.5, 24.0, 24.5])
def test_head_range_and_height(top):
    h = build_b_head(top)
    assert h.bounding_box().max.Z <= 24.0 + 1e-6                        # nothing above Z 24
    gap = head_bottom_z(top) - P.B_LOWER_TOP_Z
    assert 0.5 - 1e-6 <= gap <= 3.5 + 1e-6 and 5.0 - gap >= 1.5 - 1e-6   # tongue stays engaged


@pytest.mark.parametrize("top", [21.5, 24.0, 24.5])
def test_head_is_one_valid_solid(top):
    h = _head(top)
    assert h.is_valid and len(h.solids()) == 1


def test_lower_tower_is_one_valid_solid():
    assert _tower().is_valid and len(_tower().solids()) == 1


def test_bar_inserts_at_37mm_and_5_below_top():
    h = build_b_head(24.0)
    rim = P.M4_INSERT_HOLE_D / 2 + P.B_MIN_PLASTIC
    behind = P.B_FACE_R - P.B_WALL_T - 1.0                               # only the boss holds it here
    for t in (-18.5, 18.5):
        x, y = P.pol(P.B_FACE_R - 3.0, P.B_PHI, t)
        assert not h.is_inside(Vector(x, y, 19.0))                       # insert hole on the axis
        assert h.is_inside(Vector(x, y, 19.0 + 4.0))                     # material above it
        for dt, dz in ((rim, 0.0), (-rim, 0.0), (0.0, -rim)):            # B_MIN_PLASTIC beside and below
            assert h.is_inside(_at(behind, t + dt, 19.0 + dz))
    # Above the hole there is less: the axis is B_HOLE_BELOW_TOP under the bar top (the user's
    # bar) and the head's top B_HEAD_TOP_BELOW_BAR under it (nothing above Z 24 at the top of
    # the range), which leaves 1.7.
    above = P.B_HOLE_BELOW_TOP - P.B_HEAD_TOP_BELOW_BAR - P.M4_INSERT_HOLE_D / 2
    assert above == pytest.approx(1.7)


def test_b_parts_clear_the_drive():
    for top in (21.5, 24.5):
        assert min_clearance(build_b_head(top), reference.drive_box()) >= P.B_DRIVE_CLEARANCE
    assert min_clearance(lower_tower(), reference.drive_box()) >= P.B_DRIVE_CLEARANCE   # from housing.base


def test_coil_fits_head_and_base(base):
    for top in (21.5, 24.5):
        coil = reference.coil_b(top)
        assert overlap_volume(coil, build_b_head(top)) == pytest.approx(0, abs=1e-2)
        assert overlap_volume(coil, base) == pytest.approx(0, abs=1e-2)


def test_head_rides_on_the_tower_without_touching():
    for top in P.B_BAR_TOP_RANGE:
        assert overlap_volume(_head(top), _tower()) == pytest.approx(0, abs=1e-6)
        assert min_clearance(_head(top), _tower()) >= P.B_TONGUE_CLEAR - 1e-3


def test_tongue_locates_the_head_at_the_largest_gap():
    head = _head(P.B_BAR_TOP_RANGE[1])
    shift = P.B_TONGUE_CLEAR + 0.1
    for v in (_RADIAL, -_RADIAL, _TANGENT, -_TANGENT):
        assert overlap_volume(Pos(*(v * shift)) * head, _tower()) > 0


def test_three_pushes_round_the_pull(base):
    """Ruling 21, read from the holes in the parts.

    Three push inserts in the lower tower span a triangle, and every pull insert in the head
    lies at least B_SUPPORT_MARGIN inside it: the pull's preload presses the head onto all three
    pushes (every reaction positive) and leaves no couple for the tongue. The base's bores line
    up: a pull bore under each pull insert, a set-screw bore over each push insert.
    """
    pushes = _vertical_holes(base, P.M4_INSERT_HOLE_D)
    pulls = _vertical_holes(_head(P.B_BAR_TOP_NOM), P.M4_INSERT_HOLE_D)
    assert len(pushes) == 3 and len(convex_hull(pushes)) == 3, f"push inserts at {pushes}"
    assert pulls
    for q in pulls:
        assert support_margin(pushes, q) >= P.B_SUPPORT_MARGIN, f"pull {q}, pushes {pushes}"
    assert min(support_reactions(pushes, [(r, t, 1.0) for r, t in pulls])) > 0
    assert _same_points(pushes, P.B_PUSH_POINTS) and _same_points(pulls, P.B_PULL_POINTS)
    bores = _vertical_holes(base, P.M4_CLEAR_D)
    for p in (*pulls, *pushes):
        assert any(math.dist(p, b) < 1e-3 for b in bores), p


@pytest.mark.parametrize("top", P.B_BAR_TOP_RANGE)
def test_pull_preload_cannot_tip_the_head(base, top):
    """Ruling 21's rotation check.

    A set screw's end (Ø4) stands on each push insert, its top at the head's underside. For each
    edge of the push hull, turning the head _TILT_DEG about that edge in the sense the pull's
    preload drives it (the pull points go down) must drive the head into a push tip off that
    edge: a screw blocks the turn, not the tongue. As built, the head only touches the tips.
    """
    head, z0 = _head(top), head_bottom_z(top)
    pushes = _vertical_holes(base, P.M4_INSERT_HOLE_D)
    pulls = _vertical_holes(head, P.M4_INSERT_HOLE_D)
    tips = {p: Pos(_at(*p, z0)) * Cylinder(_TIP_D / 2, 0.5, align=_MAX) for p in pushes}
    for tip in tips.values():
        assert overlap_volume(head, tip) == pytest.approx(0, abs=1e-6)
    hull = convex_hull(pushes)
    edges = list(zip(hull, hull[1:] + hull[:1])) if len(hull) >= 3 else [tuple(hull)]
    for a, b in edges:
        axis = Axis(_at(*a, z0), _at(*b, z0) - _at(*a, z0))
        sense = next((s for s in (1, -1)                                  # Vertex: turns about the axis's line
                      if all(Vertex(_at(*q, z0)).rotate(axis, s * _TILT_DEG).Z < z0 for q in pulls)), None)
        assert sense is not None, f"pulls on both sides of the pushes {a}, {b}"
        tilted = head.rotate(axis, sense * _TILT_DEG)
        blocking = [p for p in pushes if p not in (a, b) and overlap_volume(tilted, tips[p]) > 0.1]
        assert blocking, f"turning about the pushes {a}, {b} meets no push tip"


def test_pull_screw_path(base):
    """From the floor underside: the socket head flush in its counterbore, the shank through the
    tower's bore, the thread in the head's insert hole, the tip in a narrower blind run-out."""
    bearing = (P.M4_CLEAR_D + P.B_PULL_CBORE_D) / 4                     # between bore and counterbore
    insert = (P.M4_CLEAR_D + P.M4_INSERT_HOLE_D) / 4                     # between bore and insert hole
    for r, t in P.B_PULL_POINTS:
        x, y = P.pol(r, P.B_PHI, t)
        shank = Pos(x, y, P.FLOOR_UNDER_Z) * Cylinder(P.M4_CLEAR_D / 2 - 0.1,
                                                      P.B_LOWER_TOP_Z - P.FLOOR_UNDER_Z, align=_MIN)
        socket = Pos(x, y, P.FLOOR_UNDER_Z) * Cylinder(P.B_PULL_CBORE_D / 2 - 0.1, P.B_PULL_CBORE_DEPTH,
                                                       align=_MIN)
        assert overlap_volume(base, shank + socket) == pytest.approx(0, abs=1e-6)
        assert base.is_inside(_at(r + bearing, t, P.FLOOR_UNDER_Z + P.B_PULL_CBORE_DEPTH + 0.3))
        for top in P.B_BAR_TOP_RANGE:
            head, z0 = _head(top), head_bottom_z(top)
            for dz in (0.3, P.M4_INSERT_HOLE_DEPTH - 0.3):                # the insert hole, from below
                assert not head.is_inside(_at(r + insert, t, z0 + dz))
            runout = z0 + P.M4_INSERT_HOLE_DEPTH
            assert head.is_inside(_at(r + insert, t, runout + 0.3))      # narrower above
            assert not head.is_inside(_at(r, t, runout + 0.3))
            assert not head.is_inside(_at(r, t, runout + P.B_PULL_RUNOUT - 0.3))
            assert head.is_inside(_at(r, t, runout + P.B_PULL_RUNOUT + 0.3))   # blind


def test_push_screw_path(base):
    """From the floor underside: a recess up to the insert, the insert hole, a clear bore to the
    tower's top, and the screw's end fully on the head's underside over the range (with the
    head shifted as far as the tongue lets it)."""
    ins = P.FLOOR_UNDER_Z + P.B_PUSH_RECESS                               # insert's lower end
    recess = (P.M4_INSERT_HOLE_D + P.B_PUSH_RECESS_D) / 4                 # between insert hole and recess
    insert = (P.M4_CLEAR_D + P.M4_INSERT_HOLE_D) / 4                      # between bore and insert hole
    for r, t in P.B_PUSH_POINTS:
        x, y = P.pol(r, P.B_PHI, t)
        assert not base.is_inside(_at(r + recess, t, P.FLOOR_UNDER_Z + P.B_PUSH_RECESS / 2))
        assert base.is_inside(_at(r + recess, t, ins + 0.3))              # the recess stops there
        for dz in (0.3, P.M4_INSERT_HOLE_DEPTH - 0.3):                    # the Ø5.6 hole, not just the bore
            assert not base.is_inside(_at(r + insert, t, ins + dz))
        assert base.is_inside(_at(r + insert, t, ins + P.M4_INSERT_HOLE_DEPTH + 0.3))
        screw = Pos(x, y, ins) * Cylinder(_TIP_D / 2, P.B_LOWER_TOP_Z - ins, align=_MIN)
        assert overlap_volume(base, screw) == pytest.approx(0, abs=1e-6)
        for top in P.B_BAR_TOP_RANGE:                                     # bears on the head's underside
            tip = Pos(x, y, head_bottom_z(top)) * Cylinder(_TIP_D / 2 + P.B_TONGUE_CLEAR, 0.3, align=_MIN)
            assert overlap_volume(_head(top), tip) == pytest.approx(tip.volume, rel=1e-6)


@pytest.mark.parametrize("which", ["base", "head"])
def test_plastic_round_every_hole(base, which):
    """B_MIN_PLASTIC of plastic all round every insert hole, bore, counterbore and recess of B's
    mount, over its whole length: a ring that thick round each hole lies wholly in the part.
    This also keeps the webs between neighbouring holes at least that thick."""
    part = base if which == "base" else _head(P.B_BAR_TOP_NOM)
    holes = _b_holes(part)
    n_screws = len(P.B_PUSH_POINTS) + len(P.B_PULL_POINTS)
    assert len({(r, t) for r, t, *_ in holes}) == (n_screws if which == "base" else len(P.B_PULL_POINTS))
    for r, t, rad, z0, z1 in holes:
        h = z1 - z0 - 0.1
        ring = Pos(_at(r, t, z0 + 0.05)) * (Cylinder(rad + P.B_MIN_PLASTIC, h, align=_MIN)
                                            - Cylinder(rad, h, align=_MIN))
        assert overlap_volume(part, ring) == pytest.approx(ring.volume, rel=1e-6), (r, t, rad, z0)


def test_screw_lengths_cover_the_gap_range():
    assert P.B_PULL_SCREW_LEN in _ISO_4762_M4 and P.B_PUSH_SCREW_LEN in _ISO_4026_M4
    low, high = (head_bottom_z(top) for top in P.B_BAR_TOP_RANGE)
    # Pull: socket head flush in its counterbore; tip in the head's insert, short of the run-out's end.
    tip = P.FLOOR_UNDER_Z + P.B_PULL_CBORE_DEPTH + P.B_PULL_SCREW_LEN
    for z0 in (low, high):
        assert min(tip - z0, P.M4_INSERT_LEN) >= P.B_MIN_ENGAGEMENT
        assert tip <= z0 + P.M4_INSERT_HOLE_DEPTH + P.B_PULL_RUNOUT - P.B_SCREW_TIP_SPARE

    # Push: in the insert at the tower's bottom; its tip reaches the head at the largest gap,
    # and with its lower end flush with the floor underside it is below the tower top.
    ins = (P.FLOOR_UNDER_Z + P.B_PUSH_RECESS, P.FLOOR_UNDER_Z + P.B_PUSH_RECESS + P.M4_INSERT_LEN)

    def engaged(tip):
        return min(tip, ins[1]) - max(tip - P.B_PUSH_SCREW_LEN, ins[0])

    assert engaged(high) >= P.B_MIN_ENGAGEMENT
    retracted = P.FLOOR_UNDER_Z + P.B_PUSH_SCREW_LEN
    assert retracted < P.B_LOWER_TOP_Z and engaged(retracted) >= P.B_MIN_ENGAGEMENT


def test_relief_pocket_behind_the_coil():
    top = P.B_BAR_TOP_NOM
    head = _head(top)
    z_hi, z_lo = top - P.B_POCKET_TOP_BELOW, top - P.B_POCKET_TOP_BELOW - P.B_POCKET_H
    in_pocket = P.B_FACE_R - P.B_POCKET_DEPTH / 2
    for t in (-(P.B_POCKET_HALF_T - 0.5), 0.0, P.B_POCKET_HALF_T - 0.5):
        assert not head.is_inside(_at(in_pocket, t, z_hi - 0.3))
        assert not head.is_inside(_at(in_pocket, t, z_lo + 0.3))
    assert head.is_inside(_at(in_pocket, 0.0, z_hi + 0.3))
    assert head.is_inside(_at(in_pocket, 0.0, z_lo - 0.3))
    assert head.is_inside(_at(P.B_FACE_R - P.B_POCKET_DEPTH - 0.3, 0.0, (z_hi + z_lo) / 2))
    assert head.is_inside(_at(in_pocket, P.B_POCKET_HALF_T + 0.5, (z_hi + z_lo) / 2))


def test_ledge_under_the_coil_body():
    depth, width, height = P.B_BODY
    assert P.B_LEDGE_T >= 6.0
    for top in P.B_BAR_TOP_RANGE:
        head, z0 = _head(top), head_bottom_z(top)
        body_bottom = top - height
        assert body_bottom - (z0 + P.B_LEDGE_T) >= 1.0 - 1e-6
        for r, t in P.B_PUSH_POINTS:                                      # B_LEDGE_T of plastic over each push
            assert head.is_inside(_at(r, t, z0 + P.B_LEDGE_T - 0.3))
        under_body = b_block(P.B_FACE_R, P.B_FACE_R + depth, -width / 2, width / 2,
                             body_bottom - 1.0, body_bottom)
        assert overlap_volume(head, under_body) == pytest.approx(0, abs=1e-6)
