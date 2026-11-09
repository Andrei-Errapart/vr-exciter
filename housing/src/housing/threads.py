"""Printed-thread helper: a solid "bolt" to subtract from a part."""
from dataclasses import dataclass

from build123d import Cylinder, Align, Part
from bd_warehouse.thread import IsoThread

from housing.params import THREAD_CLEARANCE

ISO_MINOR_FACTOR = 1.0825  # D1 = D - 1.0825 * pitch (ISO internal thread)


@dataclass(frozen=True)
class ThreadSpec:
    name: str
    major_d: float
    pitch: float


M16X1_5 = ThreadSpec("M16x1.5", 16.0, 1.5)
UNF_5_8_18 = ThreadSpec("5/8-18 UNF", 15.875, 25.4 / 18)


def thread_negative(spec: ThreadSpec, length: float,
                    clearance: float = THREAD_CLEARANCE) -> Part:
    """Solid to subtract: axis +Z, z = 0..length, helix unrotated (deterministic)."""
    minor_d = spec.major_d - ISO_MINOR_FACTOR * spec.pitch + clearance
    core = Cylinder(minor_d / 2, length, align=(Align.CENTER, Align.CENTER, Align.MIN))
    thread = IsoThread(
        major_diameter=spec.major_d + clearance,
        pitch=spec.pitch,
        length=length,
        external=True,
        end_finishes=("square", "square"),
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    return Part(core + thread)
