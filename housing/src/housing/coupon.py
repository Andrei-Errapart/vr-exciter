"""Thread test coupon: a plate with an M16x1.5 and a 5/8-18 UNF through hole."""
from build123d import Align, Box, Part, Pos, Text, extrude

from housing.params import COUPON_THREAD_LEN
from housing.threads import M16X1_5, UNF_5_8_18, thread_negative

COUPON_SIZE = (60.0, 30.0)
HOLE_X = 14.0
LABEL_DEPTH = 0.6
LABEL_SIZE = 4.0
LABEL_Y = -11.0


def build_thread_coupon() -> Part:
    """Plate z 0..COUPON_THREAD_LEN; labels engraved into the top face.

    Each thread negative is placed by pure translation with its start at z = 0,
    so it matches the same hole built elsewhere at the same height above the start.
    """
    result = Box(*COUPON_SIZE, COUPON_THREAD_LEN,
                 align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x, spec, label in ((-HOLE_X, M16X1_5, "M16"), (HOLE_X, UNF_5_8_18, "5/8")):
        result = result - Pos(x, 0, 0) * thread_negative(spec, COUPON_THREAD_LEN)
        text = Text(label, LABEL_SIZE, align=(Align.CENTER, Align.CENTER))
        engrave = extrude(Pos(x, LABEL_Y, COUPON_THREAD_LEN - LABEL_DEPTH) * text,
                          amount=LABEL_DEPTH)
        result = result - engrave
    return Part(result)
