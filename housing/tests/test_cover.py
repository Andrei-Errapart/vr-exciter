import pytest
from build123d import Align, Cylinder, Pos, Rot, Vector

from housing import params as P
from housing import reference
from housing.checks import min_clearance, overlap_volume
from housing.coupon import build_thread_coupon
from housing.threads import M16X1_5


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


def test_cover_thread_matches_coupon(cover):
    """Both holes come from thread_negative, placed by translation with the start at their bottom.

    Probed at the same heights above each start (C_BOSS_UNDER_Z in the cover, z 0 in the coupon),
    so the two helices are compared at the same phase. Four heights a quarter pitch apart: at
    5.0 alone, clearances of 0, 0.2 and 0.3 give the same answer.
    """
    x, y = P.pol(P.MAGNET_R, P.C_PHI)
    coupon = build_thread_coupon()
    probe = lambda part, cx, cy, z: [part.is_inside(Vector(cx + r, cy, z)) for r in (7.4, 7.9, 8.2)]
    for dz in (5.0 + k * M16X1_5.pitch / 4 for k in range(4)):
        assert probe(cover, x, y, P.C_BOSS_UNDER_Z + dz) == probe(coupon, -14.0, 0.0, dz)
