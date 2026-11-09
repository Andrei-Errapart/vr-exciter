import math
from functools import cache

import pytest
from build123d import Align, Cylinder, GeomType, Pos, Vector

from housing import params as P
from housing import reference
from housing.b_head import b_block, build_b_head, head_bottom_z
from housing.base import lower_tower
from housing.checks import min_clearance, overlap_volume

_MIN = (Align.CENTER, Align.CENTER, Align.MIN)
_RADIAL = Vector(math.cos(math.radians(P.B_PHI)), -math.sin(math.radians(P.B_PHI)), 0)
_TANGENT = Vector(math.sin(math.radians(P.B_PHI)), math.cos(math.radians(P.B_PHI)), 0)


@cache
def _head(top):
    return build_b_head(top)


@cache
def _tower():
    return lower_tower()


def _at(r, t, z):
    return Vector(*P.pol(r, P.B_PHI, t), z)


def _vertical_holes(part, d):
    """B-local (r, t) of the axes of the part's vertical cylindrical faces of diameter d near B."""
    c, s = math.cos(math.radians(P.B_PHI)), math.sin(math.radians(P.B_PHI))
    found = set()
    for f in part.faces().filter_by(GeomType.CYLINDER):
        axis = f.axis_of_rotation
        if f.radius is None or abs(f.radius - d / 2) > 1e-3 or abs(abs(axis.direction.Z) - 1) > 1e-6:
            continue
        dx, dy = axis.position.X - P.SPINDLE[0], axis.position.Y - P.SPINDLE[1]
        r, t = dx * c - dy * s, dx * s + dy * c
        if 60 < r < 100 and abs(t) < 30:
            found.add((round(r, 3), round(t, 3)))
    return sorted(found, key=lambda rt: rt[1])


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


def test_bar_inserts_at_37mm_and_5_below_top():
    h = build_b_head(24.0)
    for t in (-18.5, 18.5):
        x, y = P.pol(P.B_FACE_R - 3.0, P.B_PHI, t)
        assert not h.is_inside(Vector(x, y, 19.0))                       # insert hole on the axis
        assert h.is_inside(Vector(x, y, 19.0 + 4.0))                     # material around it


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


def test_pull_screw_path(base):
    for t in (-P.B_PULL_T, P.B_PULL_T):
        x, y = P.pol(P.B_SCREW_R, P.B_PHI, t)
        shank = Pos(x, y, P.FLOOR_UNDER_Z) * Cylinder(P.M4_CLEAR_D / 2 - 0.1,
                                                      P.B_LOWER_TOP_Z - P.FLOOR_UNDER_Z, align=_MIN)
        socket = Pos(x, y, P.FLOOR_UNDER_Z) * Cylinder(P.B_CBORE_D / 2 - 0.1, P.B_PULL_CBORE_DEPTH,
                                                       align=_MIN)
        assert overlap_volume(base, shank + socket) == pytest.approx(0, abs=1e-6)
        assert base.is_inside(_at(P.B_SCREW_R + 3.0, t, P.FLOOR_UNDER_Z + P.B_PULL_CBORE_DEPTH + 0.3))
        for d in (-1, 1):                                                 # >= 2 mm round the bore
            assert base.is_inside(_at(P.B_SCREW_R + d * (P.M4_CLEAR_D / 2 + 2.0), t, -12.0))
        for top in P.B_BAR_TOP_RANGE:                                     # its insert in the head
            head, z0 = _head(top), head_bottom_z(top)
            assert not head.is_inside(_at(P.B_SCREW_R, t, z0 + 0.3))
            assert not head.is_inside(_at(P.B_SCREW_R, t, z0 + P.M4_INSERT_HOLE_DEPTH - 0.3))
            runout = z0 + P.M4_INSERT_HOLE_DEPTH + 0.3                    # narrower run-out above
            assert not head.is_inside(_at(P.B_SCREW_R, t, runout))
            assert head.is_inside(_at(P.B_SCREW_R + P.M4_CLEAR_D / 2 + 0.3, t, runout))
            assert head.is_inside(_at(P.B_SCREW_R, t, runout + P.B_PULL_RUNOUT))  # blind
            rim = P.M4_INSERT_HOLE_D / 2 + 1.9
            for dr, dt in ((rim, 0), (-rim, 0), (0, rim), (0, -rim)):
                assert head.is_inside(_at(P.B_SCREW_R + dr, t + dt, z0 + 0.5))


def test_push_screw_path(base):
    ins = P.FLOOR_UNDER_Z + P.B_PUSH_RECESS                               # insert's lower end
    for t in (-P.B_PUSH_T, P.B_PUSH_T):
        x, y = P.pol(P.B_PUSH_R, P.B_PHI, t)
        assert not base.is_inside(_at(P.B_PUSH_R + 3.5, t, P.FLOOR_UNDER_Z + P.B_PUSH_RECESS / 2))
        assert base.is_inside(_at(P.B_PUSH_R + 3.5, t, ins + 0.3))        # the recess stops there
        assert not base.is_inside(_at(P.B_PUSH_R, t, ins + P.M4_INSERT_HOLE_DEPTH - 0.3))
        rim = P.M4_INSERT_HOLE_D / 2 + 2.0                                # plastic round the insert
        for dr, dt in ((rim, 0), (-rim, 0), (0, rim), (0, -rim)):
            assert base.is_inside(_at(P.B_PUSH_R + dr, t + dt, ins + P.M4_INSERT_LEN - 1.0))
        screw = Pos(x, y, ins) * Cylinder(4.0 / 2, P.B_LOWER_TOP_Z - ins, align=_MIN)
        assert overlap_volume(base, screw) == pytest.approx(0, abs=1e-6)
        for top in P.B_BAR_TOP_RANGE:                                     # bears on the head's underside
            tip = Pos(x, y, head_bottom_z(top)) * Cylinder(4.0 / 2, 0.3, align=_MIN)
            assert overlap_volume(_head(top), tip) == pytest.approx(tip.volume, rel=1e-6)


def test_screw_lengths_cover_the_gap_range():
    low, high = (head_bottom_z(top) for top in P.B_BAR_TOP_RANGE)
    # Pull: socket head flush in its counterbore; tip in the head's insert, short of the run-out's end.
    tip = P.FLOOR_UNDER_Z + P.B_PULL_CBORE_DEPTH + P.B_PULL_SCREW_LEN
    for z0 in (low, high):
        assert min(tip - z0, P.M4_INSERT_LEN) >= P.B_MIN_ENGAGEMENT
        assert tip <= z0 + P.M4_INSERT_HOLE_DEPTH + P.B_PULL_RUNOUT

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


def test_push_line_outside_pull_line_and_both_pairs_wide(base):
    assert P.B_PUSH_R - P.B_SCREW_R >= 7.0
    assert 2 * P.B_PULL_T >= 24.0 and 2 * P.B_PUSH_T >= 24.0
    pulls = _vertical_holes(_head(P.B_BAR_TOP_NOM), P.M4_INSERT_HOLE_D)   # the head's pull inserts
    pushes = _vertical_holes(base, P.M4_INSERT_HOLE_D)                      # the base's push inserts
    assert len(pulls) == 2 and len(pushes) == 2
    assert min(r for r, _ in pushes) - max(r for r, _ in pulls) >= 7.0
    for (_, t0), (_, t1) in (pulls, pushes):
        assert t1 - t0 >= 24.0
    bores = _vertical_holes(base, P.M4_CLEAR_D)                             # the inserts' pull bores
    for r, t in pulls:
        assert any(math.dist((r, t), bore) < 1e-3 for bore in bores)


def test_ledge_under_the_coil_body():
    depth, width, height = P.B_BODY
    assert P.B_LEDGE_T >= 6.0
    for top in P.B_BAR_TOP_RANGE:
        head, z0 = _head(top), head_bottom_z(top)
        body_bottom = top - height
        assert body_bottom - (z0 + P.B_LEDGE_T) >= 1.0 - 1e-6
        for t in (-P.B_PUSH_T, 0.0, P.B_PUSH_T):                          # solid, B_LEDGE_T thick
            assert head.is_inside(_at(P.B_PUSH_R, t, z0 + P.B_LEDGE_T - 0.3))
        under_body = b_block(P.B_FACE_R, P.B_FACE_R + depth, -width / 2, width / 2,
                             body_bottom - 1.0, body_bottom)
        assert overlap_volume(head, under_body) == pytest.approx(0, abs=1e-6)
