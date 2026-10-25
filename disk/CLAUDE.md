# CLAUDE.md — disk/

Rotor for a VR-sensor exciter: a printed Ø202 mm disc with 60 magnets on an
HDD spindle, running at 3000 rpm to give 3000 Hz. Read `README.md` for the
design, dimensions, print and assembly steps, and open items.

## Contents

- `magnet_disc_60_P1S.3mf` is the **only** model. The user removed the older
  coupons and variants on purpose. Don't recreate them or refer to them as
  existing files.
- `hdd-photos/` holds measurement photos. They are named
  `NN-<what>-<value>mm.jpg`; follow that scheme for new photos.

## Working with the 3MF

- It's a zip file. Unpack it into the scratchpad, never into the repo:
  - `3D/3dmodel.model` holds the meshes. Objects 1–4 are the parts and
    object 5 is the assembly.
  - `Metadata/model_settings.config` holds the part names, the per-part
    extruder (filament slot) and the process overrides.
  - `Metadata/custom_gcode_per_layer.xml` holds the magnet pause
    (`top_z="4"`, `M400 U1`).
- Part names encode their role, z range and filament slot, e.g.
  `03 magnet band, z 0.6-3.8 (filament 2)`. Keep that convention, and keep
  the names in sync with the geometry if you change it.
- The coordinates are in print orientation: numbered face on the plate at
  z = 0, and the disc centre at the origin before the plate transform
  (128, 128).
- To check geometry, read the vertex radius √(x²+y²) and the z levels from
  the model XML. That is quicker and more reliable than reasoning from the
  part names.

## Design constraints (don't change without a reason)

- Magnet circle r ≈ 95.5, 60 × Ø5.2 × 3.2 pockets, pitch ≈ 10 mm.
- Lid 0.6 mm: this is the sensor gap budget.
- Spindle bore Ø25.2 (hub measured at 25.01). Counterbore Ø32.6 (clamp ring
  measured at 31.97).
- **Clamp-ring seat 8.5 mm above the bottom of the hub tube** (z = 12.16 in
  print coords). Raising it, e.g. to 8.7, adds preload. **Lowering it below
  the hub top (8.52 measured) leaves the disc unclamped.** An earlier answer
  got this backwards.
- The pause must stay right after the magnet band, before the first body
  layer. Bambu Studio pauses *before* the selected layer.
- Supports must not go into the magnet pockets.
- All magnets have the same pole toward the lid, which faces the sensor in
  use. The sensor sits above the face, not at the rim.

## User context

- Printer: Bambu Lab P1S with AMS, filament PETG (including a third-party
  SUNLU transparent spool).
- Bambu Studio runs with a German UI. Give UI paths in German, e.g.
  *Prozess → Global → Stützen*, *Vorschau*, *Pause hinzufügen*,
  *Sync Infos*.
- The sensor mount and the spindle driver are not designed yet. Ask for the
  sensor body diameter and mounting style before modelling a mount.
