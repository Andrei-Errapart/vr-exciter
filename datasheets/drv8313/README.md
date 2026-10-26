# DRV8313 / SimpleFOC Mini v1.0 BLDC driver module

The module is a **SimpleFOC Mini v1.0**. It is a 3-PWM BLDC driver built
around TI's **DRV8313** triple half-bridge. The units on the market are
reseller builds of the open-source SimpleFOC design (MIT licence). The
silkscreen reads "SimpleFOC Mini v1.0" and "8-35V", and some batches add a
date ("2024-05-13") or "OSZNTEC". Outline, holes and header layout match the
upstream v1.0 Gerbers. Dimensions and pinout below were read from those
Gerbers and the EasyEDA PCB.

> **v1.0 vs v1.1:** in v1.1 (2024-04) the order of IN1/IN2/IN3/EN changed and
> a GND pin was added. The official docs warn about this. Everything here is
> **v1.0**, which is the board with the four mounting ears and the 2×5 header.
> v2.x uses a DRV8316 and is a different board.

Sources are tagged in the tables: **[G]** upstream Gerber/EasyEDA files,
**[S]** upstream schematic, **[TI]** DRV8313 datasheet, **[D]** SimpleFOC
docs, **[R]** reseller listing, **[?]** not confirmed.

## Files

| Path | Content |
|------|---------|
| `drv8313_slvsba5d.pdf` | TI DRV8313 datasheet, SLVSBA5D (Oct 2012, rev. Apr 2016), with `pdf2markdown --no-postprocess` output: `.md`, `.images/`, `.image-map.json` |
| `simplefocmini-v1.0/` | Upstream hardware repo at tag `v1.0`: schematic PDF (plus `.md` conversion and a 200 dpi `.png` render), Gerbers and drill file, EasyEDA and Altium sources, pick-and-place, 3D model (OBJ), LICENSE |
| `simplefocmini-v1.0-dimensions.svg` | Top-view dimension drawing with pin labels, generated from the Gerber outline and drill file |
| `simplefocmini-v1.0-dimensions.py` | Script that generates the SVG (`python3 simplefocmini-v1.0-dimensions.py <GKO> <DRL> <out.svg>`) |
| `simplefoc-docs/` | Official "Connecting SimpleFOCMini v1" page (Markdown source) and its images: pin roles, wiring to UNO, Nucleo and Bluepill |
| `reseller-images/` | Product photos of this exact build, including `size-25.8x21mm.png`, the reseller's dimension image |

## Dimensions

All coordinates are in mm, top view (component side). The origin is the
bottom-left corner of the outline's bounding box, +x points right and +y
points up, with the motor header at the bottom and the 2×5 header at top left.
This matches `simplefocmini-v1.0-dimensions.svg`.

| Item | Value | Src |
|------|-------|-----|
| Outline | **26.08 × 21.01**, including the ears. The reseller states 25.8 × 21, upstream "26x20". | [G] [R] |
| Board between the ears | 22.35 wide, with notches between the ears on the left and right sides | [G] |
| Mounting holes | 4 × **Ø2.0** plated (M2), at (1.69, 1.66), (1.69, 19.32), (24.30, 1.79), (24.30, 19.19) | [G] |
| Hole spacing | **22.61** horizontal. Vertical: 17.66 on the left, 17.40 on the right. The upstream layout is not quite symmetric. | [G] |
| 2×5 header | 2.54 pitch, Ø1.1 holes. Top row y = 19.06, bottom row y = 16.52, columns x = 5.00 … 15.16 | [G] |
| Power `−` / `+` | Ø1.1 holes at (22.40, 15.25) and (22.40, 10.30), 4.95 apart, so a 5.0/5.08 mm screw terminal fits | [G] |
| Motor M1 M2 M3 | 1×3 header, 2.54 pitch, Ø1.0 holes, y = 1.41, x = 8.55 / 11.09 / 13.63 | [G] |
| Height | Tallest SMD part: C3 100 µF electrolytic, H 7.0 in its 3D model. The upstream 3D model with female headers is about 11.5 tall overall. PCB thickness not stated. | [G] [?] |
| Weight | 25 g (reseller figure, probably including the headers and terminal) | [R] |

The reseller kit comes with **male** pin headers (1×5, 1×5 and 1×3) and a
2-pin blue screw terminal. Nothing is soldered. The upstream BOM uses female
headers instead.

## Pinout

### 2×5 logic header (H1)

The square pad is H1 pin 1 (GND), at the right end of the top row.

| Top row, left → right | EN | IN3 | IN2 | IN1 | **GND** (square) |
|---|---|---|---|---|---|
| H1 pin | 9 | 7 | 5 | 3 | 1 |
| DRV8313 | EN1/EN2/EN3 (pins 26/24/22, tied) via 10 kΩ R4 | IN3 (23) | IN2 (25) | IN1 (27) | GND |
| Role | Enable, **required** | PWM phase C, **required** | PWM phase B, **required** | PWM phase A, **required** | Common ground, **required** |

| Bottom row, left → right | nFT | nSP | nRT | GND | 3V3 |
|---|---|---|---|---|---|
| H1 pin | 10 | 8 | 6 | 4 | 2 |
| DRV8313 | nFAULT (18), open drain | nSLEEP (17) | nRESET (16) | GND | V3P3 (15) |
| Role | Fault output, active low | Sleep, active low | Reset, active low (clears a latched fault) | Ground | 3.3 V **output**, 10 mA max |
| On board | 10 kΩ pull-up to 3.3 V | 10 kΩ pull-up | 10 kΩ pull-up | | 470 nF |

Sources: [G] [S] [D]. Pin numbers are from the EasyEDA PCB nets; the roles
are from the docs.

The silkscreen prints `EN IN3 IN2 IN1 GND` as a vertical list at the board
edge. That list reads top to bottom but corresponds to the top row read
**left to right**.

### Power and motor

| Pad | Net | Notes |
|-----|-----|-------|
| `+` | VM, to DRV8313 VM (pins 4 and 11) and C3 100 µF/35 V | Lower of the two power pads |
| `−` | GND | Upper pad, next to the header corner |
| M1 | OUT1 (pin 5) | Phase A, driven by IN1 |
| M2 | OUT2 (pin 8) | Phase B, driven by IN2 |
| M3 (square) | OUT3 (pin 9) | Phase C, driven by IN3 |

A power LED (LED1, with R5 1 kΩ) is connected from VM to GND.

SimpleFOC driver constructor:
`BLDCDriver3PWM driver = BLDCDriver3PWM(IN1, IN2, IN3, EN);`

## Electrical limits

| Item | Value | Src |
|------|-------|-----|
| Supply VM | Board **8–35 V**: silkscreen and docs. The cap is rated 35 V, and that is the limit. Upstream v1.0 README: 8–24 V. Reseller: 8–30 V. | [D] [G] [R] |
| DRV8313 VM | 8–60 V recommended, 65 V abs. max. UVLO 6.3 typ / 8 V max (rising). VM ramp ≤ 2 V/µs. | [TI] |
| Output current | 2.5 A peak per half-bridge. OCP trips at 3 A min / 5 A typ, deglitch 5 µs. | [TI] |
| R DS(on) | 0.24 Ω typ at 25 °C, 0.39 Ω max at 85 °C (each FET) | [TI] |
| Logic inputs | VIL ≤ 0.6 V, VIH ≥ 2.2 V, max 5.5 V, so both 3.3 V and 5 V logic work. Internal 100 kΩ pulldowns on ENx/INx. | [TI] |
| PWM frequency | 0–250 kHz on ENx/INx. Dead time 90 ns. | [TI] |
| V3P3 output | 3.1–3.52 V, 10 mA max. Not enough to power an MCU. | [TI] [D] |
| Thermal shutdown | 150 °C min / 160 °C typ, 35 °C hysteresis | [TI] |
| Intended motors | Gimbal motors, R > 10 Ω. Absolute board limit 5 A. With low-resistance motors (R < 1 Ω), limit the supply voltage. | [D] |

## Things that are easy to get wrong

- **EN margin with 3.3 V logic.** The header EN goes through R4 (10 kΩ) into
  three ENx pins in parallel. Each has a 100 kΩ pulldown, about 33 kΩ
  combined. Driving EN with 3.3 V puts about 2.5 V on ENx, which is above
  VIH (2.2 V) but without much margin. 5 V logic gives about 3.8 V.
- **3V3 is an output.** Don't back-feed it from the MCU's 3.3 V rail.
- **v1.0 ≠ v1.1 pin order.** Wiring tables written for v1.1 or v2 are wrong
  for this board. The docs in `simplefoc-docs/` describe v1.0.
- **Low-resistance motors.** An HDD spindle motor has a few ohms per phase
  or less, far below the R > 10 Ω the board is meant for. Limit the voltage
  or the PWM duty (SimpleFOC `voltage_limit`), or the 3–5 A OCP will trip.
- **No current sensing** on v1.0. Use SimpleFOC voltage mode only.
- **The schematic `.md` contains labels only.** The PDF is pure vector
  graphics, so the conversion extracted no images, just the text labels one
  per line. Use `Schematic_simplefocmini.png`, or the pin tables above.
- **DRV8313 Markdown:** the table of contents came out as a very wide,
  garbled table, and "Pin Functions" is split across two headings. The PDF
  is the ground truth for numbers.

## Sources (fetched 2026-10-25)

| What | URL |
|------|-----|
| DRV8313 datasheet | https://www.ti.com/lit/ds/symlink/drv8313.pdf |
| Upstream hardware, tag v1.0 | https://github.com/simplefoc/SimpleFOCMini/tree/v1.0 |
| Docs: connecting Mini v1 | https://docs.simplefoc.com/mini_v1_connect_hardware (source: `simplefoc/simplefoc.github.io`, `docs/boards/simplefoc_mini/getting_started/connecting/mini_v1.md`) |
| Board overview, version comparison | https://docs.simplefoc.com/simplefocmini |
| Reseller listing and photos | https://www.elecrow.com/simple-foc-mini-v1-0-drv8313-dc-brushless-motor-driver-board-foc-control-driver-svpwm-control-dc-8-30v-module.html (images hosted on ae01.alicdn.com) |
