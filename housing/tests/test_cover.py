import itertools
import math

import pytest
from build123d import Align, Cylinder, Pos, Rot, Vector

from housing import params as P
from housing import reference
from housing.checks import circle_fraction, min_clearance, overlap_volume
from housing.coupon import HOLE_X, build_thread_coupon
from housing.cover import build_cover, vent_hole_centres
from housing.threads import M16X1_5, UNF_5_8_18, thread_spec

_COUPON_HOLE_X = {M16X1_5: -HOLE_X, UNF_5_8_18: HOLE_X}       # where coupon.py puts each thread


def test_cover_extent(cover):
    bb = cover.bounding_box()
    assert bb.max.Z == pytest.approx(54.4, abs=1e-3) and bb.min.Z == pytest.approx(-12.0, abs=1e-3)
    assert bb.size.X <= P.BED - 2 * P.BED_MARGIN and bb.size.Y <= P.BED - 2 * P.BED_MARGIN


def test_cover_is_one_valid_solid(cover):
    assert cover.is_valid and len(cover.solids()) == 1


def test_nothing_low_over_the_disc(cover):
    zone = Pos(*P.SPINDLE, 25.0) * Cylinder(104.0, 12.4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    assert overlap_volume(cover, zone) == pytest.approx(0, abs=1e-3)              # Z 25…37.4 inside r 104
    assert min_clearance(cover, reference.disc_envelope()) >= 3.99


def test_cover_and_base_touch_only_at_seat(cover, base):
    assert overlap_volume(cover, base) == pytest.approx(0, abs=1e-2)
    assert min_clearance(cover, base) == pytest.approx(0.0, abs=1e-3)


def test_cover_fits_only_one_way(cover, base):
    for turn in (50, 80, 130, 180, 230, 310):
        rotated = Pos(*P.SPINDLE) * Rot(0, 0, turn) * Pos(-P.SPINDLE[0], -P.SPINDLE[1]) * cover
        assert overlap_volume(rotated, base) > 1.0


def test_tab_screw_holes_are_clear(cover):
    """An M4 clearance hole runs radially through each tab; the lip above it must not close its top."""
    probe_d = P.M4_CLEAR_D - 0.1
    for phi in P.TAB_ANGLES:
        x, y = P.pol((P.DRUM_R_MID + P.TAB_R_OUT) / 2, phi)
        bolt = Pos(x, y, P.SCREW_Z) * Rot(0, 0, -phi) * Rot(0, 90, 0) * Cylinder(
            probe_d / 2, P.TAB_R_OUT - P.DRUM_R_MID + 2.0)
        assert overlap_volume(cover, bolt) == pytest.approx(0, abs=1e-3)


def test_ridges_ring_and_boss(cover):
    def at(r, phi, z, t=0.0):
        return Vector(*P.pol(r, phi, t), z)

    z = P.RIDGE_BOTTOM_Z + 0.2
    for k in range(P.RIDGE_N):
        phi = k * 360 / P.RIDGE_N
        for r in (P.RING_R[1] + 1.0, 60.0, 100.0):                    # ring to wall (at C_PHI, r 100 is C's hole)
            if phi != P.C_PHI or r < P.MAGNET_R - P.C_BOSS_D / 2:
                assert cover.is_inside(at(r, phi, z))
        assert not cover.is_inside(at(60.0, phi, P.RIDGE_BOTTOM_Z - 0.2))                   # down to RIDGE_BOTTOM_Z
        assert not cover.is_inside(at(60.0, phi, z, P.RIDGE_T / 2 + 0.2))                   # RIDGE_T thick
        between = phi + 180 / P.RIDGE_N
        assert cover.is_inside(at(sum(P.RING_R) / 2, between, z))                           # ring between ridges
        assert not cover.is_inside(at(P.RING_R[0] - 0.2, between, z))
        assert not cover.is_inside(at(P.RING_R[1] + 0.2, between, z))
    c_t = P.C_BOSS_D / 2 - 1.0                                                              # boss, beside the hole
    assert cover.is_inside(at(P.MAGNET_R, P.C_PHI, P.C_BOSS_UNDER_Z + 0.2, c_t))
    assert not cover.is_inside(at(P.MAGNET_R, P.C_PHI, P.C_BOSS_UNDER_Z - 0.2, c_t))
    web_r = (P.MAGNET_R + P.C_BOSS_D / 2 + P.DRUM_R_IN) / 2                                 # web, boss to wall
    assert cover.is_inside(at(web_r, P.C_PHI, P.C_BOSS_UNDER_Z + 0.2, P.C_WEB_W / 2 - 0.5))
    assert not cover.is_inside(at(web_r, P.C_PHI, P.C_BOSS_UNDER_Z + 0.2, P.C_WEB_W / 2 + 0.5))


def test_c_thread(cover):
    x, y = P.pol(P.MAGNET_R, P.C_PHI)
    assert not cover.is_inside(Vector(x, y, 45.0))
    assert cover.is_inside(Vector(x + 8.6, y, 45.0))
    for z in (P.C_BOSS_UNDER_Z + 0.1, P.PLATE_Z[1] - 0.1):                                 # open at both ends
        assert not cover.is_inside(Vector(x, y, z))


def _thread_probe(part, cx, cy, z):
    return [part.is_inside(Vector(cx + r, cy, z)) for r in (7.4, 7.9, 8.2)]


def _matches_coupon_hole(cover, spec, coupon_spec):
    """The cover's C thread against one of the coupon's holes.

    Both holes come from thread_negative, placed by translation with the start at their bottom.
    Probed at the same heights above each start (C_BOSS_UNDER_Z in the cover, z 0 in the coupon),
    so the two helices are compared at the same phase. Four heights a quarter pitch apart: at
    5.0 alone, clearances of 0, 0.2 and 0.3 give the same answer.
    """
    x, y = P.pol(P.MAGNET_R, P.C_PHI)
    coupon = build_thread_coupon()
    return all(_thread_probe(cover, x, y, P.C_BOSS_UNDER_Z + dz)
               == _thread_probe(coupon, _COUPON_HOLE_X[coupon_spec], 0.0, dz)
               for dz in (5.0 + k * spec.pitch / 4 for k in range(4)))


def test_cover_thread_matches_coupon(cover):
    """The cover is built with the thread named by C_THREAD, the same as the coupon's hole."""
    spec = thread_spec(P.C_THREAD)
    assert _matches_coupon_hole(cover, spec, spec)


def test_cover_takes_the_unf_thread():
    """The 5/8"-18 UNF option (C_THREAD, or make-housing build --c-thread) gives a valid cover
    whose thread is the coupon's UNF hole, not its M16 one."""
    unf = build_cover(UNF_5_8_18)
    assert unf.is_valid and len(unf.solids()) == 1
    assert _matches_coupon_hole(unf, UNF_5_8_18, UNF_5_8_18)
    assert not _matches_coupon_hole(unf, UNF_5_8_18, M16X1_5)


def test_vent_pattern_rules():
    inlet, outlet = vent_hole_centres()
    assert len(inlet) == 43 and 18 <= len(outlet) <= 22
    pts = inlet + outlet
    assert min(math.dist(a, b) for a, b in itertools.combinations(pts, 2)) >= P.VENT_MIN_SPACING - 1e-6
    for r in [x / 10 for x in range(int(P.RING_R[1] * 10), int(P.DRUM_R_IN * 10))]:
        assert circle_fraction(outlet, P.VENT_D, r) <= P.VENT_CIRCLE_MAX + 1e-9
    c = P.pol(P.MAGNET_R, P.C_PHI)
    assert all(math.dist(o, c) >= P.C_BOSS_D / 2 + P.VENT_EDGE_CLEAR + P.VENT_D / 2 for o in outlet)
    assert all(y >= P.FLAT_Y_IN + P.VENT_EDGE_CLEAR + P.VENT_D / 2 for _, y in outlet)


def _dist_to_segment(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def test_vent_edges_clear_wall_ridges_ring_and_stops():
    """Every hole's edge is >= VENT_EDGE_CLEAR from the wall's inner face (r DRUM_R_IN), the
    flat's (FLAT_Y_IN), each ridge, the central ring and each stop boss (Ruling 18).

    A ridge is taken as its centre line from the ring's outer face to the wall's inner face,
    RIDGE_T / 2 to either side; that band holds every point of the ridge's exposed part.
    """
    inlet, outlet = vent_hole_centres()
    reach = P.VENT_D / 2 + P.VENT_EDGE_CLEAR         # from a hole's centre to the nearest face
    for x, y in inlet + outlet:
        rho = math.dist((x, y), P.SPINDLE)
        assert rho <= P.DRUM_R_IN - reach + 1e-6
        assert y >= P.FLAT_Y_IN + reach - 1e-6
        assert rho <= P.RING_R[0] - reach + 1e-6 or rho >= P.RING_R[1] + reach - 1e-6
        for k in range(P.RIDGE_N):
            phi = k * 360 / P.RIDGE_N
            ridge = P.pol(P.RING_R[1], phi), P.pol(P.DRUM_R_IN, phi)
            assert _dist_to_segment((x, y), *ridge) >= P.RIDGE_T / 2 + reach - 1e-6
        for a in P.STOP_ANGLES:
            assert math.dist((x, y), P.pol(P.STOP_R, a)) >= P.STOP_BOSS_D / 2 + reach - 1e-6


def test_vents_are_holes(cover):
    inlet, outlet = vent_hole_centres()
    for x, y in inlet[:3] + outlet[:3]:
        assert not cover.is_inside(Vector(x, y, 53.0))


def test_stop_bosses(cover):
    insert_top = P.STOP_BOSS_BOTTOM_Z + P.M4_INSERT_HOLE_DEPTH
    for a in P.STOP_ANGLES:
        x, y = P.pol(P.STOP_R, a)
        assert not cover.is_inside(Vector(x, y, 45.0))                    # screw path open
        assert cover.is_inside(Vector(x + 4.5, y, 45.0))                  # boss material
        # Nothing under the boss bottom. Ø10, not Ø12 (Ruling 3): the φ 180 boss merges with
        # C's boss, whose edge lies 0.5 mm inside a Ø12 probe.
        below = Pos(x, y, P.STOP_BOSS_BOTTOM_Z - 0.6) * Cylinder(5, 1.0)
        assert overlap_volume(cover, below) == pytest.approx(0, abs=1e-3)
        # The insert hole is M4_INSERT_HOLE_DEPTH deep: probed between the two holes' radii.
        r_probe = P.M4_INSERT_HOLE_D / 2 - 0.2
        assert not cover.is_inside(Vector(x + r_probe, y, insert_top - 0.2))
        assert cover.is_inside(Vector(x + r_probe, y, insert_top + 0.2))
        # The clearance hole runs on through the plate, and no wider.
        assert not cover.is_inside(Vector(x, y, P.PLATE_Z[1] - 0.1))
        assert cover.is_inside(Vector(x + P.M4_CLEAR_D / 2 + 0.2, y, sum(P.PLATE_Z) / 2))
