import re
import zipfile

import pytest
from build123d import Box, Cylinder, Pos

from housing.bambu3mf import Mesh, is_watertight, mesh_from_part, write_bambu_3mf


def vertices_of(xml: bytes):
    pts = re.findall(rb'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', xml)
    xs, ys, zs = ([float(p[i]) for p in pts] for i in range(3))
    return xs, ys, zs


def test_mesh_is_watertight():
    assert is_watertight(mesh_from_part(Box(10, 10, 10) - Cylinder(2, 10)))


def test_winding_is_outward():
    m = mesh_from_part(Box(10, 20, 30) - Cylinder(2, 30))
    vol = 0.0
    for a, b, c in m.triangles:
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = m.vertices[a], m.vertices[b], m.vertices[c]
        vol += (x1 * (y2 * z3 - z2 * y3) - y1 * (x2 * z3 - z2 * x3) + z1 * (x2 * y3 - y2 * x3)) / 6
    assert vol == pytest.approx(6000 - 3.14159 * 4 * 30, rel=0.01)


def test_open_mesh_is_not_watertight():
    assert not is_watertight(Mesh([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 2)]))


def test_part_sits_on_plate(tmp_path):
    p = tmp_path / "t.3mf"
    write_bambu_3mf(p, mesh_from_part(Pos(50, 50, 7) * Box(10, 20, 4)), "01 test", {"wall_loops": "4"})
    z = zipfile.ZipFile(p)
    assert set(z.namelist()) >= {"3D/3dmodel.model", "Metadata/model_settings.config", "[Content_Types].xml", "_rels/.rels"}
    xs, ys, zs = vertices_of(z.read("3D/3dmodel.model"))
    assert min(zs) == pytest.approx(0.0, abs=1e-6)
    assert (min(xs) + max(xs)) / 2 == pytest.approx(0.0, abs=1e-6)
    assert (min(ys) + max(ys)) / 2 == pytest.approx(0.0, abs=1e-6)
    assert b'transform="1 0 0 0 1 0 0 0 1 128 128 0"' in z.read("3D/3dmodel.model")
    cfg = z.read("Metadata/model_settings.config").decode()
    assert 'value="01 test"' in cfg and 'key="wall_loops" value="4"' in cfg
