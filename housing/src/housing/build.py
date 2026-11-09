"""Build every printed part: STEP, Bambu Studio 3MF and the (git-ignored) assembly STEP."""
import sys
import time
from pathlib import Path

from build123d import Compound, Part, Rot, export_step

from . import params as P
from .b_head import build_b_head
from .bambu3mf import Mesh, is_watertight, mesh_from_part, write_bambu_3mf
from .base import build_base
from .coupon import build_thread_coupon
from .cover import build_cover
from .reference import coil_b, disc_envelope, drive_box, load_board, sensor_c

HOUSING_DIR = Path(__file__).resolve().parents[2]

_COMMON = {"layer_height": "0.2", "wall_loops": "4", "sparse_infill_density": "25%",
           "sparse_infill_pattern": "gyroid", "top_shell_layers": "5",
           "bottom_shell_layers": "4", "enable_support": "0"}
_COVER = {"layer_height": "0.2", "wall_loops": "4", "sparse_infill_density": "100%",
          "enable_support": "0"}
_B_HEAD = {**_COMMON, "sparse_infill_density": "40%"}


def _summary(name: str, mesh: Mesh) -> str:
    size = " x ".join(f"{max(c) - min(c):.1f}" for c in zip(*mesh.vertices))
    ok = "yes" if is_watertight(mesh) else "no"
    return f"{name}: {size} mm, {len(mesh.triangles)} triangles, watertight {ok}"


def main(out_dir: Path = HOUSING_DIR) -> None:
    out_dir = Path(out_dir)
    (out_dir / "step").mkdir(parents=True, exist_ok=True)
    (out_dir / "build").mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    base, cover = build_base(), build_cover()
    head, coupon = build_b_head(P.B_BAR_TOP_NOM), build_thread_coupon()
    parts = [
        ("base", "housing_base_P1S.3mf", "01 base (PETG)", base, base, _COMMON),
        ("cover", "housing_cover_P1S.3mf", "02 cover (transparent PETG)", cover,
         Part(Rot(180, 0, 0) * cover), _COVER),
        ("b_head", "housing_b_head_P1S.3mf", "03 B head (PETG)", head, head, _B_HEAD),
        ("thread_coupon", "thread_coupon_P1S.3mf", "04 thread coupon (PETG)", coupon, coupon, _B_HEAD),
    ]
    for stem, f3mf, label, part, posed, settings in parts:
        export_step(part, str(out_dir / "step" / f"{stem}.step"))
        mesh = mesh_from_part(posed)
        write_bambu_3mf(out_dir / f3mf, mesh, label, settings)
        print(_summary(stem, mesh))

    assembly = Compound(children=[
        base, cover, head, drive_box(), disc_envelope(),
        coil_b(P.B_BAR_TOP_NOM), sensor_c(1.0), load_board(),
    ])
    export_step(assembly, str(out_dir / "build" / "assembly.step"))
    print(f"assembly.step written; total {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HOUSING_DIR)
