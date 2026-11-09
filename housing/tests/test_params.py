import pytest

from housing import params as P


def test_pol_matches_spec_positions():
    assert P.pol(95.5, 180) == pytest.approx((-95.3, 95.9), abs=0.05)   # C axis
    assert P.pol(95.5, 20) == pytest.approx((89.94, 63.24), abs=0.05)   # B pole


def test_drum_outline_flat_and_radius():
    f = P.drum_outline(P.DRUM_R_IN, P.FLAT_Y_IN)
    bb = f.bounding_box()
    assert bb.min.Y == pytest.approx(-10.0, abs=1e-3)
    assert bb.max.Y == pytest.approx(95.9 + 113.0, abs=1e-3)
    assert bb.max.X == pytest.approx(0.2 + 113.0, abs=1e-3)


def test_feet_inside_drum():
    for phi in P.FEET_ANGLES:
        x, y = P.pol(P.FEET_R, phi)
        assert ((x - 0.2) ** 2 + (y - 95.9) ** 2) ** 0.5 < P.DRUM_R_IN
