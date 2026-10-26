"""Remove named top-level components from a STEP assembly and write the rest.

Used to drop the pins-up 2x12 headers (components P1, P2) from WeAct's
STM32G474 Core Board model, so make-module-models can put pins-down headers
under the board instead.

Needs OpenCASCADE Python bindings (pip install cadquery-ocp).

    python strip_step_components.py IN.step OUT.step P1 P2
"""
import sys

from OCP.collections import Sequence_TDF_Label
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Reader, STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool


def label_name(label):
    attr = TDataStd_Name()
    if label.FindAttribute(TDataStd_Name.GetID_s(), attr):
        return attr.Get().ToExtString()
    return ""


def main():
    src, dst, *drop = sys.argv[1:]
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(True)
    if reader.ReadFile(src) != IFSelect_RetDone:
        sys.exit(f"cannot read {src}")
    reader.Transfer(doc)

    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    roots = Sequence_TDF_Label()
    tool.GetFreeShapes(roots)
    removed = []
    for i in range(1, roots.Length() + 1):
        comps = Sequence_TDF_Label()
        tool.GetComponents_s(roots.Value(i), comps)
        for j in range(1, comps.Length() + 1):
            comp = comps.Value(j)
            ref = TDF_Label()
            tool.GetReferredShape_s(comp, ref)
            if label_name(ref) in drop or label_name(comp) in drop:
                removed.append(label_name(ref) if label_name(ref) in drop else label_name(comp))
                tool.RemoveComponent(comp)
        tool.UpdateAssemblies()

    # The definitions of removed components (here sub-assemblies holding a
    # shared header part) would otherwise stay in the file as free top-level
    # shapes, and KiCad loads every free shape. Delete free shapes other than
    # the original roots until none are left.
    keep = {roots.Value(i).Tag() for i in range(1, roots.Length() + 1)}
    for _ in range(10):
        free = Sequence_TDF_Label()
        tool.GetFreeShapes(free)
        extra = [free.Value(i) for i in range(1, free.Length() + 1) if free.Value(i).Tag() not in keep]
        if not extra:
            break
        for label in extra:
            comps = Sequence_TDF_Label()
            tool.GetComponents_s(label, comps)
            for j in range(1, comps.Length() + 1):
                tool.RemoveComponent(comps.Value(j))
            tool.RemoveShape(label, True)
    free = Sequence_TDF_Label()
    tool.GetFreeShapes(free)
    if free.Length() != len(keep):
        sys.exit(f"stray free shapes left: {free.Length() - len(keep)}")

    missing = set(drop) - set(removed)
    if missing:
        sys.exit(f"components not found: {sorted(missing)}")

    writer = STEPCAFControl_Writer()
    writer.SetNameMode(True)
    writer.SetColorMode(True)
    writer.Transfer(doc, STEPControl_AsIs)
    if writer.Write(dst) != IFSelect_RetDone:
        sys.exit(f"cannot write {dst}")
    print(f"removed {removed}, wrote {dst}")


if __name__ == "__main__":
    main()
