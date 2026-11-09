# HDD housing extension: closed drum with sensor mounts

Date: 2026-11-09. Status: approved by the user on 2026-11-09, built 2026-11-09/10 (changes listed at the end). Reworked as a closed drum
after a review on 2026-11-09.

## Why

The exciter is now running. The magnet disc (`disk/`) turns on the gutted HDD
and the driver board (`hdd-driver/`) is screwed to the drive's underside. The
modules on that board (WeAct, SimpleFOC Mini, MT3608) stick out about 16 mm
below the drive, so the whole assembly currently **stands on the modules**.
The disc is also not safe to leave open at 3000 rpm (user).

The housing extension is a printed **closed drum** round the drive and the
disc:

1. its base covers the board and the modules, and stands on rubber feet;
2. the base holds the **pickup coil** (sensor B) under the magnet ring;
3. a transparent cover closes the drum over and round the disc;
4. the cover holds a **threaded magnetic sensor** (sensor C) above the
   magnet ring.

## Goals

- The drive stands on rubber feet, never on the electronics.
- The board and modules are enclosed. The base never touches them, and it
  never pushes on the board: the board's spring contacts to the motor must
  not be disturbed.
- The base is held by the drive's four bottom mounting holes, using the
  user's existing drive screws.
- Sensor B (pickup coil) sits under the magnet ring, pole facing up, with a
  1 mm gap to the disc underside that can be adjusted a little.
- The spinning disc is enclosed on **all** sides: top, sides (user) and
  bottom (review). What matters most (user): **fingers can't reach the
  disc, and the disc can't come loose and fly out** towards someone's eyes
  or neck.
- Sensor C (threaded sensor) is screwed into the cover above the magnet
  ring, tip down. You set the gap by screwing the sensor in or out and lock
  it with a nut. Its mount is noticeably sturdier than the minimum, because
  the sensor is heavy (user request).
- The cover goes back in the same place every time, so C's gap stays set.
- USB plugs in from outside with the drum closed. The 12 V wires stay in J1
  while the base is fitted.

## Non-goals

- Proving that the drum holds a bursting disc (see "What it is not shown
  to stop"). The user has no polycarbonate, which `disk/README.md` asks
  for, so the cover is printed.
- No change to the disc or the PCB.
- Sensor C's cable goes to other equipment, not to the board. The board has
  only one VR input (J3), and that belongs to B.

## Anti-goals (a failure even if it "fits")

- Anything that can touch the spinning disc, including a cover that sags.
  The disc rim moves at about 30 m/s.
- An opening that lets a finger reach the disc.
- Anything that presses on the modules or lifts the board.
- A sensor mount that vibrates enough to change the gap. The rotation is
  50 Hz, so keep mount resonances well above 100 Hz.

## Coordinates

- **X, Y:** the drive frame from `hdd-driver/README.md`. It's a bottom view
  with the connector end at the top: X to the right of the centre line, Y
  down from the connector end, in mm. Seen **from above**, with the connector
  end away from you, left and right swap: B is then on the left and C on the
  right.
- **Z:** height above the drive's underside, which is the face of holes
  4/5/9/10. It is positive towards the disc (up in use) and negative into the
  tray.
- Polar positions are about the spindle axis (0.2, 95.9). The angle φ is
  measured from +X, positive towards the connector end (−Y).

## Measured facts (user, 2026-11-09)

| What | Value |
|---|---|
| Drive footprint | 101.6 × 147 (X ±50.8, Y 0…147) |
| Drive height, underside to top edge of the casting | 22.66 |
| Disc underside above the drive underside | **25.0 … 25.4** (the spread is runout or measurement scatter) |
| Disc | Ø202, 8 mm thick, magnets Ø5×3 in a ring at r 95.5, 0.6 mm under the **top** face. So magnets at Z ≈ 29.2…32.8, disc top Z 33.0…33.4 |
| Board | flush with the faces of holes 4/5/9/10 (see "Tray depth") |
| Threaded sensor C | outside Ø 15.85, 10 threads ≈ 15 mm → **M16×1.5** |
| Pickup coil B | steel bar with 2 holes Ø5.2 at 37 mm. Hole centres **5.0 below the bar's top edge** (2.4 from hole edge to top edge). Body 20.5 wide along the bar, sticks out 23 mm **from the wall** (the bar's back face), total height 19.4 from the bar's top edge down; pole face (Ø≈6) on top of the body, 16 mm from the wall, its top level with the bar's top edge. The pole looks centred between the holes in the product photo |
| Rubber feet | mounting holes for **M3** screws (user) |
| Magnets in the disc | placed in their pockets during a print pause, then printed over; a tight fit (user). A magnet only comes free if the disc itself fails |
| Threaded sensor C, other | pickup tip at one end, cable at the other; "the body is long enough" for a threaded hole plus a lock nut; "pretty heavy" (not weighed) |

The board, module and connector positions in this document were read from
the current `hdd-driver/hdd-driver.kicad_pcb`. Take exact values from that
file.

The 3D export in `hdd-driver/build/test-model/` is **stale**. It was made on
25 Oct, before the layout changed: in it, J1 is at (−29.9, 60), J3 is
missing and the modules are elsewhere. Regenerate it with
`hdd-driver/scripts/export-test-model` before using it for anything.

## Layout

### Overview

- **Two printed halves** meet at Z 0, the drive's underside:
  - the **base** (PETG): the tray round the electronics, the drum floor,
    the lower drum wall and B's tower, in one piece;
  - the **cover** (transparent PETG): the upper drum wall, the top plate
    and C's threaded boss, in one piece.
- **Drum wall:**
  - Inner face at **r 113** round the spindle, 4 mm thick, so the outside
    is Ø234.
  - At the connector end the wall is **flat**: inner face at Y −10 between
    X ±39.4, outer face at Y −14. The flat keeps the USB tunnel short. It is
    4.9 mm from the disc rim at its closest.
- **Clearances inside the wall:**
  - drive corners 4.6 mm (they are at r 108.4);
  - B's coil body 10.5 mm;
  - disc rim ≥ 4.9 mm at the flat, 12 mm elsewhere.
  - The tray's two connector-end corners (r 112.1) merge into the wall.
- **Size:** X ±117, Y −14…212.9. Both halves fit the 256 × 256 bed.

### Base: tray

- **Footprint:** the tray goes *around* the drive footprint, not inside it.
  - Inner outline: the drive footprint plus 0.3 mm all round.
  - Walls 2.4 mm thick, so the outside is about X ±53.5, Y −2.7…149.7.
  - Reason: the WeAct board, J1 and J3 reach to Y ≈ 1. An end wall inside
    the footprint would hit them.
- **Tray depth:**
  - Two readings of "flush" are possible. If the board's outer face is at
    Z 0, the lowest point is Z −16 (WeAct board with its USB-C). If the
    board's drive-side face is at Z 0, it is Z −17.6.
  - Design for −17.6.
  - Floor top at **Z −21.0** (≥ 3.4 mm clear), floor 3 mm, underside at
    **Z −24.0**.
- **Contact with the drive:** only through the four screw bosses, which
  touch at Z 0. The tray wall tops stop at Z −0.5, so an uneven casting
  can't make the base rock or bend.
- **Screw bosses at holes 4, 5, 9, 10:**
  - Positions: (−47.625, 41.28), (47.625, 41.28), (−47.625, 85.73),
    (47.625, 85.73). The holes take 6-32 UNC.
  - Each boss is hollow and open through the floor. At its top is a 3 mm
    ledge with a 3.8 mm clearance hole.
  - The user's drive screw goes in from below, through the bore. Its head
    sits on the ledge.
  - The bore is ≥ 8 mm, for a pan head and a screwdriver.
  - The bosses merge into the side walls.
- **Openings in the tray's end wall (Y −2.7):**
  - J1 12 V terminal (X ≈ −30…−15.5): slot open from the wall's top edge,
    so the base can be fitted with the wires already in place.
  - J3 VR terminal (X ≈ 21…31): slot open from the top, for B's cable,
    which now stays inside the drum.
  - WeAct USB-C: a window big enough for a plug overmold (14 × 9). Its
    centre is at about X −2.4, Z −15.8. Confirm both from the regenerated
    3D model.
- **Floor holes into the electronics bay:**
  - Ø5 poke holes under the WeAct's push-buttons and the MT3608 trimmer.
  - A few vent slots, at most 4 mm wide, under the SimpleFOC Mini and the
    MT3608.
  - JP1 is only reachable with the base off.

### Base: drum floor and wall

- **Floor:** one plate with the tray floor, Z −24…−21, filling the whole
  drum outline. The underside is flat for printing. Any ribs go on top,
  inside the drum, away from the tray.
- **Wall:** r 113–117 (with the flat) from the floor up to Z 0. Its top
  5 mm, Z −5…0, is thinned to the inner half for the joint (see "Joint").
- **Heat and vents:**
  - Everything the 12 V input delivers at steady speed ends up as heat
    inside the drum:
    - air drag on the disc (1.5 W for ideal smooth faces, several watts
      plausible);
    - bearing friction;
    - losses in the motor, DRV8313, MT3608 and WeAct.
  - A rough guess is 3–10 W in total. With about 0.14 m² of drum surface,
    that is very roughly 2–7 K above room.
  - **Vent holes in the cover (user's idea):** one group near the axis and
    one round the outer edge (see "Cover"). The spinning disc acts as a
    centrifugal fan: it draws air in near the axis and pushes it out at the
    rim. Holes in both places therefore give a through-flow, not just
    leaks.
  - The electronics bay keeps its floor vents to the outside.
  - **Acceptance check:**
    1. Measure the 12 V input power at a steady 3000 rpm.
    2. Run for at least 1 h with the drum closed. Measure the air inside
       near the board (a probe through the 12 V slot) and the room.
    3. Accept if the inside is at most **15 K** above room.
    4. Otherwise add more cover holes of the same size.
- **Openings in the flat:**
  - **USB tunnel:**
    - A closed rectangular tube, 14 × 9, from the flat's outer face to
      the tray's USB window, about 11 mm long. It is sealed to both walls,
      so it opens only onto the USB port.
    - The plug must reach about 14 mm in from the outer face. Flare the
      outer end (about 20 × 14) so fingertips can grip a short overmold.
      Check this with the user's cable.
  - **12 V slot:**
    - In line with J1 (X ≈ −23), at J1's wire height (confirm from the
      model).
    - Open from the wall's top, so the wires drop in as the base is fitted.
      The cover's overlap closes its top.
    - **At most 6 mm wide**; it takes a cable up to Ø6.

### Base: feet

- Five M3 brass heat-set inserts (M3 × 5.7, as Ruthex), pressed in from
  below, in solid pads. The user's rubber feet take M3 screws.
- On a pentagon at r ≈ 104 round the spindle:

  | φ | Position | Where |
  |---|---|---|
  | 180° | (−103.8, 95.9) | directly under C |
  | 252° | (−31.9, 194.8) | drum floor |
  | 324° | (84.3, 157.0) | drum floor |
  | 36° | (84.3, 34.8) | drum floor |
  | 115° | (−43.8, 1.6) | tray floor, outside the board area |

- With 0.5 kg at C, the centre of gravity is at about (−26, 91). That is
  26 mm off centre, well inside the pentagon, whose inner radius is 84 mm.
- Their rubber gives enough to take up the fifth foot.

### Sensor B: pickup coil under the ring (user's choice "B")

- **Position:** φ = 20°, on J3's side. Pole centre at **(89.9, 63.2)**,
  r 95.5. That is about 9 cm from J3.
- **Tower:**
  - A wall whose face is tangential at r 79.5 and faces outwards.
  - The coil's steel bar lies flat on that face. The body points radially
    outwards, so the pole lands on r 95.5 and the body's far end is at
    r 102.5, under the disc edge.
  - It stands on the drum floor.
- **Fixing:**
  - Two M4 heat-set inserts, 37 mm apart along the tangent and symmetric
    about the radius. The bar is held with M4 screws and washers through its
    5.2 mm holes.
  - Insert axes 5.0 mm below the bar top: **Z 19.0** at the nominal height,
    Z 16.5…19.5 over the adjustment range below.
  - With the cover off, the screws are reachable horizontally from outside
    the disc rim. The base wall stops at Z 0, below them.
- **Height:**
  - The bar top (= pole top) is at **Z 24.0** nominal, 1.0 mm under the
    lowest measured disc underside. The body bottom is then at Z 4.6.
  - The nominal height must be adjustable over **at least Z 21.5…24.5**.
    The disc measurement (25.0–25.4) may not show the true lowest point at
    the magnet ring, and the disc moves at 30 m/s. The builder chooses how:
    - the inserts in a small carrier block clamped to the tower through
      vertical slots, or
    - a bolt-on tower raised with printed shims.
    Either way, the user's "two inserts at 37 mm" stays.
  - The pole is about 5.2–5.6 mm from the magnets, through 4.2 mm of PETG.
    This was accepted; reprinting the disc magnets-down is the fallback if
    the signal is too weak.
- **Wall:**
  - About 52 wide × 7 thick, rising from the floor to Z ≈ 23. Nothing of
    the tower may be above Z 24 under the disc.
  - Ribs on the back.
  - A shallow relief pocket in the face behind the coil body, for the wire
    exit and anything that sticks out behind the bar. The coil's wires
    leave the body sideways, close to the bar.
- **Clearances:** body and tower ≥ 8 mm from the drive's side. Beyond
  φ ≈ 25° the tower would hit the drive.
- **Cable:** inside the drum, along the outside of the tray's right wall,
  round the corner and into J3's slot. Two small cable hooks on the tray
  wall are enough.

### Sensor C: threaded sensor in the cover (user's idea)

- **Position:** φ = 180°, on the side opposite B, straight out from the
  spindle. The sensor axis is at **(−95.3, 95.9)**, 17.5 mm in from the
  drum wall's inner face.
- **Held by the cover.** Taking the cover off for disc access takes C with
  it. When the cover goes back on, C returns to the same height, so its
  gap stays set.
- **Sensor:**
  - Vertical, tip down. The gap to the disc top is **adjustable from 1 to
    10 mm** (user): tip from Z 34.4 to Z 43.4. At 1 mm the tip is about
    1.6–2.0 mm from the magnets.
  - At 10 mm the tip sits 6 mm up inside the boss, with 11 mm of thread
    still engaged plus the nut. The boss is PETG and doesn't affect the
    field.
  - The user sets the gap by turning the sensor and locks it with their nut
    on top of the cover.
- **Boss:**
  - Hangs from the underside of the top plate. Ø30 round the hole.
  - Internal **M16×1.5** thread through the boss and the plate, about
    17 mm long.
  - Boss underside at **Z 37.4** (4 mm above the highest disc top).
  - Leave free room above the cover for the nut (24 AF) and the cable
    leaving upwards.
  - Ribs tie the boss to the drum wall and the plate. Together they form a
    short, deep bracket. A rough hand estimate for that bracket alone is
    about 900 Hz with 0.5 kg.
- **Thread length:** the 1 mm setting needs the most, about 33 mm of
  thread from the tip: 3 mm below the boss, 17 mm of boss and plate, plus a
  13 mm nut. The user says the body is long enough. Check that before
  printing the boss.
- **Sensor weight:** not weighed. Design for **0.5 kg** at the boss, so
  there is margin over the "pretty heavy" description.

### Cover

- **Material:** transparent PETG (Claude's assumption). Printed
  "transparent" PETG comes out translucent: the disc will be visible, but
  not crisply.
- **Top plate:**
  - **Z 51.4…54.4** (3 mm). It stays at this height so that C gets 17 mm
    of thread.
  - Closed except for C's threaded hole and the vent holes.
- **Wall:** continues the base wall from Z 0 up to the plate, at r 113–117
  and with the same flat. Its bottom 5 mm (Z −5…0) is the outer half only,
  r 115–117, and overlaps the base wall (see "Joint").
- **Internal ridges (user's idea), the cover's main stiffening:**
  - About **8 radial ridges**, 3 mm thick, on the underside of the plate.
    They run from the wall in to a central ring (r 30–33). One of them
    runs through C's boss.
  - Inside r 104 they hang down to **Z 40**, about 11 mm deep and 6.6 mm
    over the disc.
  - The central ring only joins the ridges. It stays at Z 40 like them;
    it is no longer a stop.
  - They block some of the view, which is accepted.
- **Vent holes (user's idea):**
  - All are **Ø4 at most**, too small for a fingertip, and all are in the
    top plate, between the ridges.
  - **Spacing:** adjacent holes ≥ 7 mm apart, centre to centre. Holes are
    ≥ 3 mm from the ridges, the central ring, the wall and the stop
    bosses.
  - **Inlet group, inside the central ring (user's idea):**
    - A hexagonal pattern at 7 mm pitch, filling r ≤ 25: about 43 holes,
      about 540 mm² open.
    - The intact ring at r 30–33 carries the plate round it, so the
      perforated centre only has to hold itself. That is why it may be
      denser than the outer holes.
    - Below it is the slow hub (under 8 m/s at r 25) and the clamp ring.
    - The centre is also where the disc's fan action draws air in.
  - **Outside the central ring, staggered (user's idea):** holes at a
    single radius line up across the circle that carries the plate's
    bending, like the perforation on a stamp. Rule: on any circle outside
    the central ring, holes take at most **25 %** of its length.
  - **Outlet group:** about 20 holes, every 15°, alternating between r 105
    and r 108.5, so the two radii form a zig-zag:
    - they start 7.5° off the ridges, so none sits on one;
    - they lie over the gap between the disc rim and the wall;
    - leave them out along the flat (gap under 5 mm) and near C's boss;
    - each circle loses under 10 %.
  - **None in the wall.** A hole at disc height would be a straight path
    out in the disc's plane, towards someone's eyes or neck.
  - Keep them clear of C's boss and its nut (≥ 3 mm from the boss), the
    ridges' roots, the central ring and the stop bosses.
  - The ridges carry the stiffness the holes take out of the plate.
- **Loose-disc stops (user's "thumb" idea, extended):**
  - **The fault:** the clamp ring's six M2 screws work loose. The disc can
    then lift and tilt on the spindle hub: its bore is Ø25.2 on Ø25.01,
    with 8.5 mm of engagement.
  - **Why not one stop near the hub** (review): C's tip and B's pole are
    only 1 mm from the disc, so any stop with more clearance than that is
    not the first contact. A 2 mm hub ring let C be hit first. Worst-case
    envelope with C at 1 mm and that ring: the rim rises 3.6 mm.
  - **Why not one thumb opposite C:** it limits the lift to 1 mm, but the
    disc can still tip sideways about the line between C and the thumb.
    The rim then still rises 3.3 mm.
  - **Design: four adjustable stops**:
    - At **r 75**, 90° apart: φ 0° (the user's thumb, opposite C), 90°,
      180° (in line with C) and 270°. Each sits on a ridge.
    - Each stop is an **M4 nylon screw** in an M4 heat-set insert, in a
      boss on its ridge. It comes down through the top plate (the screw
      fills the hole), is locked with a nut on top, and its free length
      below the boss is ≤ 5 mm.
    - r 75 lies on the plain plate face, inside the index numbers
      (r 86–90.6) and the magnet band. A rub there is at about 24 m/s,
      not 30.
  - **Setting:** do it like C. With the cover on, turn each stop down
    until it just drags on the disc at the disc's highest point (turn the
    disc by hand). Then back it off to **0.6 mm**: 7/8 turn of M4 × 0.7.
    General rule: about 60 % of the smaller sensor gap, which is normally
    B's 1 mm, since C's can be anything from 1 to 10 mm. If C or B is set
    closer than 1 mm, set the stops closer too.
  - **Worst-case envelope** at 0.6 mm (rigid disc on the flange, tilt
    limited by the bore and by the stops):
    - hub lift ≤ 0.6 mm (7.9 of 8.5 mm stays engaged);
    - rim rise ≤ 1.0 mm;
    - at C's tip, 0.73 mm (0.27 mm short of C);
    - drop at B's pole, 0.59 mm (0.41 mm short of B).
    - The stops are therefore the first contact, and the disc stays on its
      hub and far below the ridges.
  - **Normally they never touch.** In the fault, the rub brakes the disc
    hard. The motor is too weak to keep up, so it slows and stops, and the
    VR speed loop's stall detection (`hdd-driver/README.md`) sees it.
  - **Prevention (outside this design):** medium-strength threadlocker on
    the clamp ring's six M2 screws is the cheapest protection. That belongs
    in the disc assembly steps of `disk/README.md`.
- **Clearance over the disc:** nothing of the cover may be lower than
  Z 37.4 inside r 104, except the four stop tips.
- **Sag:** under its own weight plus 0.5 kg at C, the cover may sag at most
  0.2 mm anywhere above the disc.

### Joint between base and cover (the user's locating ridges)

- **Seat:** the cover's wall sits on the base wall's top face at Z 0. Make
  that face flat to within 0.3 mm.
- **Overlap:**
  - The cover's outer half (r 115–117) comes 5 mm down (to Z −5) over the
    base's inner half (r 113–115) all round.
  - It locates the cover in X and Y, and leaves no straight-through gap.
  - Leave 0.5 mm under its bottom edge, so the cover rests on the seat only.
- **Key:** one tab and notch fix the rotation, so C always lands at 180°.
- **Screw tabs (review: a 5 mm lip is too shallow for M4):**
  - **Where:** six, roughly evenly spaced. Keep them clear of the flat
    (φ ≈ 70–110°), the tray corners, B and the key.
  - **Tab:** the lip continues down to **Z −12** over a width of 16 mm and
    is thickened outward to r 119 (4 mm, r 115–119). Chamfer the
    thickening at 45° so it prints.
  - **Recess:** the base wall's outer half has a pocket for each tab, down
    to Z −12.5.
  - **Screw:** M4 × 12 pan head with a washer, radial, **axis at Z −7.0**,
    through a Ø4.5 hole in the tab. That leaves 2.75 mm of tab under the
    hole.
  - **Insert:** Ruthex M4 × 8.1 (outside Ø6.3; hole size from the maker's
    table), pressed in radially from outside. Its outer end is at r 115,
    and it reaches in to r 106.9.
  - **Boss:**
    - On the inside of the base wall, from r 115 in to r 105, 12 mm wide.
    - It spans Z −12.2…−1.8, which leaves ≥ 2 mm of plastic round the
      insert and keeps everything below the seat.
- **Loads (review: define the fault load, check the whole path):**
  - **Static:** the cover with C weighs about 1 kg (10 N).
  - **Fault load at a stop:** about 8 N expected, so design for **20 N**
    per stop and check strength at **100 N**. The 8 N is the sum of:
    - the disc shifted by the bore clearance, about 2 N of imbalance at
      3000 rpm;
    - the disc tilted 0.6 mm across, about 0.27 N·m of moment, which is
      about 3.5 N at r 75;
    - its weight, 2 N.
  - **Load path:** stop → boss → ridge → plate and wall → screw tabs →
    screws (in shear) → inserts → base. Treat each ridge as a T-section:
    3 × 11.4 ridge under the 3 mm plate, I ≈ 1700 mm⁴. To be safe, treat
    it as a cantilever from the wall to r 75, ignoring the central ring:
    - deflection at 20 N ≈ 0.11 mm, well inside the 0.27 mm margin at C;
    - stress at 100 N ≈ 25 MPa, below printed PETG's strength (about
      40 MPa). The ridges print as vertical walls, so this stress runs
      along the extrusion lines.
  - **Screws:** 100 N upward shared by six is about 17 N each, in shear.
    That is negligible for M4 and for a 4 mm tab.
  - **Twist:** friction at a stop (0.3 × 100 N at r 75) gives 2.3 N·m.
    That is about 3 N per screw at r 117, also negligible.
- The screws pull the cover down the same way every time, and C's gap is
  set with the cover screwed down.
- **Opening the drum:** six screws. The cover lifts off with C, and the
  disc and B are then as open as they are today.

### What the drum guards against

The user's priorities: fingers must not reach the disc, and the disc must
not come loose and fly out.

- **Fingers:** none of the remaining openings lets a finger reach the
  disc:
  - the USB tunnel, which leads only to the USB port;
  - the 12 V slot, at most 6 mm wide, in the flat at Z < −5;
  - holes into the electronics bay, Ø5 or 4 mm wide at most;
  - the vent holes in the top plate, Ø4 at most;
  - the drive-screw bores, closed off by the screw heads;
  - C's threaded hole, which the sensor fills.
- **The disc coming off its spindle,** if the clamp ring works loose:
  - The four stops keep it on its hub, with a rim rise of 1 mm at most.
  - They meet it before either sensor does (see "Loose-disc stops").
  - The wall (12 mm away) and the plate surround it in any case.
- **Loose magnets:** they are printed in and tight (user), so they only
  come free if the disc fails.
- **Not claimed: containing a disc that breaks up.**
  - The disc stores about 45 J at 3000 rpm (20 % infill; about 90 J if
    solid).
  - Its stress at that speed is under 1 MPa against tens of MPa for PETG,
    so a break-up needs a defect or a crash.
  - The drum is a barrier in the way, but its strength against fragments
    is not verified.
  - A slow drop-weight test can't verify it either: a 2 m drop hits at
    6.3 m/s, against about 30 m/s at the rim, and plastics break
    differently at different speeds (review). So no impact test is
    planned.

### Thread test coupon

A small plate with two 10 mm long internal threads, made exactly like the
boss:
- **M16×1.5**, the user's measurement: 10 threads ≈ 15 mm;
- **5/8"-18 UNF**, which has nearly the same diameter and is common on
  magnetic pickups: 10 threads = 14.1 mm.

Print it first and try the sensor in both. Then build the boss with the
thread that fits.

## How it gets made

- **Material and printer:** PETG on the user's Bambu Lab P1S (bed
  256 × 256).
- **Parts:**
  - **Base:** Ø234 × 227 in plan, up to 47 mm tall (B's tower), one piece,
    floor down. About 0.35 kg of PETG.
  - **Cover:** Ø234 × 227 in plan (Ø238 at the screw tabs), about 66 mm
    tall (Z −12…54.4), printed top face down. The visible face then comes out smooth, and C's thread
    prints with its axis vertical. About 0.42 kg of transparent PETG.
  - The thread test coupon.
- **Deliverables:**
  - A **3MF** for Bambu Studio, with the parts and sensible process settings
    as with `disk/magnet_disc_60_P1S.3mf`.
  - **STEP** files of each part and of the assembly with the drive
    footprint, board and sensors.
  - A README in a new top-level folder `housing/`, in the same style as
    `disk/` and `hdd-driver/`.
- **Modelling (Claude's call):** a parametric Python script with build123d
  in a local virtualenv (ignored by git), generating STEP and 3MF. All the
  numbers above are parameters.
- **Fit check:**
  - First regenerate the 3D export from the current PCB with
    `hdd-driver/scripts/export-test-model`; the copy in `build/` is stale.
  - Then check for interference against the new `test-assembly.step` (board
    and modules). The base must clear every module and connector by
    ≥ 2 mm.
  - Confirm the USB-C window and J1's wire height from it.

## Claude's calls (check these)

- **Drum:**
  - Closed drum, wall r 113–117 (Ø234), flat at the connector end (inner
    face at Y −10).
  - Split at Z 0; 5 mm stepped overlap with the cover outside; one key;
    seat flat to 0.3 mm.
  - Six radial M4 screws in tabs to Z −12, axis at Z −7.
  - Top plate 3 mm at Z 51.4, which keeps 17 mm of thread for C.
  - About 8 radial ridges to Z 40, joined by a central ring at r 30–33.
  - Four adjustable nylon stops at r 75, 90° apart, set to 0.6 mm (user's
    thumb idea, extended to four). This replaces the 2 mm hub ring.
  - Fault load: 20 N per stop for deflection, 100 N for strength.
  - Vent holes (user's idea, staggered as the user suggested), sized
    and placed by Claude: Ø4.
    - Inlet: about 43 in a hexagonal pattern inside the central ring
      (r ≤ 25), as the user suggested.
    - Outside the ring, at most 25 % of any circle.
    - Outlet: about 20, alternating between r 105 and 108.5.
    - None in the wall. A temperature check
    with the drum closed decides whether to add more (≤ 15 K over room).
- **Openings:**
  - USB through a short closed tunnel with a flared entrance. The plug
    must reach about 14 mm in.
  - 12 V through a slot at most 6 mm wide.
- **Feet:** five, on a pentagon at r 104, one of them under C.
- **Material:** transparent PETG.
- **No impact test:** containing a disc that breaks up is not claimed.
- M4 heat-set inserts for the coil, the cover screws and the stops; M3
  for the feet (the user's feet take M3).
- **Carried over from the earlier design:**
  - The tray goes around the drive (0.3 mm gap) rather than inside its
    outline.
  - The tray depth assumes the deeper of the two readings of "flush".
  - B's height is adjustable over ≥ 3 mm (Z 21.5…24.5), with the
    mechanism left to the builder.
  - C's mount is sized for a 0.5 kg sensor.
  - The thread coupon carries both M16×1.5 and 5/8"-18 UNF.
  - The 3 mm screw ledge assumes 6-32 × 1/4" drive screws.
  - Poke holes for the buttons and the trimmer, and vent slots.

## Left to the builder

- Rib layout, fillets, wall details, insert pocket sizes (follow the insert
  maker's table), printed-thread clearance (start at +0.3 mm on the
  diameters and tune with the coupon).
- Floor ribs; the exact joint profile, key and screw positions; the USB
  flare; the 12 V slot shape. All of these within the clearances, opening
  limits and stiffness targets above.
- Cable hook design.

## Changes made during the build (2026-11-09/10)

- **Tray depth:** floor top Z −24.5, underside −27.5 (spec −21.0/−24.0). The
  real board reaches Z −21.93 (SimpleFOC capacitor C3); the spec's −17.6
  counted only the WeAct. Keeps at least 2 mm clearance.
- **Tray end wall:** inner face at Y −2.5 (spec: 0.3 mm gap). The board edge
  was 0.30 mm and the WeAct 1.70 mm from it.
- **Board features** measured from the KiCad export: WeAct buttons, MT3608
  trimmer screw axis, J1 wire height Z −5.4, USB receptacle mouth Z −15.87,
  J3 wire height Z −3.9.
- **Wiring (user, 2026-11-09):** J1 faces outwards, so the 12 V wires leave
  through the end-wall slot and a 6 mm slot in the drum flat (down to Z −11,
  so a Ø6 cable passes under the cover lip). J3 faces inwards, so there is no
  J3 slot in the end wall; B's cable enters through a 6 mm slot in the tray's
  right wall at Y 15 and plugs into J3 from inside, with two cable hooks on
  that wall.
- **Joint:** key at φ 240° (spec: one key; at 270° a cover turned 180° would
  not be blocked). 0.25 mm radial clearance at the lip and tabs and 0.25 mm
  per side at the tab recesses. 45° gussets under the six insert bosses so
  the base prints without supports.
- **Sensor B mount:** push-pull from below, with the inserts on a carrier
  (the head) that rides on a lower tower. Three M4 set screws hold the head
  up at (r 69, t ±10), behind the wall, and (r 88, t 0), under a 6 mm ledge
  below the coil body. One M4 pull screw at (r 74.5, t 0) holds it down from
  5.5 mm inside their triangle, so its preload presses the head onto all
  three. (A first layout put the pushes and pulls on two parallel lines;
  tightening the pulls tilted the head.) Drive clearance is 7.55 mm at the
  bar-insert bosses (spec: at least 8, for the wall).
- **Vents:** outlet radii 105/108 (spec 105/108.5), to keep 3 mm from the
  wall.
- **Loose-disc margin (fine grid):** B about 0.39 mm (spec 0.41).
