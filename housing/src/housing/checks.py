"""Fit-check helpers: overlap, clearance and vent coverage."""
import math

from build123d import Shape

from housing.params import SPINDLE


def overlap_volume(a: Shape, b: Shape) -> float:
    """Volume common to a and b; 0 when they don't meet."""
    return (a & b).volume


def min_clearance(a: Shape, b: Shape) -> float:
    """Smallest distance between a and b; 0 when they touch or overlap."""
    return a.distance_to(b)


def circle_fraction(centres: list[tuple[float, float]], d: float, r: float) -> float:
    """Fraction of the circle of radius r about SPINDLE that lies inside holes of diameter d.

    Each hole the circle crosses covers the arc between the two points where
    the circle meets the hole's edge; the fractions of all holes are summed.
    """
    h = d / 2
    total = 0.0
    for x, y in centres:
        rho = math.hypot(x - SPINDLE[0], y - SPINDLE[1])
        if rho + r <= h:                       # the hole swallows the whole circle
            total += 1.0
            continue
        if abs(rho - r) >= h:                  # the circle misses the hole
            continue
        cos_a = (r * r + rho * rho - h * h) / (2 * r * rho)
        total += 2 * math.acos(max(-1.0, min(1.0, cos_a))) / (2 * math.pi)
    return total
