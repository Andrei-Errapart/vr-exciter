import re
import zipfile

import pytest

from housing.bambu3mf import Mesh, is_watertight
from housing.build import main


def read_mesh(path) -> Mesh:
    xml = zipfile.ZipFile(path).read("3D/3dmodel.model").decode()
    verts = [tuple(float(g) for g in m) for m in re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', xml)]
    tris = [tuple(int(g) for g in m) for m in re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', xml)]
    return Mesh(verts, tris)


def test_build_writes_everything(tmp_path):
    main(tmp_path)
    for f in ["step/base.step", "step/cover.step", "step/b_head.step", "step/thread_coupon.step",
              "housing_base_P1S.3mf", "housing_cover_P1S.3mf", "housing_b_head_P1S.3mf",
              "thread_coupon_P1S.3mf", "build/assembly.step"]:
        assert (tmp_path / f).stat().st_size > 0
    files = list(tmp_path.glob("*.3mf"))
    assert len(files) == 4
    for f in files:
        mesh = read_mesh(f)
        assert is_watertight(mesh), f.name
        zs = [v[2] for v in mesh.vertices]
        assert min(zs) == pytest.approx(0.0, abs=1e-6)
        xs = [v[0] for v in mesh.vertices]
        ys = [v[1] for v in mesh.vertices]
        assert max(xs) - min(xs) <= 252 and max(ys) - min(ys) <= 252
