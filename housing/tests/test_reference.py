import math

import pytest
from build123d import Box, Pos, Vector

from housing import params as P
from housing import reference
from housing.checks import circle_fraction, min_clearance, overlap_volume
from housing.reference import BOARD_TEST_PCB, ROOT, footprint_positions

J1_AT = "(at 124.65 46.75"     # J1's position in the test PCB, KiCad coordinates


def test_footprint_positions_parse_current_pcb():
    pos = footprint_positions((ROOT / "hdd-driver/hdd-driver.kicad_pcb").read_text())
    assert pos["J1"][:2] == pytest.approx((-25.35, 6.75), abs=0.01)
    assert pos["J3"][:2] == pytest.approx((24.71, 4.61), abs=0.01)
    assert pos["U1"] == pytest.approx((-2.05, 19.67, -90.0), abs=0.01)


def test_board_orientation(board):
    # measured: X -36…38, Y 0…73, Z -21.93…4.49
    bb = board.bounding_box()
    assert -22.5 <= bb.min.Z <= -21.4          # modules hang below the drive; lowest: SimpleFOC's C3
    assert bb.max.Z <= 5.0                      # only leads through the board rise above Z 0
    assert -37.0 <= bb.min.X and bb.max.X <= 39.0
    assert -1.5 <= bb.min.Y and bb.max.Y <= 75.0


def test_stale_board_export_is_rejected(tmp_path, monkeypatch):
    text = BOARD_TEST_PCB.read_text()
    assert J1_AT in text
    stale = tmp_path / "hdd-driver-test.kicad_pcb"
    stale.write_text(text.replace(J1_AT, "(at 120.1 100.0", 1))
    monkeypatch.setattr(reference, "BOARD_TEST_PCB", stale)
    with pytest.raises(RuntimeError, match="export-test-model"):
        reference.load_board()


def test_missing_board_export_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(reference, "BOARD_STEP", tmp_path / "test-assembly.step")
    with pytest.raises(RuntimeError, match="export-test-model"):
        reference.load_board()


def test_board_features_inside_their_modules():
    for x, y in P.WEACT_BUTTONS:
        assert -16.7 <= x <= 12.6 and 1.0 <= y <= 38.4
    x, y = P.MT3608_TRIMMER
    assert -35.0 <= x <= -16.6 and 15.3 <= y <= 53.6
    assert -10.0 <= P.J1_WIRE_Z <= -2.0
    assert -18.0 <= P.USB_CENTRE_XZ[1] <= -13.0


def test_board_features_match_the_export():
    """The recorded literals still describe the exported board (re-measure if not)."""
    boxes = reference.named_bboxes(reference.BOARD_STEP)
    for (x, y), sw in zip(P.WEACT_BUTTONS, ("SW1", "SW2", "SW3")):
        c = boxes[sw].center()
        assert (x, y) == pytest.approx((c.X, c.Y), abs=0.01)
    pot = boxes["Potentiometer_Bourns_3296W_Vertical"]
    x, y = P.MT3608_TRIMMER
    assert pot.min.X + 1.1 <= x <= pot.max.X - 1.1 and pot.min.Y + 1.1 <= y <= pot.max.Y - 1.1
    j1 = boxes["TerminalBlock_Phoenix_MKDS-1,5-2-5_08_1x02_P5_08mm_Horizontal"]
    assert j1.min.Z < P.J1_WIRE_Z < -1.6                                  # between free side and board
    usb = boxes["USB_TYPEC16-7R35x8R94"]
    assert P.USB_CENTRE_XZ[0] == pytest.approx(usb.center().X, abs=0.01)
    assert usb.min.Z < P.USB_CENTRE_XZ[1] < usb.max.Z


def test_circle_fraction_single_hole():
    # one Ø4 hole centred on r 50: 4/(2π·50) of the circle
    assert circle_fraction([P.pol(50, 0)], 4.0, 50.0) == pytest.approx(4 / (2 * math.pi * 50), rel=0.02)


def test_circle_fraction_ignores_holes_off_the_circle():
    assert circle_fraction([P.pol(50, 0), P.pol(60, 90)], 4.0, 50.0) == pytest.approx(
        circle_fraction([P.pol(50, 0)], 4.0, 50.0))


def test_overlap_and_clearance():
    a = Box(10, 10, 10)
    assert overlap_volume(a, Pos(5, 0, 0) * Box(10, 10, 10)) == pytest.approx(500.0)
    assert overlap_volume(a, Pos(20, 0, 0) * Box(10, 10, 10)) == 0.0
    assert min_clearance(a, Pos(20, 0, 0) * Box(10, 10, 10)) == pytest.approx(10.0)


def test_drive_and_disc_envelopes(drive, disc):
    bb = drive.bounding_box()
    assert (bb.min.X, bb.min.Y, bb.min.Z) == pytest.approx((-50.8, 0.0, 0.0))
    assert (bb.max.X, bb.max.Y, bb.max.Z) == pytest.approx((50.8, 147.0, 22.66))
    bb = disc.bounding_box()
    assert bb.center().X == pytest.approx(P.SPINDLE[0]) and bb.center().Y == pytest.approx(P.SPINDLE[1])
    assert bb.size.X == pytest.approx(2 * P.DISC_R)
    assert (bb.min.Z, bb.max.Z) == pytest.approx((25.0, 33.4))


def test_coil_b_on_the_tower_face():
    coil = reference.coil_b(24.0)
    bb = coil.bounding_box()
    assert (bb.min.Z, bb.max.Z) == pytest.approx((24.0 - 19.4, 24.0))
    assert coil.is_inside(Vector(*P.pol(P.MAGNET_R, P.B_PHI), 23.5))          # pole under the magnets
    assert coil.is_inside(Vector(*P.pol(P.B_FACE_R + 0.6, P.B_PHI, 22.5), 13.0))   # bar end
    assert not coil.is_inside(Vector(*P.pol(P.B_FACE_R - 0.1, P.B_PHI), 20.0))     # nothing behind the face
    assert not coil.is_inside(Vector(*P.pol(P.B_FACE_R + 23.1, P.B_PHI), 20.0))    # body ends at r 102.5


def test_sensor_c_tip_and_nut():
    c = reference.sensor_c(1.0)
    bb = c.bounding_box()
    assert bb.min.Z == pytest.approx(P.DISC_TOP_Z[1] + 1.0)
    x, y = P.pol(P.MAGNET_R, P.C_PHI)
    assert bb.center().X == pytest.approx(x) and bb.center().Y == pytest.approx(y)
    assert c.is_inside(Vector(x + 11.9, y, P.PLATE_Z[1] + 6.0))               # nut, 24 AF
    assert not c.is_inside(Vector(x + 11.9, y, P.PLATE_Z[1] - 1.0))           # only the shank below the plate


def test_usb_plug_probe():
    bb = reference.usb_plug_probe().bounding_box()
    x, z = P.USB_CENTRE_XZ
    assert (bb.min.Y, bb.max.Y) == pytest.approx((-15.0, -2.7))
    assert bb.center().X == pytest.approx(x) and bb.center().Z == pytest.approx(z)
    assert (bb.size.X, bb.size.Z) == pytest.approx((13.6, 8.6))
