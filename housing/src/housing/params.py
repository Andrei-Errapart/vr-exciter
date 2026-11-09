"""Every spec number for the housing, in mm (angles in degrees).

Drive frame: X, Y in mm (bottom view, connector end at Y 0); Z is height above
the drive underside, positive towards the disc. Polar coordinates about the
spindle: phi from +X, positive towards -Y.
"""
import math

from build123d import Circle, Face, Pos, Rectangle

# --- frame ---
SPINDLE = (0.2, 95.9)
DRIVE_X_HALF = 50.8
DRIVE_LEN = 147.0
DRIVE_TOP_Z = 22.66
HOLES = ((-47.625, 41.28), (47.625, 41.28), (-47.625, 85.73), (47.625, 85.73))
DRIVE_UNDER_Z = 0.0  # the drive's underside; the base touches the drive only here, with its screw bosses

# --- disc ---
DISC_R = 101.0
DISC_UNDER_Z = (25.0, 25.4)
DISC_TOP_Z = (33.0, 33.4)
MAGNET_R = 95.5
HUB_ENGAGEMENT = 8.5
BORE_CLEARANCE = 0.19

# --- tray ---
TRAY_GAP = 0.3
TRAY_WALL = 2.4
TRAY_WALL_TOP_Z = -0.5
# Connector end only: the board's PCB is flush with the drive's end (Y 0) and the WeAct,
# J1 and J3 reach Y 1.4, so a 0.3 mm gap there would leave them < 2 mm from the end wall.
TRAY_END_GAP = 2.5
FLOOR_TOP_Z = -24.5  # 2.57 clear of MODULE_LOW_Z (spec: -21.0 for a -17.6 board)
FLOOR_UNDER_Z = -27.5
BOSS_LEDGE = 3.0
BOSS_CLEAR_D = 3.8
BOSS_BORE_D = 8.0
BOSS_OD = BOSS_BORE_D + 2 * TRAY_WALL  # 12.8; trimmed flush with the tray's outer faces
J1_SLOT_X = (-30.0, -15.5)
USB_WINDOW = (14.0, 9.0)
USB_PLUG = (13.6, 8.6)  # plug overmold probe, X x Z
USB_PLUG_Y = (-15.0, -2.7)  # probe from outside the flat through the tunnel into the end wall
MODULE_LOW_Z = -21.93  # measured, SimpleFOC C3 (the WeAct reaches -17.47)

# --- board features, measured 2026-11-09 on hdd-driver/build/test-model/test-assembly.step
# (export-test-model of hdd-driver.kicad_pcb as of e944f72), posed by reference.load_board().
# Labels from reference.named_bboxes(); re-measure when the board layout changes.
# WeAct push-buttons SW1, SW2, SW3: bbox centres (= centres of their actuator faces).
WEACT_BUTTONS = ((7.84, 4.69), (3.21, 34.46), (-11.94, 4.67))
# MT3608 trimmer (label Potentiometer_Bourns_3296W_Vertical): axis of its adjusting
# screw (r 1.1 circle on the free face). The bbox centre, (-22.51, 36.11), is 3.7 mm
# off the screw, so a poke hole there would miss it.
MT3608_TRIMMER = (-23.64, 39.61)
# J1 (label TerminalBlock_Phoenix_MKDS-1,5-2-5_08_1x02_P5_08mm_Horizontal): centre of
# the wire-clamp openings, Z -6.80…-3.95. Its bbox centre is -6.75 (bbox includes the
# leads through the board). In the model the openings face +Y, into the board; on the
# real board they face -Y, out through the end wall (user, 2026-11-09).
J1_WIRE_Z = -5.4
# J3 (label TerminalBlock_Phoenix_MPT-0,5-2-2_54_1x02_P2_54mm_Horizontal): centre of the
# wire openings on its +Y face (they face +Y on the real board too), Z -6.15…-1.75 at the
# face, -5.25…-2.45 0.7 mm in, from an is_inside scan at the pins X 24.71 and 27.25.
J3_WIRE_Z = -3.9
# WeAct USB-C receptacle (label USB_TYPEC16-7R35x8R94): centre of its mouth, shell
# X -6.52…2.42, Z -17.47…-14.27. Its bbox centre Z is -15.42 (bbox includes the pegs).
USB_CENTRE_XZ = (-2.05, -15.87)

# --- drum ---
DRUM_R_IN = 113.0
DRUM_WALL = 4.0
DRUM_R_MID = DRUM_R_IN + DRUM_WALL / 2  # 115: base's inner half inside, cover's lip outside
FLAT_Y_IN = -10.0
SEAT_Z = 0.0
LIP_BOTTOM_Z = -5.0
BASE_OUTER_TOP_Z = -5.5

# --- joint ---
TAB_ANGLES = (0, 50, 130, 180, 230, 310)
TAB_WIDTH = 16.0
TAB_BOTTOM_Z = -12.0
TAB_R_OUT = 119.0
TAB_THICK_TOP_Z = -1.0  # top of the tab's outward thickening, before its 45° chamfer
RECESS_BOTTOM_Z = -12.5
SCREW_Z = -7.0
KEY_ANGLE = 270
KEY_WIDTH = 8.0
KEY_DEPTH = 3.0
JOINT_SIDE_CLEAR = 0.2  # each side of the cover's tabs and key in the base's recesses and notch
JOINT_END_CLEAR = 0.5  # under the cover's key, and beyond the tab's thickening in its recess
INSERT_BOSS_R_IN = 105.0
INSERT_BOSS_W = 12.0
INSERT_BOSS_Z = (-12.2, -1.8)

# --- openings ---
USB_FLARE = (20.0, 14.0)
USB_TUNNEL_WALL = 2.0
J1_SLOT_BOTTOM_Z = J1_WIRE_Z - 4.0
PSU_SLOT_X = -23.0
PSU_SLOT_W = 6.0
PSU_SLOT_BOTTOM_Z = J1_WIRE_Z - 3.5
# B's cable enters the tray through the right side wall (+X) and reaches J3's +Y-facing
# entries from behind, below the carrier's SMD parts (their lowest point near the path:
# -2.8). Checked by tests/test_base.py::test_j3_cable_path_is_clear.
CABLE_SLOT_W = 6.0
J3_CABLE_SLOT_Y = 15.0
J3_SLOT_BOTTOM_Z = J3_WIRE_Z - 4.5
POKE_D = 5.0
FLOOR_SLOT_W = 4.0
FLOOR_SLOT_LEN = 20.0  # along Y
FLOOR_SLOT_PITCH = 6.0  # three slots side by side, centre to centre in X
# Group centres: the SimpleFOC Mini (U2, at (8.15, 49.49)) and the MT3608 (U3, at
# (-25.8, 34.45)); U3's group sits towards -Y to stay >= 3 mm off the trimmer poke hole.
FLOOR_SLOT_GROUPS = ((8.15, 50.0), (-25.8, 24.0))
# Two hooks on the outside of the right tray wall hold B's cable on its way to the slot.
CABLE_HOOK_Y = (25.0, 35.0)
CABLE_HOOK_W = 6.0  # along Y
CABLE_HOOK_GAP = 6.0  # cable channel between the wall and the post
CABLE_HOOK_T = 2.4  # post thickness, and the lip's thickness at its tip
CABLE_HOOK_LIP = 2.0  # the lip reaches back towards the wall, leaving a 4 mm entry
CABLE_HOOK_TOP_Z = -12.0

# --- feet ---
FEET_R = 104.0
FEET_ANGLES = (180, 252, 324, 36, 115)
FOOT_PAD_D = 10.0
FOOT_PAD_CAP = 2.0  # solid plastic above the insert hole

# --- inserts ---
M4_INSERT_HOLE_D = 5.6
M4_INSERT_LEN = 8.1
M4_INSERT_HOLE_DEPTH = M4_INSERT_LEN + 1.0
M4_INSERT_OD = 6.3
M4_CLEAR_D = 4.5
M3_INSERT_HOLE_D = 4.0
M3_INSERT_LEN = 5.7
M3_INSERT_HOLE_DEPTH = M3_INSERT_LEN + 0.8

# --- sensor B ---
B_PHI = 20.0
B_FACE_R = 79.5
B_WALL_T = 7.0
B_HALF_T = 26.0
B_HOLE_SPACING = 37.0
B_HOLE_BELOW_TOP = 5.0
B_BAR_TOP_NOM = 24.0
B_BAR_TOP_RANGE = (21.5, 24.5)
B_BODY = (23.0, 20.5, 19.4)  # depth from the wall, width, height
B_BAR = (46.0, 1.2, 12.0)  # steel bar: length along the face, thickness, height
B_HEAD_H = 23.4  # head bottom to bar top
B_LOWER_TOP_Z = -2.4
B_PULL_T = 8.0
B_PUSH_T = 16.0
B_DRIVE_CLEARANCE = 7.5

# --- sensor C ---
C_PHI = 180.0
C_BOSS_D = 30.0
C_BOSS_UNDER_Z = 37.4
C_GAP_RANGE = (1.0, 10.0)
C_WEB_W = 20.0
C_SENSOR_D = 15.85
C_SENSOR_LEN = 60.0
C_NUT_AF = 24.0
C_NUT_H = 13.0

# --- cover ---
PLATE_Z = (51.4, 54.4)
RIDGE_N = 8
RIDGE_T = 3.0
RIDGE_BOTTOM_Z = 40.0
RING_R = (30.0, 33.0)
STOP_R = 75.0
STOP_ANGLES = (0, 90, 180, 270)
STOP_GAP = 0.6
STOP_BOSS_D = 12.0
STOP_BOSS_BOTTOM_Z = 39.0

# --- vents ---
VENT_D = 4.0
INLET_PITCH = 7.0
INLET_R_MAX = 25.0
OUTLET_R = (105.0, 108.5)
OUTLET_STEP_DEG = 15.0
OUTLET_START_DEG = 7.5
VENT_MIN_SPACING = 7.0
VENT_EDGE_CLEAR = 3.0
VENT_CIRCLE_MAX = 0.25

# --- threads ---
THREAD_CLEARANCE = 0.3
COUPON_THREAD_LEN = 10.0

# --- bed ---
BED = 256.0
BED_MARGIN = 2.0


def pol(r: float, phi_deg: float, t: float = 0.0) -> tuple[float, float]:
    """Drive-frame (x, y) at radius r and tangential offset t about SPINDLE.

    Radial unit is (cos phi, -sin phi); tangent unit is (sin phi, cos phi).
    """
    p = math.radians(phi_deg)
    c, s = math.cos(p), math.sin(p)
    return (SPINDLE[0] + r * c + t * s, SPINDLE[1] - r * s + t * c)


def drum_outline(r: float, flat_y: float) -> Face:
    """Circle of radius r about SPINDLE, cut by Y = flat_y, keeping Y >= flat_y."""
    disc = Pos(SPINDLE[0], SPINDLE[1]) * Circle(r)
    keep = Pos(SPINDLE[0], (flat_y + SPINDLE[1] + r + 1.0) / 2) * Rectangle(
        2 * r + 2.0, SPINDLE[1] + r + 1.0 - flat_y
    )
    return (disc & keep).face()
