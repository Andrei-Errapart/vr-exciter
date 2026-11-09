"""Hand calculations behind the spec, as checked code: the loose disc's envelope and the
cover ridge's fault load path. Pure math; every number comes from params."""
import math

from . import params as P


def loose_disc_envelope(
    stops: list[tuple[float, float, float]],
    ring: tuple[float, float] | None = None,
    n: int = 101,
) -> dict[str, float]:
    """Worst-case poses of a rigid disc lifted off the platter.

    Surface displacement z = z0 + tx*x + ty*y about the spindle. Constraints: tilt limited by
    the bore (BORE_CLEARANCE over HUB_ENGAGEMENT); the hub foot stays on the flange
    (z0 >= HUB_FOOT_R*|t|); z0 <= HUB_ENGAGEMENT; each stop (r, phi, clearance) caps z at its
    point; a ring (outer radius, clearance) caps z everywhere inside it. Brute force over a
    n x n grid of (tx, ty), both z0 extremes. Returns rim_rise, hub_lift, z_at_c and
    drop_at_b (how far the disc can drop at B's pole), in mm.
    """
    tmax = P.BORE_CLEARANCE / P.HUB_ENGAGEMENT
    pts = [(r * math.cos(math.radians(p)), r * math.sin(math.radians(p)), c) for r, p, c in stops]
    c_xy = (P.MAGNET_R * math.cos(math.radians(P.C_PHI)), P.MAGNET_R * math.sin(math.radians(P.C_PHI)))
    b_xy = (P.MAGNET_R * math.cos(math.radians(P.B_PHI)), P.MAGNET_R * math.sin(math.radians(P.B_PHI)))
    out = {"rim_rise": -math.inf, "hub_lift": -math.inf, "z_at_c": -math.inf, "drop_at_b": -math.inf}
    for i in range(n):
        tx = -tmax + 2 * tmax * i / (n - 1)
        for j in range(n):
            ty = -tmax + 2 * tmax * j / (n - 1)
            t = math.hypot(tx, ty)
            if t > tmax:
                continue
            lo = P.HUB_FOOT_R * t
            hi = P.HUB_ENGAGEMENT
            for x, y, c in pts:
                hi = min(hi, c - (tx * x + ty * y))
            if ring is not None:
                hi = min(hi, ring[1] - t * ring[0])
            if lo > hi:
                continue
            for z0 in (lo, hi):
                out["rim_rise"] = max(out["rim_rise"], z0 + t * P.DISC_R)
                out["hub_lift"] = max(out["hub_lift"], z0)
                out["z_at_c"] = max(out["z_at_c"], z0 + tx * c_xy[0] + ty * c_xy[1])
                out["drop_at_b"] = max(out["drop_at_b"], -(z0 + tx * b_xy[0] + ty * b_xy[1]))
    return out


def ridge_cantilever(force_n: float, arm_mm: float) -> tuple[float, float]:
    """(deflection mm, peak stress MPa) of a cover ridge as a cantilever under an end load.

    T-section: the web is RIDGE_T wide and as deep as the ridge (plate underside to
    RIDGE_BOTTOM_Z); the flange is the plate, RIDGE_FLANGE_W wide.
    """
    web_h = P.PLATE_Z[0] - P.RIDGE_BOTTOM_Z
    fl_t = P.PLATE_Z[1] - P.PLATE_Z[0]
    a_web, a_fl = P.RIDGE_T * web_h, P.RIDGE_FLANGE_W * fl_t
    y_web, y_fl = web_h / 2, web_h + fl_t / 2  # from the ridge's bottom edge
    y_na = (a_web * y_web + a_fl * y_fl) / (a_web + a_fl)
    inertia = (
        P.RIDGE_T * web_h**3 / 12 + a_web * (y_web - y_na) ** 2
        + P.RIDGE_FLANGE_W * fl_t**3 / 12 + a_fl * (y_fl - y_na) ** 2
    )
    c = max(y_na, web_h + fl_t - y_na)
    return (
        force_n * arm_mm**3 / (3 * P.PETG_E_MPA * inertia),
        force_n * arm_mm * c / inertia,
    )


def screw_shear_n(force_n: float) -> float:
    """Shear per joint screw, the load shared equally by all of them."""
    return force_n / len(P.TAB_ANGLES)
