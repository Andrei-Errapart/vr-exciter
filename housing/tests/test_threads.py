import pytest

from housing.threads import M16X1_5, UNF_5_8_18, thread_negative


def test_negative_outer_diameter_includes_clearance():
    bb = thread_negative(M16X1_5, 17.0).bounding_box()
    assert bb.size.X == pytest.approx(16.3, abs=0.05)
    assert bb.size.Z == pytest.approx(17.0, abs=0.05)


def test_unf_pitch():
    assert UNF_5_8_18.pitch == pytest.approx(1.4111, abs=1e-4)


def test_negative_starts_at_z0():
    bb = thread_negative(M16X1_5, 10.0).bounding_box()
    assert bb.min.Z == pytest.approx(0.0, abs=0.01)
