# 60-magnet exciter disc for a VR sensor

A 3D-printed disc that carries 60 small NdFeB magnets. It sits on the spindle
of a gutted 3.5" hard drive and excites a variable-reluctance (VR, passive
coil) pickup at **3000 pulses per second**:

    60 magnets × 3000 rpm (50 rev/s) = 3000 Hz

The magnet count is high so the motor can run slowly. At 3000 rpm the spindle
speed is easy to control and the loads on the printed part stay modest.

## Files

| Path | Content |
|------|---------|
| `magnet_disc_60_P1S.3mf` | The disc, ready to slice in Bambu Studio (P1S + AMS). This is the only model; earlier coupons and variants were dropped. |
| `hdd-photos/` | Caliper measurements of the HDD spindle and clamp ring that the hub is designed around, plus the drive's footprint. |

### `hdd-photos/`

| Photo | Shows |
|-------|-------|
| `01-hub-diameter-25.01mm.jpg` | Spindle hub outer diameter: 25.01 mm |
| `02-hub-centre-boss-diameter-10.66mm.jpg` | Centre boss on top of the hub: Ø10.66 mm |
| `03-hub-centre-boss-height-2.16mm.jpg` | Centre boss height above the hub top: 2.16 mm |
| `04-hub-height-above-platter-flange-8.52mm.jpg` | Hub top (clamp-ring plane) above the platter flange: 8.52 mm |
| `05-clamp-ring-diameter-31.97mm.jpg` | Original platter clamp ring: Ø31.97 mm |
| `06-hdd-underside-length-ruler.jpg`, `07-hdd-underside-width-ruler.jpg` | Drive underside against rulers (standard 3.5" footprint, about 147 × 102 mm) |

## Disc design

Units are mm. Heights are given in **print orientation**: the numbered face
is on the build plate at z = 0.

| Feature | Value |
|---------|-------|
| Outer diameter | 202 (r 101), chamfered top edge |
| Plate thickness | 8.0 |
| Magnet circle | r ≈ 95.5, 60 pockets, pitch ≈ 10.0 |
| Pockets | Ø5.2 × 3.2 deep, for Ø5 × 3 magnets |
| Lid over magnets (sensor side) | 0.6 |
| Index numbers | 1–59 plus a wedge at magnet 0, inlaid 0.4 deep in the face, r 86–90.6 |
| Hub tube | Ø44 outside (cone to Ø50 where it meets the plate), Ø32 foot that rests on the platter flange |
| Spindle bore | Ø25.2 (hub is Ø25.01) |
| Clamp-ring counterbore | Ø32.6, open to the face |
| Clamp-ring seat | **8.5 above the bottom of the hub tube** (measured 8.52, photo 04) |
| Total height | 20.66 |
| Tip speed at magnet circle, 3000 rpm | ≈ 30 m/s |

The disc is a single object with four parts. Each part is assigned to an AMS
filament slot:

| Part | z range | Filament slot |
|------|---------|---------------|
| `01 face lid, 0.6 mm` | 0–0.6 | 1 |
| `02 numbers 1-59 + zero wedge` | 0–0.4, inlaid in the lid | 3 |
| `03 magnet band, z 0.6-3.8` | 0.6–3.8, contains the pockets | 2 |
| `04 body` | 3.8–20.66, plate and hub | 1 |

Process overrides saved in the 3MF: 0.2 mm layers, 3 walls, 20 % gyroid,
5 top and 3 bottom shell layers. It is printed in PETG.

### Why the seat is at 8.5 mm

The original HDD clamp ring is screwed onto the top of the spindle hub with
six M2 screws and presses down on the seat inside the counterbore. The seat
has to sit **at or slightly above** the clamp-ring plane (the hub top).

- If the seat is lower than the hub top (an 8.2 mm seat, for example), the
  ring bottoms out on the hub and leaves a gap above the seat. The disc is
  then not clamped.
- At 8.5 mm the ring just touches the seat, with no preload. PETG also creeps
  a little under the screws.
- If the disc has axial play after assembly, rebuild the model with the seat
  at about 8.7 mm. The screws then compress the extra 0.2 mm and hold the
  disc down.

## Printing (Bambu Studio, P1S + AMS)

1. Open `magnet_disc_60_P1S.3mf`. Bambu Studio may report that the file comes
   from an older version and load only the geometry. If so, check the process
   settings listed above and check that the per-part filament assignments
   survived.
2. **Magnet pause.** The file has a pause before the layer at **z = 4.0**,
   right after the magnet band (top at 3.8) is finished. Its message reads
   *"Insert 60 magnets 5x3 mm, SAME pole facing down, then resume"*. In
   *Vorschau*, check that the layer slider shows the pause marker. If it is
   missing, drag the slider to the 4.0 mm layer, right-click the **+** and
   choose *Pause hinzufügen*. Bambu Studio pauses *before* the selected layer.
3. **Supports: leave them off.** Generated supports go into the magnet
   pockets and block the magnets. The pockets don't need support anyway,
   because the body's first layer bridges the short span or prints straight
   onto the magnet (pocket 3.2, magnet 3.0). If supports are ever needed for
   something else, use *Nur auf Druckplatte*, paint blockers over the
   pockets, or add a support-blocker volume over the band.
4. For a third-party spool (e.g. SUNLU PETG), set its AMS slot to
   Generic PETG or a custom preset in *Gerät*, then press *Sync Infos* in
   *Vorbereiten*. Run flow-dynamics calibration on its first use.

### Inserting the magnets

The magnets are axially magnetised Ø5 × 3 mm NdFeB discs, so their poles are
on the flat faces.

- Take the magnets one at a time from a single stack and keep their
  orientation. All 60 must have the **same pole facing down**, toward the
  lid, which is the sensor side in use.
- A magnet inserted the wrong way round gives an inverted pulse, which is
  easy to see on a scope.
- Neighbours at 10 mm pitch repel only slightly. The pockets and the layers
  printed over them hold the magnets.

## Assembly

1. Flip the disc so that the numbered face is up. Slide the hub tube over the
   spindle until its foot rests on the platter flange.
2. Put the original clamp ring into the counterbore and tighten the six M2
   screws.
3. Try to move the disc up and down by hand. Any axial play or rattle means
   the disc is too loose (see "Why the seat is at 8.5 mm" above).
4. Spin it up slowly before going to 3000 rpm. Wobble or radial runout shows
   up in the VR signal as amplitude modulation once per revolution (50 Hz).

The disc (Ø202) overhangs the HDD housing. Anything that mounts the sensor
has to come from outside the disc or be attached to the base.

## Sensor

- The sensor sits **above the face and looks down** at the magnet circle,
  r ≈ 95.5. Its tip should be 0.5–1 mm above the lid, which puts it about
  1.1–1.6 mm from the magnets.
- A sensor at the rim would see only the weak side field of the axial
  magnets. Rim sensing would need a different disc with radially magnetised
  magnets.
- The output scales with speed and with 1/gap, so tens of volts are possible.
  Use a clamped input stage: MAX9924, LM1815, or a comparator with a series
  resistor and clamp diodes.
- If the sensor has its own bias magnet, the disc magnets add to its flux.
  Check the pulse polarity and amplitude.

## Accuracy notes

- Magnet placement error turns into timing jitter. ±0.1 mm on a 10 mm pitch
  is about ±1 % of the period.
- Keep radial and axial runout small, or the gap changes once per revolution.
  Aim for balance quality G6.3 or better, which at 3000 rpm is about 20 µm of
  eccentricity.
- For an exact 3000.0 Hz, the speed loop needs a crystal-derived reference.

## Safety

The magnets pass at about 30 m/s. Put a polycarbonate cover over the rotor
before running at speed.

## Open items

- **Sensor mount.** Not designed yet. It needs a stand with an arm that
  reaches over the disc to r 95.5. Designing it requires the sensor's body
  diameter and its thread or clamp style.
- **Spindle drive.** The HDD spindle motor needs a sensorless BLDC/FOC driver
  in closed-loop speed mode at 3000 rpm. No driver has been chosen yet.
- **Clamping.** If the disc has play at 8.5 mm, build the 8.7 mm seat
  variant.
