import math

import pytest

from housing import params as P
from housing.analysis import (convex_hull, loose_disc_envelope, ridge_cantilever, screw_shear_n,
                              support_margin, support_reactions)

def stops(gap=P.STOP_GAP):
    return [(P.STOP_R, a, gap) for a in P.STOP_ANGLES]


def test_stops_are_first_contact():
    e = loose_disc_envelope(stops())
    assert e["hub_lift"] <= P.STOP_GAP + 1e-6
    assert e["rim_rise"] <= 1.05                            # spec: 1.0
    assert e["z_at_c"] <= 0.75                              # spec: 0.73, C at 1.0 keeps >= 0.25
    assert e["drop_at_b"] <= 0.61                           # spec: 0.59, B at 1.0 keeps >= 0.39


def test_single_thumb_is_not_enough():
    e = loose_disc_envelope([(95.5, 180.0, 1.0), (60.0, 0.0, 1.0)], ring=(28.0, 2.0))
    assert e["rim_rise"] > 3.0


def test_fault_load_path():
    d, s = ridge_cantilever(20.0, P.DRUM_R_IN - P.STOP_R)
    assert d <= 0.12
    assert ridge_cantilever(100.0, P.DRUM_R_IN - P.STOP_R)[1] <= 26.0
    assert screw_shear_n(100.0) == pytest.approx(16.7, abs=0.1)


def test_convex_hull():
    square = [(0, 0), (4, 0), (4, 4), (0, 4)]
    assert sorted(convex_hull(square + [(2, 2), (2, 0)])) == sorted(square)   # inner and edge points dropped
    assert len(convex_hull([(0, 0), (1, 1), (2, 2)])) < 3                     # collinear: no area


def test_support_margin():
    tri = [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]
    assert support_margin(tri, (2.0, 3.0)) == pytest.approx(2.0)              # nearest edge: x = 0
    assert support_margin(tri, (1.0, 1.0)) == pytest.approx(1.0)
    assert support_margin(tri, (-1.0, 1.0)) == pytest.approx(-1.0)            # outside
    assert support_margin([(0, 0), (5, 0), (10, 0)], (5, 1)) == -math.inf     # a line holds nothing


def test_support_reactions():
    tri = [(0.0, 0.0), (6.0, 0.0), (0.0, 6.0)]
    assert support_reactions(tri, [(2.0, 2.0, 3.0)]) == pytest.approx([1.0, 1.0, 1.0])  # at the centroid
    r = support_reactions(tri, [(1.0, 1.0, 1.0), (4.0, 1.0, 1.0)])
    assert sum(r) == pytest.approx(2.0) and min(r) > 0
    assert min(support_reactions(tri, [(7.0, 1.0, 1.0)])) < 0                   # outside: one lifts
