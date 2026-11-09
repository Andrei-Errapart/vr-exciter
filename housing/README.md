# Closed-drum housing for the exciter

A 3D-printed drum round the gutted HDD and the magnet disc (`../disk/`). The
base covers the driver board and stands on rubber feet. It holds sensor B (the
pickup coil) under the magnet ring. A transparent cover closes the drum over
the disc and holds sensor C (a threaded magnetic sensor) above it. Four nylon
stops in the cover keep a loose disc on its spindle.

The parts are parametric build123d models. Every number is in
`src/housing/params.py`.

## Files

| Path | Content |
|------|---------|
| `housing_base_P1S.3mf` | Base: tray, drum wall, joint, feet. 233.9 × 226.9 × 27.5, printed floor down |
| `housing_cover_P1S.3mf` | Cover: wall, plate, ridges, stops, C boss. 238.0 × 226.9 × 66.4, printed top face down |
| `housing_b_head_P1S.3mf` | B head: carries the coil bar, adjusts in height. Printed upright |
| `thread_coupon_P1S.3mf` | Test pieces for the sensor threads. Print first |
| `step/*.step` | The same four parts as STEP |
| `build/assembly.step` | Whole assembly with the board, about 29 MB. Generated, not in git |
| `src/housing/`, `tests/` | Source and tests; see `CLAUDE.md` |

The 3MFs carry their process settings per object: 0.2 mm layers, 4 walls, no
supports. Infill: base 25 % gyroid, B head and coupon 40 %, cover 100 %. In
Bambu Studio open the 3MF, pick the filament, check the *Vorschau*, slice.

## Parts and print settings

| Part | Filament |
|------|----------|
| base, B head, thread coupon | PETG |
| cover | SUNLU transparent PETG (you can see the disc turn; 100 % infill) |

Print order:

1. **Thread coupon.** It has M16×1.5 (sensor C) and 5/8"-18 UNF test pieces.
   Screw the sensor into them. If a thread is too tight or too loose, change
   `THREAD_CLEARANCE` in `params.py` and rebuild before printing the cover.
2. B head, then the base, then the cover.

The base and cover nearly fill the P1S bed (256 mm). Keep them as the 3MF
places them.

## Bill of materials

| Qty | Part | Where |
|-----|------|-------|
| 16 | Ruthex M4 × 8.1 heat-set insert | 2 B bar, 2 pull, 2 push, 6 joint, 4 stops |
| 5 | Ruthex M3 × 5.7 heat-set insert | feet, pressed in from below |
| 6 | M4 × 12 pan head + washer | cover to base, radial through the tabs |
| 2 | M4 × 30 socket head (ISO 4762) | B pull screws, from below |
| 2 | M4 × 20 set screw (ISO 4026) | B push screws, from below |
| 2 | M4 × 10 + washer | coil bar to B head |
| 4 | M4 nylon screw, about 30 long, + 4 M4 nuts | stops; the nut locks on top of the cover |
| 5 | rubber foot with M3 screw | length to suit; the insert is 5.7 deep |
| 4 | 6-32 UNC drive screws | yours, from below into holes 4/5/9/10 |
| 1 | medium-strength threadlocker | the disc's six M2 clamp-ring screws (`../disk/README.md`) |

Sensor C comes with its own 24 AF nut, which locks it on top of the cover.

## Assembly

Frame: X, Y as in `../hdd-driver/README.md` (bottom view, connector end at
Y 0). Z is height above the drive's underside, up towards the disc.

1. **Inserts.** Heat-set them square to the face.
   - Base: 6 M4 in the joint bosses (pressed in radially from outside),
     5 M3 in the feet pads (from below).
   - B head: 2 M4 in the face (coil bar), 2 M4 in the bottom (pull screws).
   - B lower tower: 2 M4 in the bottom (push screws), recessed 3 mm.
   - Cover: 4 M4 in the stop bosses, from the boss bottom.
2. **Base onto the drive.** The base touches the drive only at its four screw
   bosses. Fasten it with your four 6-32 screws from below through the hollow
   bosses into holes 4, 5, 9, 10. JP1 (12 V / USB) is reachable only with the
   base off, so set it first.
3. **Feet.** Screw the five rubber feet into the M3 inserts.
4. **Disc.** Mount it on the spindle as in `../disk/README.md`.
5. **B head.** Fit the coil bar with the two M4 × 10 screws. Put the head on
   its lower tower (the tongue runs in the head's groove), then fit the two
   pull and two push screws from below. Plug B's cable into J3: it enters
   through the 6 mm slot in the tray's right wall at Y 15, and rests in the
   two hooks outside that wall. Set the height (next section).
6. **12 V.** The wires leave straight out through the end-wall slot and the
   6 mm slot in the drum flat. A cable up to Ø6 passes under the cover lip.
7. **Cover.** Fit sensor C in the cover first. Lower the cover onto the base.
   The key fits one way only, which puts C at 180°, opposite the coil. Fit the
   six radial M4 × 12 screws with washers. To open the drum, remove the same
   six screws; the cover lifts off with C still in it.
8. **Stops** (next section).

## Adjustments

**B height.** Cover off, disc on and stopped.

1. Tip or lift the tray to reach the floor underside.
2. Loosen the two pull screws.
3. Set the gap between pole and disc underside to **1.0 mm** with the two
   push screws (M4: one turn is 0.7 mm). Check with a feeler gauge.
4. Tighten the pull screws.

To lower the head, first back the push screws off. The bar top ranges over
Z 21.5 to 24.5 (nominal 24.0).

**C gap.** 1 to 10 mm above the disc. Turn the sensor in its M16 thread, then
lock it with its nut on top of the cover.

**Stops.** With the cover on:

1. Turn each nylon stop down until it just drags on the disc at the disc's
   highest point. Turn the disc by hand to find that point.
2. Back it off **7/8 turn** (0.6 mm).
3. Lock it with its nut.

Rule: the stop gap is about 60 % of the smaller sensor gap, normally B's
1 mm. If you change B's gap, redo the stops.

## Acceptance checks

**Thermal.** The drum is closed, so check the heat once:

1. Measure the 12 V input power at a steady 3000 rpm.
2. Run at least 1 h with the drum closed.
3. Probe the inside air through the 12 V slot. It must stay at most 15 K
   above room temperature.
4. If it is hotter, add more Ø4 holes to the cover in the same pattern.

## What the drum guards against

It does:

- **Keep fingers off the disc.** The openings that remain are the USB tunnel
  (leads only to the USB port), the 12 V slot (6 mm wide), the floor holes
  into the electronics bay (at most Ø5 or 4 mm wide), the drive-screw bores
  (closed by the screws), C's thread (filled by the sensor) and the Ø4 cover
  vents.
- **Hold a loose disc on its spindle.** If the clamp-ring screws work loose,
  the four stops limit the hub lift to 0.6 mm and the rim rise to about
  1.0 mm. C keeps about 0.27 mm and B about 0.39 mm (`analysis.py`). Use
  threadlocker on those six M2 screws.
- **Keep the magnets in.** They are printed in and tight. They come free only
  if the disc itself fails.

It does **not** claim to contain a disc that breaks up. That would release
about 45 J at 3000 rpm with 20 % infill, about 90 J if solid. The drum is a
barrier, but its strength against fragments is not verified.

## Regenerating

The tests compare the housing with the real board, so the board export must be
fresh. They refuse a stale one.

    hdd-driver/scripts/export-test-model   # first
    housing/make-housing test              # checks
    housing/make-housing build             # writes step/, *.3mf, build/assembly.step

`make-housing` creates `.venv` (Python 3.12, through uv) on first run. To
change a dimension, edit `src/housing/params.py`, run the tests, then build.
