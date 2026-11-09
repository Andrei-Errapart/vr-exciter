# HDD Housing (Closed Drum) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate the printable closed-drum housing as parametric build123d models: base, transparent cover, sensor-B head and thread coupon. Deliver STEP files, Bambu Studio 3MFs and a `housing/` README.

**Architecture:**
- **Layout:** a Python package `housing/src/housing/`. One module per printed part, plus modules for shared geometry (frame and parameters, joint, threads), checks against reference solids (drive, disc, sensors, board), an analysis module for the hand calculations, and a hand-written Bambu 3MF writer modelled on `disk/magnet_disc_60_P1S.3mf`.
- **Single source of numbers:** every number from the spec lives in `params.py`.
- **Tests:** pytest checks geometry, clearances and exported files against the spec's values.

**Tech Stack:** Python 3.12 in a uv venv at `housing/.venv`, build123d, bd_warehouse (threads), pytest. KiCad 10 `kicad-cli` is used only through `hdd-driver/scripts/export-test-model`.

**Spec:** `docs/superpowers/specs/2026-11-09-hdd-housing-extension-design.md` (approved). Read it in full before starting. Section names below refer to it.

## Global Constraints

- **Frame:** drive frame X, Y in mm (bottom view, connector end at Y 0). Z is the height above the drive underside, positive towards the disc. Polar coordinates are about the spindle (0.2, 95.9), with φ measured from +X, positive towards −Y.
- **Model pose:** model every part in the frame above, in its position of use. Export poses are applied only in `build.py`.
- **Numbers:** every dimension comes from `housing.params`. No literal spec numbers in part modules.
- **Inserts and screws:**
  - Heat-set inserts are Ruthex M4 × 8.1 (OD 6.3, hole Ø5.6 × ≥ 9 deep) and M3 × 5.7 (hole Ø4.0 × ≥ 6.5 deep). Check the hole sizes against the Ruthex table during Task 1 and change the two params if they differ.
  - M4 clearance hole Ø4.5.
- **Printed threads:** +0.3 mm on the diameters (`THREAD_CLEARANCE`).
- **Printer:** Bambu P1S with a 256 × 256 bed. Every exported part must fit within 252 × 252, which leaves 2 mm all round.
- **Vents:** every vent hole is Ø4 at most, and none goes in the drum wall.
- **Disc clearance:** nothing of the cover may be lower than Z 37.4 inside r 104. Stop screws are not modelled.
- **Joint:** the cover touches the base only at the seat (Z 0, r 113–115). The lip bottom has 0.5 mm clearance and the tab bottoms have 0.5 mm.
- **Python:** the venv must be Python 3.12, because build123d's OCP wheels do not support the system Python 3.15. Create it with `uv venv --python 3.12 housing/.venv`.
- **Don't modify** `hdd-driver/` sources. The only change in `disk/` is one line in its README (Task 11).

## Review Focus

1. **Stale or missing board export:** the fit check must fail with a message naming `hdd-driver/scripts/export-test-model`, never pass silently. Test: Task 4, `test_stale_board_export_is_rejected`.
2. **Exported meshes:** they must be watertight and lie on the plate (min z = 0, inside the bed). If not, Bambu shows repair warnings or floats parts. Tests: Task 3, `test_mesh_is_watertight` and `test_part_sits_on_plate`.
3. **Thread clearance drift:** the cover's M16 hole and the coupon's M16 hole must come from the same function and clearance. Test: Task 7, `test_cover_thread_matches_coupon`.
4. **Parameter edits that break the loose-disc margins** (stop radius, count, gap, sensor gaps). Test: Task 9 reads `params` live.
5. **The cover must fit only one way.** Test: Task 7, `test_cover_fits_only_one_way`. Rotated by any tab spacing, it collides with the base.

---

## File Structure

```
.gitignore                         + .superpowers/, housing/.venv/, housing/build/, __pycache__/, .pytest_cache/
housing/
  README.md                        parts, BOM, print, assembly, adjustment, checks
  CLAUDE.md                        folder notes (source vs generated, tools)
  requirements.txt                 pinned build123d, bd_warehouse, pytest
  pytest.ini                       pythonpath = src, testpaths = tests
  make-housing                     bash: ensure venv, run tests or build
  src/housing/
    __init__.py
    params.py                      all spec numbers + pol(), drum outline helper
    threads.py                     ThreadSpec, M16X1_5, UNF_5_8_18, thread_negative()
    joint.py                       seat/lip/tab/recess/key solids shared by base and cover
    base.py                        build_base(): tray, floor, wall, bosses, feet, openings, B lower tower
    b_head.py                      build_b_head(bar_top_z): separate B tower head
    cover.py                       build_cover(), vent_hole_centres()
    coupon.py                      build_thread_coupon()
    reference.py                   drive/disc/coil/sensor envelopes, board import, board features
    checks.py                      overlap_volume(), min_clearance(), circle_fraction()
    analysis.py                    loose-disc envelope, ridge/joint load checks
    bambu3mf.py                    Mesh, mesh_from_part(), is_watertight(), write_bambu_3mf()
    build.py                       main(): STEP, 3MF, assembly STEP
  tests/
    conftest.py                    session fixtures: base, cover, b_head, board
    test_params.py  test_threads.py  test_coupon.py  test_bambu3mf.py
    test_reference.py  test_base.py  test_b_mount.py  test_cover.py
    test_analysis.py  test_build.py
  step/                            committed: base, cover, b_head, thread_coupon .step
  *_P1S.3mf                        committed: one 3MF per printed part
  build/                           git-ignored: assembly.step
disk/README.md                     one line: threadlocker on the clamp-ring screws
```

---

### Task 1: Scaffolding, parameters, frame helpers

**Files:**
- Create: `housing/requirements.txt`, `housing/pytest.ini`, `housing/make-housing`, `housing/src/housing/__init__.py`, `housing/src/housing/params.py`, `housing/tests/test_params.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces:
  - `params.pol(r: float, phi_deg: float, t: float = 0.0) -> tuple[float, float]`: radial unit (cos φ, −sin φ), tangent unit (sin φ, cos φ).
  - `params.drum_outline(r: float, flat_y: float) -> build123d.Face`: a circle about `SPINDLE` cut by the line Y = `flat_y`, keeping the part with Y ≥ flat_y.
  - The constants below, all floats in mm unless noted.

- [ ] **Step 1: Set up the venv and pins.** Run `uv venv --python 3.12 housing/.venv && uv pip install --python housing/.venv build123d bd_warehouse pytest`. Write the resolved versions as `==` pins in `requirements.txt`.
- [ ] **Step 2: Write `make-housing` and the ignore entries.** `make-housing` (bash, `set -euo pipefail`) creates the venv if it is missing, installs `requirements.txt`, then runs `pytest` for `make-housing test` and `python -m housing.build` for `make-housing build`. Add the `.gitignore` entries from the File Structure.
- [ ] **Step 3: Write the failing test** `tests/test_params.py`:

```python
from housing import params as P

def test_pol_matches_spec_positions():
    assert P.pol(95.5, 180) == pytest.approx((-95.3, 95.9), abs=0.05)   # C axis
    assert P.pol(95.5, 20) == pytest.approx((89.94, 63.24), abs=0.05)   # B pole

def test_drum_outline_flat_and_radius():
    f = P.drum_outline(P.DRUM_R_IN, P.FLAT_Y_IN)
    bb = f.bounding_box()
    assert bb.min.Y == pytest.approx(-10.0, abs=1e-3)
    assert bb.max.Y == pytest.approx(95.9 + 113.0, abs=1e-3)
    assert bb.max.X == pytest.approx(0.2 + 113.0, abs=1e-3)

def test_feet_inside_drum():
    for phi in P.FEET_ANGLES:
        x, y = P.pol(P.FEET_R, phi)
        assert ((x - 0.2) ** 2 + (y - 95.9) ** 2) ** 0.5 < P.DRUM_R_IN
```

- [ ] **Step 4: Run it and see it fail.** Run `housing/make-housing test`. Expected: FAIL with an ImportError.
- [ ] **Step 5: Write `params.py`** with these constants. Group them under comments that name the spec section.

| Group | Constants |
|---|---|
| frame | `SPINDLE=(0.2,95.9)`, `DRIVE_X_HALF=50.8`, `DRIVE_LEN=147.0`, `DRIVE_TOP_Z=22.66`, `HOLES=((-47.625,41.28),(47.625,41.28),(-47.625,85.73),(47.625,85.73))` |
| disc | `DISC_R=101.0`, `DISC_UNDER_Z=(25.0,25.4)`, `DISC_TOP_Z=(33.0,33.4)`, `MAGNET_R=95.5`, `HUB_ENGAGEMENT=8.5`, `BORE_CLEARANCE=0.19` |
| tray | `TRAY_GAP=0.3`, `TRAY_WALL=2.4`, `TRAY_WALL_TOP_Z=-0.5`, `FLOOR_TOP_Z=-21.0`, `FLOOR_UNDER_Z=-24.0`, `BOSS_LEDGE=3.0`, `BOSS_CLEAR_D=3.8`, `BOSS_BORE_D=8.0`, `J1_SLOT_X=(-30.0,-15.5)`, `J3_SLOT_X=(21.0,31.0)`, `USB_WINDOW=(14.0,9.0)`, `USB_CENTRE_XZ=(-2.4,-15.8)`, `MODULE_LOW_Z=-17.6` |
| drum | `DRUM_R_IN=113.0`, `DRUM_WALL=4.0`, `FLAT_Y_IN=-10.0`, `SEAT_Z=0.0`, `LIP_BOTTOM_Z=-5.0`, `BASE_OUTER_TOP_Z=-5.5` |
| joint | `TAB_ANGLES=(0,50,130,180,230,310)`, `TAB_WIDTH=16.0`, `TAB_BOTTOM_Z=-12.0`, `TAB_R_OUT=119.0`, `RECESS_BOTTOM_Z=-12.5`, `SCREW_Z=-7.0`, `KEY_ANGLE=270`, `KEY_WIDTH=8.0`, `KEY_DEPTH=3.0` |
| openings | `USB_FLARE=(20.0,14.0)`, `PSU_SLOT_X=-23.0`, `PSU_SLOT_W=6.0`, `POKE_D=5.0`, `FLOOR_SLOT_W=4.0` |
| feet | `FEET_R=104.0`, `FEET_ANGLES=(180,252,324,36,115)` |
| inserts | `M4_INSERT_HOLE_D=5.6`, `M4_INSERT_LEN=8.1`, `M4_INSERT_OD=6.3`, `M4_CLEAR_D=4.5`, `M3_INSERT_HOLE_D=4.0`, `M3_INSERT_LEN=5.7` |
| sensor B | `B_PHI=20.0`, `B_FACE_R=79.5`, `B_WALL_T=7.0`, `B_HALF_T=26.0`, `B_HOLE_SPACING=37.0`, `B_HOLE_BELOW_TOP=5.0`, `B_BAR_TOP_NOM=24.0`, `B_BAR_TOP_RANGE=(21.5,24.5)`, `B_BODY=(23.0,20.5,19.4)` (depth from the wall, width, height), `B_HEAD_H=23.4` (head bottom to bar top), `B_LOWER_TOP_Z=-2.4`, `B_PULL_T=8.0`, `B_PUSH_T=16.0`, `B_DRIVE_CLEARANCE=7.5` |
| sensor C | `C_PHI=180.0`, `C_BOSS_D=30.0`, `C_BOSS_UNDER_Z=37.4`, `C_GAP_RANGE=(1.0,10.0)`, `C_WEB_W=20.0` |
| cover | `PLATE_Z=(51.4,54.4)`, `RIDGE_N=8`, `RIDGE_T=3.0`, `RIDGE_BOTTOM_Z=40.0`, `RING_R=(30.0,33.0)`, `STOP_R=75.0`, `STOP_ANGLES=(0,90,180,270)`, `STOP_GAP=0.6`, `STOP_BOSS_D=12.0`, `STOP_BOSS_BOTTOM_Z=39.0` |
| vents | `VENT_D=4.0`, `INLET_PITCH=7.0`, `INLET_R_MAX=25.0`, `OUTLET_R=(105.0,108.5)`, `OUTLET_STEP_DEG=15.0`, `OUTLET_START_DEG=7.5`, `VENT_MIN_SPACING=7.0`, `VENT_EDGE_CLEAR=3.0`, `VENT_CIRCLE_MAX=0.25` |
| threads | `THREAD_CLEARANCE=0.3`, `COUPON_THREAD_LEN=10.0` |
| bed | `BED=256.0`, `BED_MARGIN=2.0` |

- [ ] **Step 6: Run the tests and see them pass.** Run `housing/make-housing test`. Expected: 3 passed.
- [ ] **Step 7: Commit.** Run `git add .gitignore housing && git commit -m "housing: scaffold package, parameters and frame helpers"`.

---

### Task 2: Threads and the thread test coupon

**Files:**
- Create: `housing/src/housing/threads.py`, `housing/src/housing/coupon.py`, `housing/tests/test_threads.py`, `housing/tests/test_coupon.py`

**Interfaces:**
- Consumes: `params.THREAD_CLEARANCE`, `params.COUPON_THREAD_LEN`.
- Produces:
  - `ThreadSpec(name: str, major_d: float, pitch: float)` (frozen dataclass).
  - `M16X1_5 = ThreadSpec("M16x1.5", 16.0, 1.5)` and `UNF_5_8_18 = ThreadSpec("5/8-18 UNF", 15.875, 25.4/18)`.
  - `thread_negative(spec: ThreadSpec, length: float, clearance: float = THREAD_CLEARANCE) -> Part`: a solid "bolt" shape to subtract. Its axis is +Z from z = 0 to `length`. It is a core cylinder at the minor diameter plus clearance, fused with a `bd_warehouse.thread.IsoThread(external=True)` of `major_d + clearance` and `pitch`.
  - `build_thread_coupon() -> Part`: a plate 60 × 30 × `COUPON_THREAD_LEN`, with the M16 hole at x −14 and the UNF hole at x +14. Each hole has its label ("M16", "5/8") engraved 0.6 mm deep on the top face.

- [ ] **Step 1: Write the failing tests.**

```python
def test_negative_outer_diameter_includes_clearance():
    bb = thread_negative(M16X1_5, 17.0).bounding_box()
    assert bb.size.X == pytest.approx(16.3, abs=0.05)
    assert bb.size.Z == pytest.approx(17.0, abs=0.05)

def test_unf_pitch():
    assert UNF_5_8_18.pitch == pytest.approx(1.4111, abs=1e-4)

def test_coupon_has_two_through_threads():
    c = build_thread_coupon()
    assert not c.is_inside(Vector(-14, 0, 5)) and not c.is_inside(Vector(14, 0, 5))
    assert c.is_inside(Vector(-14 + 8.6, 0, 5))           # material beyond the major radius
    assert c.bounding_box().size.Z == pytest.approx(10.0, abs=0.01)
```

- [ ] **Step 2: Run them and see them fail.** Run `housing/make-housing test`. Expected: FAIL with an ImportError.
- [ ] **Step 3: Implement `threads.py` and `coupon.py`** with the signatures above.
- [ ] **Step 4: Run the tests and see them pass.** Expected: PASS.
- [ ] **Step 5: Commit.** Use the message `housing: printed thread helper and thread test coupon`.

---

### Task 3: Bambu 3MF writer

**Files:**
- Create: `housing/src/housing/bambu3mf.py`, `housing/tests/test_bambu3mf.py`

**Interfaces:**
- Produces:
  - `Mesh(vertices: list[tuple[float,float,float]], triangles: list[tuple[int,int,int]])` (NamedTuple).
  - `mesh_from_part(part: Part, tolerance: float = 0.02, angular_tolerance: float = 0.1) -> Mesh`: tessellates with `part.tessellate()`, then welds coincident vertices (rounded to 1e-5 mm).
  - `is_watertight(mesh: Mesh) -> bool`: true when every undirected edge is used by exactly two triangles.
  - `write_bambu_3mf(path: Path, mesh: Mesh, object_name: str, settings: Mapping[str, str]) -> None`:
    - Translate the vertices so that the bbox centre XY is (0, 0) and min z = 0.
    - Write the same structure as `disk/magnet_disc_60_P1S.3mf`: `[Content_Types].xml`, `_rels/.rels`, `3D/3dmodel.model` (object id 1, `<build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 128 128 0" printable="1"/>`), and `Metadata/model_settings.config` (one `<object id="1">` with `name`, `extruder` = 1, every `settings` key as `<metadata key=… value=…/>`, and one `<plate>`).
    - Unpack the disc 3MF into the scratchpad and copy the XML headers, namespaces and content-types from it.

- [ ] **Step 1: Write the failing tests.**

```python
def test_mesh_is_watertight():
    assert is_watertight(mesh_from_part(Box(10, 10, 10) - Cylinder(2, 10)))

def test_part_sits_on_plate(tmp_path):
    p = tmp_path / "t.3mf"
    write_bambu_3mf(p, mesh_from_part(Pos(50, 50, 7) * Box(10, 20, 4)), "01 test", {"wall_loops": "4"})
    z = zipfile.ZipFile(p)
    assert set(z.namelist()) >= {"3D/3dmodel.model", "Metadata/model_settings.config", "[Content_Types].xml", "_rels/.rels"}
    xs, ys, zs = vertices_of(z.read("3D/3dmodel.model"))       # small helper in the test
    assert min(zs) == pytest.approx(0.0, abs=1e-6)
    assert (min(xs) + max(xs)) / 2 == pytest.approx(0.0, abs=1e-6)
    assert b'transform="1 0 0 0 1 0 0 0 1 128 128 0"' in z.read("3D/3dmodel.model")
    cfg = z.read("Metadata/model_settings.config").decode()
    assert 'value="01 test"' in cfg and 'key="wall_loops" value="4"' in cfg
```

- [ ] **Step 2: Run them and see them fail.** Expected: FAIL with an ImportError.
- [ ] **Step 3: Implement `bambu3mf.py`.**
- [ ] **Step 4: Run the tests and see them pass.** Expected: PASS.
- [ ] **Step 5: Commit.** Use the message `housing: Bambu 3MF writer with watertight check`.

---

### Task 4: Reference solids, board import, fit-check helpers

**Files:**
- Create: `housing/src/housing/reference.py`, `housing/src/housing/checks.py`, `housing/tests/conftest.py`, `housing/tests/test_reference.py`
- Modify: `housing/src/housing/params.py` (record the board features found in Step 5)

**Interfaces:**
- Consumes: `params.*`.
- Produces:
  - `checks.overlap_volume(a: Shape, b: Shape) -> float`
  - `checks.min_clearance(a: Shape, b: Shape) -> float`, using `a.distance_to(b)`
  - `checks.circle_fraction(centres: list[tuple[float,float]], d: float, r: float) -> float`: the fraction of the circle of radius `r` about `SPINDLE` that falls inside the holes, from the summed chord-angle of each hole the circle crosses.
  - `reference.drive_box() -> Part`: X ±50.8, Y 0…147, Z 0…22.66.
  - `reference.disc_envelope() -> Part`: cylinder r 101, Z 25.0…33.4.
  - `reference.coil_b(bar_top_z: float) -> Part`: bar 46 × 1.2 × 12 on the face at r 79.5, plus the body box: depth 23, width 20.5, height 19.4 down from `bar_top_z`.
  - `reference.sensor_c(gap: float) -> Part`: Ø15.85 cylinder from `DISC_TOP_Z[1] + gap` up 60 mm, plus a nut 24 AF × 13 on the plate top.
  - `reference.usb_plug_probe() -> Part`: a 13.6 × 8.6 box along Y from −15 to −2.7, centred on `USB_CENTRE_XZ`.
  - `reference.BOARD_STEP` and `reference.BOARD_TEST_PCB`: paths under `hdd-driver/build/test-model/`.
  - `reference.footprint_positions(pcb_text: str) -> dict[str, tuple[float,float,float]]`: ref → (X, Y, rot) in the drive frame, i.e. KiCad (x − 150, y − 40).
  - `reference.load_board() -> Compound`: imports `BOARD_STEP` and rotates it 180° about X, mapping (x, y, z) → (x, −y, −z).
    - Before importing, it raises `RuntimeError("board export is stale or missing; run hdd-driver/scripts/export-test-model")` if the file is missing, or if `footprint_positions` of `BOARD_TEST_PCB` and of `hdd-driver/hdd-driver.kicad_pcb` differ for J1, J3, U1, U2 or U3.
  - `reference.named_bboxes(step_path: Path) -> dict[str, BoundBox]`: walks the imported assembly's labels and transforms the boxes like `load_board`.
  - Session fixtures in `conftest.py`: `board` (from `load_board()`), `disc`, `drive`.

- [ ] **Step 1: Regenerate the board export.** Run `hdd-driver/scripts/export-test-model`. Expected: `written to …/build/test-model`.
- [ ] **Step 2: Write the failing tests.**

```python
def test_footprint_positions_parse_current_pcb():
    pos = footprint_positions((ROOT / "hdd-driver/hdd-driver.kicad_pcb").read_text())
    assert pos["J1"][:2] == pytest.approx((-25.35, 6.75), abs=0.01)
    assert pos["J3"][:2] == pytest.approx((24.71, 4.61), abs=0.01)

def test_board_orientation(board):
    bb = board.bounding_box()
    assert -18.1 <= bb.min.Z <= -15.5          # modules hang below the drive
    assert bb.max.Z <= 5.0                      # only the spring contacts rise above Z 0
    assert -37.0 <= bb.min.X and bb.max.X <= 39.0
    assert -1.5 <= bb.min.Y and bb.max.Y <= 75.0

def test_stale_board_export_is_rejected(tmp_path, monkeypatch):
    stale = tmp_path / "hdd-driver-test.kicad_pcb"
    stale.write_text(BOARD_TEST_PCB.read_text().replace("(at 124.65 46.75", "(at 120.1 100.0", 1))
    monkeypatch.setattr(reference, "BOARD_TEST_PCB", stale)
    with pytest.raises(RuntimeError, match="export-test-model"):
        reference.load_board()

def test_circle_fraction_single_hole():
    # one Ø4 hole centred on r 50: 4/(2π·50) of the circle
    assert circle_fraction([P.pol(50, 0)], 4.0, 50.0) == pytest.approx(4 / (2 * math.pi * 50), rel=0.02)
```

  In the stale test, use J1's actual `(at …)` string from the test PCB. The literal above is an example.
- [ ] **Step 3: Run them and see them fail.** Expected: FAIL with an ImportError.
- [ ] **Step 4: Implement `reference.py`, `checks.py` and `conftest.py`.**
- [ ] **Step 5: Record the board features in `params.py`.**
  - Run `named_bboxes(BOARD_STEP)` and record:
    - `WEACT_BUTTONS`: XY centres of SW1, SW2, SW3;
    - `MT3608_TRIMMER`: XY centre of RV1;
    - `J1_WIRE_Z`: J1's bbox centre Z;
    - `USB_CENTRE_XZ`: the USB-C receptacle's bbox centre X and Z.
  - If labels are missing from the assembly, take them from `hdd-driver/lib/3d/*.step`, transformed by the U1/U3 footprint placement (+11.04 mm socket offset, per `hdd-driver/CLAUDE.md`).
  - Add this test and run it:

```python
def test_board_features_inside_their_modules():
    for x, y in P.WEACT_BUTTONS:
        assert -16.7 <= x <= 12.6 and 1.0 <= y <= 38.4
    x, y = P.MT3608_TRIMMER
    assert -35.0 <= x <= -16.6 and 15.3 <= y <= 53.6
    assert -10.0 <= P.J1_WIRE_Z <= -2.0
    assert -18.0 <= P.USB_CENTRE_XZ[1] <= -13.0
```

- [ ] **Step 6: Run the tests and see them pass.** Expected: PASS.
- [ ] **Step 7: Commit.** Use the message `housing: reference solids, board import with freshness check`.

---

### Task 5: Base: tray, drum floor and wall, joint, feet, openings

**Files:**
- Create: `housing/src/housing/joint.py`, `housing/src/housing/base.py`, `housing/tests/test_base.py`

**Interfaces:**
- Consumes: `params.*`, `reference.*`, `checks.*`, `threads` (none).
- Produces:
  - `joint.tab_solid(phi: float) -> Part`: the cover's tab, as positive material:
    - lip continuation r 115–117 from Z `LIP_BOTTOM_Z` down to `TAB_BOTTOM_Z`;
    - outward thickening r 117–`TAB_R_OUT` from Z −1 down to `TAB_BOTTOM_Z`, with a 45° chamfer on its top edge;
    - `TAB_WIDTH` wide, and an `M4_CLEAR_D` radial hole on Z `SCREW_Z`.
  - `joint.recess_cut(phi: float) -> Part`: the base cut for a tab, `TAB_WIDTH` + 0.4 wide, r 115–`TAB_R_OUT` + 0.5, from Z `BASE_OUTER_TOP_Z` down to `RECESS_BOTTOM_Z`.
  - `joint.insert_boss(phi: float) -> Part`: r 105–115, 12 wide, Z −12.2…−1.8, with a radial `M4_INSERT_HOLE_D` hole from r 115 to r 115 − (`M4_INSERT_LEN` + 1) on Z `SCREW_Z`.
  - `joint.key_notch() -> Part` (base cut) and `joint.key_tab() -> Part` (cover material). Both sit at `KEY_ANGLE` in the inner half (r 113–115). The notch is `KEY_WIDTH` wide × `KEY_DEPTH` deep. The tab is 0.4 narrower and 0.5 shorter.
  - `base.build_base() -> Part`, made of:
    - the drum floor over `drum_outline(DRUM_R_IN + DRUM_WALL, FLAT_Y_IN − DRUM_WALL)` from `FLOOR_UNDER_Z` to `FLOOR_TOP_Z`;
    - the wall ring from the floor to `SEAT_Z`, with the outer half (r 115–117) only up to `BASE_OUTER_TOP_Z`;
    - the tray walls, and the hollow bosses at `HOLES`;
    - the five feet pads with `M3_INSERT_HOLE_D` × (`M3_INSERT_LEN` + 0.8) holes from below;
    - the six `joint.recess_cut` cuts and `joint.insert_boss` bosses, and `joint.key_notch`;
    - the end-wall slots: J1 and J3 open from the wall top down to `J1_WIRE_Z` − 4, and the USB window;
    - the USB tunnel: a 2 mm-walled tube from the flat to the end wall, flared to `USB_FLARE` at the outer face over the 4 mm wall thickness;
    - the 12 V slot in the flat: `PSU_SLOT_W` wide at `PSU_SLOT_X`, from Z 0 down to `J1_WIRE_Z` − 3.5;
    - Ø`POKE_D` poke holes under `WEACT_BUTTONS` and `MT3608_TRIMMER`;
    - three `FLOOR_SLOT_W` × 20 slots each under U2 and U3, clear of the poke holes and bosses by ≥ 3 mm;
    - two cable hooks on the outside of the right tray wall.
    - The B lower tower is added in Task 6.

- [ ] **Step 1: Write the failing tests** (`base` is a session fixture calling `build_base()`):

```python
def test_base_fits_bed(base):
    s = base.bounding_box().size
    assert s.X <= P.BED - 2 * P.BED_MARGIN and s.Y <= P.BED - 2 * P.BED_MARGIN
    assert base.bounding_box().min.Z == pytest.approx(-24.0, abs=1e-3)

def test_base_clears_drive_and_touches_only_at_bosses(base, drive):
    assert overlap_volume(base, drive) == pytest.approx(0, abs=1e-3)
    for x, y in P.HOLES:
        assert overlap_volume(base, Pos(x, y, -0.05) * Box(9, 9, 0.1)) > 0      # boss reaches Z 0
        assert not base.is_inside(Vector(x, y, -10))                              # bore open from below

def test_seat_is_top_of_wall(base):
    ring = Pos(*P.SPINDLE, 0.05) * (Cylinder(117.5, 0.1) - Cylinder(112.5, 0.1))
    assert overlap_volume(base, ring) == pytest.approx(0, abs=1e-3)
    seat = Pos(*P.pol(114, 200), -0.05) * Box(1, 1, 0.1)
    assert overlap_volume(base, seat) > 0

def test_feet_insert_holes(base):
    for phi in P.FEET_ANGLES:
        x, y = P.pol(P.FEET_R, phi)
        assert not base.is_inside(Vector(x, y, -23.5)) and base.is_inside(Vector(x + 3.5, y, -23.5))

def test_usb_tunnel_open_and_walled(base):
    assert overlap_volume(base, reference.usb_plug_probe()) == pytest.approx(0, abs=1e-3)
    x, z = P.USB_CENTRE_XZ
    assert base.is_inside(Vector(x - 8.0, -6.0, z)) and base.is_inside(Vector(x + 8.0, -6.0, z))

def test_psu_slot_width(base):
    assert not base.is_inside(Vector(P.PSU_SLOT_X, -12, P.J1_WIRE_Z))
    assert base.is_inside(Vector(P.PSU_SLOT_X - 3.6, -12, P.J1_WIRE_Z))
    assert base.is_inside(Vector(P.PSU_SLOT_X + 3.6, -12, P.J1_WIRE_Z))

def test_base_clears_board(base, board):
    assert min_clearance(base, board) >= 2.0
```

- [ ] **Step 2: Run them and see them fail.** Expected: FAIL with an ImportError.
- [ ] **Step 3: Implement `joint.py` and `base.py`.**
- [ ] **Step 4: Run the tests and see them pass.** Expected: PASS. If `test_base_clears_board` fails, fix the base, never the threshold.
- [ ] **Step 5: Commit.** Use the message `housing: base with tray, drum wall, joint, feet and openings`.

---

### Task 6: Sensor B mount: lower tower and adjustable head

Mechanism (Claude's choice among the spec's options):
- **Push-pull height adjustment from below.** Two pull screws (M4 × 35, socket head) come up through the floor and lower tower into inserts in the head. Two push set screws (M4 × 25) in inserts in the lower tower press on the head's underside.
- **Location:** a tongue on the lower tower runs in a groove in the head.
- **Why this one:** it keeps the user's two M4 inserts at 37 mm, it adjusts continuously with the disc in place, and it adds no depth towards the drive.

**Files:**
- Create: `housing/src/housing/b_head.py`, `housing/tests/test_b_mount.py`
- Modify: `housing/src/housing/base.py` (add the lower tower in `build_base`)

**Interfaces:**
- Consumes: `params.B_*`, `reference.coil_b`, `reference.drive_box`, `checks.*`.
- Produces:
  - `b_head.build_b_head(bar_top_z: float = B_BAR_TOP_NOM) -> Part`: the head in its position of use.
    - Wall r (`B_FACE_R` − `B_WALL_T`)…`B_FACE_R`, ±`B_HALF_T`, from `bar_top_z` − `B_HEAD_H` up to `bar_top_z` − 0.5.
    - Two radial M4 insert holes from the face at t ±`B_HOLE_SPACING`/2, Z `bar_top_z` − `B_HOLE_BELOW_TOP`, in Ø9.5 bosses reaching back to r `B_FACE_R` − `M4_INSERT_LEN` − 1.
    - Two vertical M4 insert holes from the bottom at t ±`B_PULL_T`, in bosses r 70–79.5.
    - A bottom groove r 74.0–78.0, ±24.0, 6 deep.
    - A relief pocket in the face behind the coil body, 1.5 deep, ±11 wide, from 1 mm below the bar top down 12 mm, for the wire exit (spec, "Wall").
  - `b_head.head_bottom_z(bar_top_z: float) -> float`.
  - `base.lower_tower() -> Part`, added to `build_base`.
    - Same footprint, from `FLOOR_TOP_Z` to `B_LOWER_TOP_Z`.
    - A tongue r 74.2–77.8, ±23.8, 5 tall.
    - Ø4.5 bores at ±`B_PULL_T` through the tower and floor, counterbored Ø8 × 4 from below.
    - M4 insert holes at ±`B_PUSH_T`, pressed in from below.

- [ ] **Step 1: Write the failing tests.**

```python
@pytest.mark.parametrize("top", [21.5, 24.0, 24.5])
def test_head_range_and_height(top):
    h = build_b_head(top)
    assert h.bounding_box().max.Z <= 24.0 + 1e-6                        # nothing above Z 24
    gap = head_bottom_z(top) - P.B_LOWER_TOP_Z
    assert 0.5 - 1e-6 <= gap <= 3.5 + 1e-6 and 5.0 - gap >= 1.5          # tongue stays engaged

def test_bar_inserts_at_37mm_and_5_below_top():
    h = build_b_head(24.0)
    for t in (-18.5, 18.5):
        x, y = P.pol(P.B_FACE_R - 3.0, P.B_PHI, t)
        assert not h.is_inside(Vector(x, y, 19.0))                       # insert hole on the axis
        assert h.is_inside(Vector(x, y, 19.0 + 4.0))                     # material around it

def test_b_parts_clear_the_drive():
    for top in (21.5, 24.5):
        assert min_clearance(build_b_head(top), reference.drive_box()) >= P.B_DRIVE_CLEARANCE
    assert min_clearance(lower_tower(), reference.drive_box()) >= P.B_DRIVE_CLEARANCE   # from housing.base

def test_coil_fits_head_and_base(base):
    for top in (21.5, 24.5):
        coil = reference.coil_b(top)
        assert overlap_volume(coil, build_b_head(top)) == pytest.approx(0, abs=1e-2)
        assert overlap_volume(coil, base) == pytest.approx(0, abs=1e-2)
```

- [ ] **Step 2: Run them and see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement `b_head.py` and `base.lower_tower()`.**
- [ ] **Step 4: Run the tests and see them pass.** The whole suite stays green.
- [ ] **Step 5: Commit.** Use the message `housing: sensor B push-pull mount`.

---

### Task 7: Cover: shell, joint, ridges, sensor C boss

**Files:**
- Create: `housing/src/housing/cover.py`, `housing/tests/test_cover.py`

**Interfaces:**
- Consumes: `params.*`, `joint.tab_solid`, `joint.key_tab`, `threads.thread_negative`, `threads.M16X1_5`, `reference.*`, `checks.*`.
- Produces `cover.build_cover(thread: ThreadSpec = M16X1_5) -> Part` (vents and stops are added in Task 8):
  - plate: `drum_outline(DRUM_R_IN + DRUM_WALL, FLAT_Y_IN − DRUM_WALL)` at Z `PLATE_Z`;
  - wall: r 113–117 with the flat, from `SEAT_Z` to `PLATE_Z[0]`;
  - lip: outer half r 115–117 from `LIP_BOTTOM_Z` to `SEAT_Z`;
  - six `joint.tab_solid` tabs and `joint.key_tab`;
  - `RIDGE_N` ridges at φ = k·45°: `RIDGE_T` thick, from the ring's outer radius to the wall, from Z `RIDGE_BOTTOM_Z` to the plate;
  - the ring at `RING_R`, same Z range;
  - the C boss: Ø`C_BOSS_D` at `pol(MAGNET_R, C_PHI)`, from Z `C_BOSS_UNDER_Z` to the plate, with a web `C_WEB_W` wide to the wall;
  - `thread_negative(thread, PLATE_Z[1] − C_BOSS_UNDER_Z)` subtracted at the C axis, starting at Z `C_BOSS_UNDER_Z`.

- [ ] **Step 1: Write the failing tests** (`cover` is a session fixture).

```python
def test_cover_extent(cover):
    bb = cover.bounding_box()
    assert bb.max.Z == pytest.approx(54.4, abs=1e-3) and bb.min.Z == pytest.approx(-12.0, abs=1e-3)
    assert bb.size.X <= P.BED - 2 * P.BED_MARGIN and bb.size.Y <= P.BED - 2 * P.BED_MARGIN

def test_nothing_low_over_the_disc(cover):
    zone = Pos(*P.SPINDLE, 25.0) * Cylinder(104.0, 12.4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    assert overlap_volume(cover, zone) == pytest.approx(0, abs=1e-3)              # Z 25…37.4 inside r 104
    assert min_clearance(cover, reference.disc_envelope()) >= 3.99

def test_cover_and_base_touch_only_at_seat(cover, base):
    assert overlap_volume(cover, base) == pytest.approx(0, abs=1e-2)
    assert min_clearance(cover, base) == pytest.approx(0.0, abs=1e-3)

def test_cover_fits_only_one_way(cover, base):
    for turn in (50, 80, 130, 180, 230, 310):
        rotated = Pos(*P.SPINDLE) * Rot(0, 0, turn) * Pos(-P.SPINDLE[0], -P.SPINDLE[1]) * cover
        assert overlap_volume(rotated, base) > 1.0

def test_c_thread(cover):
    x, y = P.pol(P.MAGNET_R, P.C_PHI)
    assert not cover.is_inside(Vector(x, y, 45.0))
    assert cover.is_inside(Vector(x + 8.6, y, 45.0))

def test_cover_thread_matches_coupon(cover):
    x, y = P.pol(P.MAGNET_R, P.C_PHI)
    probe = lambda part, cx, cy, z: [part.is_inside(Vector(cx + r, cy, z)) for r in (7.4, 7.9, 8.2)]
    assert probe(cover, x, y, 45.0) == probe(build_thread_coupon(), -14.0, 0.0, 5.0)   # same clearance
```

  If the phase of the helix makes the last test flaky, compare at three Z values one pitch apart instead of one.
- [ ] **Step 2: Run them and see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement `cover.py`.**
- [ ] **Step 4: Run the tests and see them pass.** Expected: PASS.
- [ ] **Step 5: Commit.** Use the message `housing: cover shell, joint, ridges and C boss`.

---

### Task 8: Cover: loose-disc stops and vent holes

**Files:**
- Modify: `housing/src/housing/cover.py`, `housing/tests/test_cover.py`

**Interfaces:**
- Produces:
  - `cover.vent_hole_centres() -> tuple[list[tuple[float,float]], list[tuple[float,float]]]`, returning (inlet, outlet).
    - **Inlet:** a hexagonal lattice at `INLET_PITCH` about `SPINDLE` with |c| ≤ `INLET_R_MAX` (43 holes).
    - **Outlet:** φ = `OUTLET_START_DEG` + k·`OUTLET_STEP_DEG`, k = 0…23, alternating r `OUTLET_R[0]`/`OUTLET_R[1]`. Drop a hole when its edge is closer than `VENT_EDGE_CLEAR` to the flat's inner face, or closer than `VENT_EDGE_CLEAR` to C's boss.
  - `build_cover` adds:
    - Ø`VENT_D` through-holes in the plate at all centres;
    - four stop bosses Ø`STOP_BOSS_D` at `pol(STOP_R, a)` for a in `STOP_ANGLES`, from the plate down to `STOP_BOSS_BOTTOM_Z`, each with an M4 insert hole from the boss bottom (`M4_INSERT_LEN` + 1 deep) and an `M4_CLEAR_D` hole on through the plate.

- [ ] **Step 1: Write the failing tests.**

```python
def test_vent_pattern_rules():
    inlet, outlet = vent_hole_centres()
    assert len(inlet) == 43 and 18 <= len(outlet) <= 22
    pts = inlet + outlet
    assert min(math.dist(a, b) for a, b in itertools.combinations(pts, 2)) >= P.VENT_MIN_SPACING - 1e-6
    for r in [x / 10 for x in range(int(P.RING_R[1] * 10), int(P.DRUM_R_IN * 10))]:
        assert circle_fraction(outlet, P.VENT_D, r) <= P.VENT_CIRCLE_MAX + 1e-9
    c = P.pol(P.MAGNET_R, P.C_PHI)
    assert all(math.dist(o, c) >= P.C_BOSS_D / 2 + P.VENT_EDGE_CLEAR + P.VENT_D / 2 for o in outlet)
    assert all(y >= P.FLAT_Y_IN + P.VENT_EDGE_CLEAR + P.VENT_D / 2 for _, y in outlet)

def test_vents_are_holes(cover):
    inlet, outlet = vent_hole_centres()
    for x, y in inlet[:3] + outlet[:3]:
        assert not cover.is_inside(Vector(x, y, 53.0))

def test_stop_bosses(cover):
    for a in P.STOP_ANGLES:
        x, y = P.pol(P.STOP_R, a)
        assert not cover.is_inside(Vector(x, y, 45.0))                    # screw path open
        assert cover.is_inside(Vector(x + 4.5, y, 45.0))                  # boss material
        below = Pos(x, y, P.STOP_BOSS_BOTTOM_Z - 0.6) * Cylinder(6, 1.0)  # nothing under the boss bottom
        assert overlap_volume(cover, below) == pytest.approx(0, abs=1e-3)
```
- [ ] **Step 2: Run them and see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement the vents and stops in `cover.py`.**
- [ ] **Step 4: Run the tests and see them pass.** The Task 7 tests stay green.
- [ ] **Step 5: Commit.** Use the message `housing: cover stops and staggered vents`.

---

### Task 9: Analysis: loose-disc envelope and load checks

**Files:**
- Create: `housing/src/housing/analysis.py`, `housing/tests/test_analysis.py`

**Interfaces:**
- Consumes: `params.*`.
- Produces:
  - `loose_disc_envelope(stops: list[tuple[float,float,float]], ring: tuple[float,float] | None = None, n: int = 101) -> dict[str, float]`.
    - Each stop is (r, φ, clearance).
    - `ring` is (outer radius, clearance): a stop at every point inside that radius.
    - Returns `rim_rise`, `hub_lift`, `z_at_c` (at r `MAGNET_R`, `C_PHI`) and `drop_at_b` (at r `MAGNET_R`, `B_PHI`), all in mm.
    - Model: a rigid disc, with surface displacement z0 + tx·x + ty·y. The foot (r 16) stays on the flange, so z0 ≥ 16·|t|. The bore limits |t| ≤ `BORE_CLEARANCE`/`HUB_ENGAGEMENT`. Every stop limits z at its point to its clearance. Brute-force search over (tx, ty) on an n × n grid, at both z0 extremes. This is the method behind the spec's numbers.
  - `ridge_cantilever(force_n: float, arm_mm: float) -> tuple[float, float]`: (deflection mm, stress MPa) for the T-section of a 3 × 11.4 ridge under a 3 mm plate (30 mm effective flange), E = 2000 MPa.
  - `screw_shear_n(force_n: float) -> float`: equal sharing over `len(TAB_ANGLES)`.

- [ ] **Step 1: Write the failing tests.**

```python
def stops(gap=P.STOP_GAP):
    return [(P.STOP_R, a, gap) for a in P.STOP_ANGLES]

def test_stops_are_first_contact():
    e = loose_disc_envelope(stops())
    assert e["hub_lift"] <= P.STOP_GAP + 1e-6
    assert e["rim_rise"] <= 1.05                            # spec: 1.0
    assert e["z_at_c"] <= 0.75                              # spec: 0.73, C at 1.0 keeps ≥ 0.25
    assert e["drop_at_b"] <= 0.61                           # spec: 0.59, B at 1.0 keeps ≥ 0.39

def test_single_thumb_is_not_enough():
    e = loose_disc_envelope([(95.5, 180.0, 1.0), (60.0, 0.0, 1.0)], ring=(28.0, 2.0))
    assert e["rim_rise"] > 3.0

def test_fault_load_path():
    d, s = ridge_cantilever(20.0, P.DRUM_R_IN - P.STOP_R)
    assert d <= 0.12
    assert ridge_cantilever(100.0, P.DRUM_R_IN - P.STOP_R)[1] <= 26.0
    assert screw_shear_n(100.0) == pytest.approx(16.7, abs=0.1)
```

- [ ] **Step 2: Run them and see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement `analysis.py`.**
- [ ] **Step 4: Run the tests and see them pass.** Expected: PASS.
- [ ] **Step 5: Commit.** Use the message `housing: loose-disc envelope and load checks`.

---

### Task 10: Build pipeline: STEP, 3MF, assembly

**Files:**
- Create: `housing/src/housing/build.py`, `housing/tests/test_build.py`
- Generated and committed: `housing/step/*.step`, `housing/*_P1S.3mf`

**Interfaces:**
- Consumes: every `build_*` function, `bambu3mf.*`, `reference.*`.
- Produces `build.main(out_dir: Path = HOUSING_DIR) -> None`, which writes:

| Part | STEP | 3MF (object name) | Print pose | Settings |
|---|---|---|---|---|
| base | `step/base.step` | `housing_base_P1S.3mf` ("01 base (PETG)") | as modelled | `layer_height` 0.2, `wall_loops` 4, `sparse_infill_density` 25%, `sparse_infill_pattern` gyroid, `top_shell_layers` 5, `bottom_shell_layers` 4, `enable_support` 0 |
| cover | `step/cover.step` | `housing_cover_P1S.3mf` ("02 cover (transparent PETG)") | rotate 180° about X | `layer_height` 0.2, `wall_loops` 4, `sparse_infill_density` 100%, `enable_support` 0 |
| B head | `step/b_head.step` | `housing_b_head_P1S.3mf` ("03 B head (PETG)") | as modelled | as base, with `sparse_infill_density` 40% |
| coupon | `step/thread_coupon.step` | `thread_coupon_P1S.3mf` ("04 thread coupon (PETG)") | as modelled | as B head |

  - It also writes `build/assembly.step`: base, cover, B head at nominal, `drive_box`, `disc_envelope`, `coil_b(24.0)`, `sensor_c(1.0)` and `load_board()`.
  - Each 3MF is a separate file because every part fills the bed. This is a plan-level choice; the spec said "a 3MF".
  - `make-housing build` runs `main()`.

- [ ] **Step 1: Write the failing test.**

```python
def test_build_writes_everything(tmp_path):
    main(tmp_path)
    for f in ["step/base.step", "step/cover.step", "step/b_head.step", "step/thread_coupon.step",
              "housing_base_P1S.3mf", "housing_cover_P1S.3mf", "housing_b_head_P1S.3mf",
              "thread_coupon_P1S.3mf", "build/assembly.step"]:
        assert (tmp_path / f).stat().st_size > 0
    for f in tmp_path.glob("*.3mf"):
        mesh = read_mesh(f)                         # test helper: parse 3D/3dmodel.model
        assert is_watertight(mesh)
        zs = [v[2] for v in mesh.vertices]
        assert min(zs) == pytest.approx(0.0, abs=1e-6)
        xs = [v[0] for v in mesh.vertices]; ys = [v[1] for v in mesh.vertices]
        assert max(xs) - min(xs) <= 252 and max(ys) - min(ys) <= 252
```

- [ ] **Step 2: Run it and see it fail.** Expected: FAIL.
- [ ] **Step 3: Implement `build.py`.**
- [ ] **Step 4: Run the tests and see them pass.** Expected: PASS.
- [ ] **Step 5: Generate the deliverables.** Run `housing/make-housing build`. Then open `housing/build/assembly.step` in FreeCAD and do a visual sanity pass: the cover sits on the base, the disc sits inside, and B and C are in place. Note anything odd in the commit message.
- [ ] **Step 6: Commit.** Run `git add housing/src housing/tests housing/step housing/*.3mf` and commit with the message `housing: build pipeline and generated STEP/3MF`.

---

### Task 11: Documentation

**Files:**
- Create: `housing/README.md`, `housing/CLAUDE.md`
- Modify: `disk/README.md` (assembly step 2)

- [ ] **Step 1: Write `housing/README.md`** in the style of `disk/README.md`. Sections:
  - **What it is:** a closed drum, the parts and the files.
  - **Parts and print settings:**
    - Give Bambu Studio paths in German, e.g. *Prozess → Global*.
    - Print the cover in the SUNLU transparent PETG.
    - Print order: thread coupon first.
  - **Bill of materials:**
    - 16 Ruthex M4 × 8.1: 2 for the B bar, 2 pull, 2 push, 6 joint, 4 stops;
    - 5 Ruthex M3 × 5.7 (feet);
    - 6 × M4 × 12 pan head + washers (cover);
    - 2 × M4 × 35 socket head (pull) and 2 × M4 × 25 set screws (push);
    - 2 × M4 × 10 + washers (B bar);
    - 4 × M4 × 30 nylon screws + 4 nuts (stops);
    - 5 × M3 screws for the feet;
    - the user's four 6-32 drive screws.
  - **Assembly:** inserts, base onto the drive (holes 4/5/9/10, the user's screws from below), feet, B head, cover. JP1 is only reachable with the base off.
  - **Adjustments:**
    - **B height:** with the cover off and the disc on, loosen the pull screws. Set the gap to 1 mm with the push screws from below (1 turn = 0.7 mm), checking with a feeler gauge, then tighten the pull screws.
    - **C gap:** 1–10 mm, set by turning the sensor, locked with the nut.
    - **Stops:** turn each down until it just drags at the disc's high point, then back off 7/8 turn (0.6 mm). Rule: about 60 % of the smaller sensor gap.
  - **Acceptance checks:**
    - Thermal: measure the 12 V input power at a steady 3000 rpm, then run ≥ 1 h with the drum closed. Inside air must be ≤ 15 K above room; otherwise add Ø4 cover holes.
    - What the drum guards against, and what it does not (burst containment is not claimed).
  - **Regenerating:** run `hdd-driver/scripts/export-test-model` first, then `housing/make-housing test` and `housing/make-housing build`.
- [ ] **Step 2: Write `housing/CLAUDE.md`** in the style of `hdd-driver/CLAUDE.md`:
  - `src/` is the source; `step/`, `*.3mf` and `build/` are generated.
  - Numbers only in `params.py`.
  - The venv is Python 3.12, through uv.
  - The board export must be fresh.
  - Frame and Z conventions.
- [ ] **Step 3: Add to `disk/README.md` assembly step 2:** "Use medium-strength threadlocker on the six M2 clamp-ring screws."
- [ ] **Step 4: Verify.** Run `housing/make-housing test`. Expected: all tests pass. Then run `git status`. Expected: only the files of this task are changed.
- [ ] **Step 5: Commit.** Use the message `housing: README, folder notes, clamp-screw threadlocker note`.
