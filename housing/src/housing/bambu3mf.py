"""Write a part as a Bambu Studio 3MF (same layout as disk/magnet_disc_60_P1S.3mf)."""
import zipfile
from collections import Counter
from pathlib import Path
from typing import Mapping, NamedTuple
from xml.sax.saxutils import escape, quoteattr

from build123d import Part


class Mesh(NamedTuple):
    vertices: list[tuple[float, float, float]]
    triangles: list[tuple[int, int, int]]


def mesh_from_part(part: Part, tolerance: float = 0.02, angular_tolerance: float = 0.1) -> Mesh:
    """Tessellate and weld coincident vertices (rounded to 1e-5 mm)."""
    verts, tris = part.tessellate(tolerance, angular_tolerance)
    index: dict[tuple[int, int, int], int] = {}
    out_v: list[tuple[float, float, float]] = []
    remap: list[int] = []
    for v in verts:
        key = (round(v.X * 1e5), round(v.Y * 1e5), round(v.Z * 1e5))
        if key not in index:
            index[key] = len(out_v)
            out_v.append((key[0] / 1e5, key[1] / 1e5, key[2] / 1e5))
        remap.append(index[key])
    out_t = []
    for a, b, c in tris:
        t = (remap[a], remap[b], remap[c])
        if len(set(t)) == 3:  # welding can collapse sliver triangles
            out_t.append(t)
    return Mesh(out_v, out_t)


def is_watertight(mesh: Mesh) -> bool:
    """True when every undirected edge is used by exactly two triangles."""
    edges: Counter = Counter()
    for a, b, c in mesh.triangles:
        for u, v in ((a, b), (b, c), (c, a)):
            edges[(min(u, v), max(u, v))] += 1
    return bool(edges) and all(n == 2 for n in edges.values())


def _num(x: float) -> str:
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
 <Default Extension="png" ContentType="image/png"/>
 <Default Extension="gcode" ContentType="text/x.gcode"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>"""


def write_bambu_3mf(path: Path, mesh: Mesh, object_name: str, settings: Mapping[str, str]) -> None:
    """Write one object centred on the plate (XY) and sitting on it (z=0)."""
    xs = [v[0] for v in mesh.vertices]
    ys = [v[1] for v in mesh.vertices]
    zs = [v[2] for v in mesh.vertices]
    cx, cy, z0 = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)

    model = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">',
        ' <metadata name="Application">BambuStudio-01.10.00.89</metadata>',
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
        f' <metadata name="Title">{escape(object_name)}</metadata>',
        ' <resources>',
        '  <object id="1" type="model">',
        '   <mesh>',
        '    <vertices>',
    ]
    for x, y, z in mesh.vertices:
        model.append(f'     <vertex x="{_num(x - cx)}" y="{_num(y - cy)}" z="{_num(z - z0)}"/>')
    model += ['    </vertices>', '    <triangles>']
    for a, b, c in mesh.triangles:
        model.append(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>')
    model += [
        '    </triangles>', '   </mesh>', '  </object>', ' </resources>', ' <build>',
        '  <item objectid="1" transform="1 0 0 0 1 0 0 0 1 128 128 0" printable="1"/>',
        ' </build>', '</model>',
    ]

    cfg = [
        '<?xml version="1.0" encoding="UTF-8"?>', '<config>', '  <object id="1">',
        f'    <metadata key="name" value={quoteattr(object_name)}/>',
        '    <metadata key="extruder" value="1"/>',
    ]
    for k, v in settings.items():
        cfg.append(f'    <metadata key={quoteattr(k)} value={quoteattr(str(v))}/>')
    cfg += [
        '  </object>', '  <plate>',
        '    <metadata key="plater_id" value="1"/>',
        '    <metadata key="plater_name" value=""/>',
        '    <metadata key="locked" value="false"/>',
        '    <model_instance>',
        '      <metadata key="object_id" value="1"/>',
        '      <metadata key="instance_id" value="0"/>',
        '      <metadata key="identify_id" value="1000"/>',
        '    </model_instance>', '  </plate>', '</config>',
    ]

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("3D/3dmodel.model", "\n".join(model) + "\n")
        z.writestr("Metadata/model_settings.config", "\n".join(cfg) + "\n")
