import pytest
from build123d import Box, Pos, Vector

from housing.coupon import build_thread_coupon


def test_coupon_has_two_through_threads():
    c = build_thread_coupon()
    assert not c.is_inside(Vector(-14, 0, 5)) and not c.is_inside(Vector(14, 0, 5))
    assert c.is_inside(Vector(-14 + 8.6, 0, 5))           # material beyond the major radius
    assert c.bounding_box().size.Z == pytest.approx(10.0, abs=0.01)


def test_labels_are_engraved_into_top_face():
    c = build_thread_coupon()
    for x in (-14, 14):
        top = Pos(x, -11, 9.8) * Box(10, 5, 0.4)      # inside the 0.6 mm engraving depth
        deep = Pos(x, -11, 8.8) * Box(10, 5, 0.4)     # below it: untouched
        assert (c & top).volume < top.volume - 1.0
        assert (c & deep).volume == pytest.approx(deep.volume, rel=1e-3)
