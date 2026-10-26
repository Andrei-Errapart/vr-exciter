# datasheets/ — hardware reference index

Vendor datasheets for the hardware this repo targets. Each is kept as the
original PDF plus a Markdown conversion. Modules with no vendor datasheet
(the SimpleFOC Mini in `drv8313/`, the WeAct STM32G474 Core Board in
`weact_stm32G474/`) are documented by a hand-written `README.md` instead.
This is reference material, not code. Use this file to find the right
document and section; don't read the big files end to end.

## How to look something up

1. Pick the file from the routing table below.
2. List its sections with `grep -n '^#' datasheets/<dir>/<file>.md`, or
   search directly with `grep -n -i 'keyword' datasheets/<dir>/<file>.md`.
3. Read only that range (Read with `offset`/`limit`). Large files:
   - `stm32g4/stm32g474xe_ds12288_rev6.md`: about 6100 lines.
   - `stm32g4/pm0214-...md`: about 10,000 lines.
   - `stm32g4/es0430-...md`: about 1700 lines.
   - The RM0440 reference manual is split into one Markdown file per chapter
     under `stm32g4/rm0440-markdown/`. Open `index.md` for the chapter list.
     The biggest chapter, HRTIM, is about 4200 lines.
4. **The PDF is the ground truth.** The Markdown is a machine conversion:
   - Tables can be split across pages ("(continued)" headings).
   - Footnote letters get glued to names.
   - Units lose their sub- and superscripts (`V IN`, `I 2 C`).
   - Formulas may be garbled.

   If a number matters, confirm it in the PDF:
   `pdftotext -layout -f <page> -l <page> <file>.pdf -`.
5. Diagrams (pinouts, timing, block diagrams) exist only as images in
   `<file>.images/`. `<file>.image-map.json` maps each image to its PDF page
   and bounding box. Read the image when the text refers to a figure.

## Routing table

| Looking for | File | Sections / keywords to grep |
|---|---|---|
| SimpleFOC Mini v1.0 module (the DRV8313 board): header pinout, power and motor pads, dimensions and mounting holes, EN/nSLEEP/nRESET/nFAULT circuit, voltage and current limits, v1.0 vs v1.1 pin order | `drv8313/README.md` | whole file (hand-written): `Dimensions`, `Pinout`, `Electrical limits`, `Things that are easy to get wrong` |
| SimpleFOC Mini outline and hole positions as a drawing | `drv8313/simplefocmini-v1.0-dimensions.svg` | generated from `simplefocmini-v1.0/Gerber/` by `simplefocmini-v1.0-dimensions.py` |
| SimpleFOC Mini schematic, PCB, Gerbers, BOM, 3D model | `drv8313/simplefocmini-v1.0/` | `Schematic_simplefocmini.png` (the `.md` holds labels only), `EasyEDA/PCB_*.json` (pad nets), `Gerber/`, `3D model/OBJ_simplefocmini.obj` (units are 10 mil = 0.254 mm) |
| SimpleFOC wiring examples (UNO, Nucleo, Bluepill) and pin roles | `drv8313/simplefoc-docs/mini_v1_connect_hardware.md` | `Microcontroller`, `BLDC motor`, `Power supply`, `Examples of connection schematics` |
| DRV8313 chip: pin functions, absolute maximum and recommended ratings, electrical characteristics (V3P3, VIH/VIL, pulldowns, rDS(on), OCP, UVLO, TSD), switching times and dead time, bridge logic, nRESET/nSLEEP, BLDC application circuits, layout, thermal | `drv8313/drv8313_slvsba5d.md` (SLVSBA5D, Apr 2016) | `5 Pin Configuration and Functions`, `6.1 Absolute Maximum Ratings`, `6.3 Recommended Operating Conditions`, `6.5 Electrical Characteristics`, `6.6 Switching Characteristics`, `7.3.2 Bridge Control`, `7.3.5 Protection Circuits`, `7.4.1 nRESET and nSLEEP Operation`, `8.2.1 Three-Phase Brushless-DC Motor Control`, `10 Layout` |
| WeAct STM32G474CEU6 board: which of the two CEU6 boards (square Core Board vs Long), header pinout, power input range and LDO, USB-C CC / UCPD solder bridges, QSPI flash pins, LEDs and buttons, free pins and suggested SPI/UART/I2C/CAN pin sets, DFU/UART bootloader, dimensions | `weact_stm32G474/README.md` | whole file (hand-written): `Which board`, `Mechanical dimensions (Core Board)`, `Header pinout (Core Board)`, `On-board circuits (Core Board)`, `Pins with an on-board function`, `Voltage tolerance`, `Default SPI / UART / I2C / CAN pin choices`, `Programming and boot`, `Full pin table`, `Long Core Board` |
| WeAct STM32G474 board schematics, outlines, 3D models | `weact_stm32G474/weact-stm32g474-coreboard-v10_schematic.png`, `..._board-shape-1.png` (dimensions), `-3.png` (bottom side), `*_3d.step` | read the image; the PDFs are vector with no Markdown. The STEP has the 2x12 headers pins-up; `hdd-driver/lib/3d/WeAct_STM32G474_CoreBoard.step` is the pins-down version |
| STM32G474 MCU: pin definition and I/O structure (FT/TT 5 V tolerance), alternate-function (AF) numbers, boot modes, peripheral counts per package | `stm32g4/stm32g474xe_ds12288_rev6.md` | `Table 2. STM32G474xB/xC/xE features`, `3.7 Boot modes`, `4.1 UFQFPN48 pinout description`, `4.10 Pin definition` (`Table 11` legend, `Table 12`), `4.11 Alternate functions` (`Table 13`, see defect note) |
| STM32G474 MCU: voltage/current limits, I/O levels, clocks, ADC, DAC, timer, SPI/I2C/USART timing, current consumption, package drawing | same file | `5.2 Absolute maximum ratings`, `5.3.1 General operating conditions`, `5.3.5 Supply current characteristics`, `5.3.14 I/O port characteristics`, `5.3.19 Analog-to-digital converter characteristics`, `5.3.27 Communication interfaces characteristics`, `6.2 UFQFPN48 package information` |
| STM32G4 registers and peripheral behaviour: GPIO/AF, RCC and PLL, FLASH option bytes, timers (TIM1/TIM8/TIM20 advanced timers for 3-phase PWM, HRTIM), ADC, COMP, OPAMP, DMA, USART, SPI, USB, UCPD | `stm32g4/rm0440-markdown/<chapter>.md` (ST's own Markdown edition of RM0440 Rev 9; `index.md` lists the chapters) | The G474 is a **category 3** device: use `Embedded_flash_memory_(FLASH)_for_category_3_devices.md`. Timers: `Advanced-control_timers_(TIM1__47_TIM8__47_TIM20).md` |
| STM32G4 silicon errata (per silicon revision Z/Y/X) and workarounds | `stm32g4/es0430-stm32g471xx473xx474xx483xx484xx-device-errata-stmicroelectronics.md` (ES0430 Rev 9) | `1 Summary of device errata` (`Table 3`), then `2.x` by peripheral |
| Cortex-M4 core: instruction set (FPU, DSP/SIMD), NVIC, SCB, MPU, SysTick, fault handling | `stm32g4/pm0214-stm32-cortexm4-mcus-and-mpus-programming-manual-stmicroelectronics.md` (PM0214 Rev 10) | `2.3 Exception model`, `2.4 Fault handling`, `3.1 Instruction set summary`, `4.3 Nested vectored interrupt controller (NVIC)`, `4.6 Floating point unit (FPU)` |
| STM32G4 board-level hardware design: supplies and decoupling, reset, crystals, boot pins, SWD | `stm32g4/an5093-getting-started-with-stm32g4-series--hardware-development-boards-stmicroelectronics.md` (AN5093 Rev 2) | `2 Power supplies`, `4 Clocks`, `5 Boot configuration`, `6.4 Serial wire debug (SWD) pin assignment`, `7 Recommendations` |
| STM32 GPIO hardware: TT vs FT tolerance, pull-up sizing, 5 V interfacing, unused pins | `stm32g4/an4899-guidelines-for-gpio-hardware-settings-and-lowpower-consumption-on-stm32-mcus-stmicroelectronics.md` (AN4899 Rev 4) | `5.2 Three-volt tolerant and five-volt tolerant`, `5.3 Five-volt tolerant application examples`, `6 GPIO hardware guideline` |
| STM32G4 analog (ADC, DAC, COMP, OPAMP) versus the F3; comparator application examples (useful for VR-sensor zero-crossing detection) | `stm32g4/an5310-...md` (AN5310 Rev 1), `stm32g4/an4232-...md` (AN4232 Rev 4) | AN5310 `3 I/O configurations`, `5 ... analog peripherals`; AN4232 `2 Overview of analog comparators`, `3 Application examples` |
| EMC design for STM32 boards (layout, filtering, grounding, ESD) | `stm32g4/an1709-emc-design-guide-for-stm8-stm32-and-legacy-mcus-stmicroelectronics.md` (AN1709 Rev 5) | `5.1.1 Optimized PCB layout`, `5.1.2 Power supply filtering`, `5.1.3 Ground connections` |
| STM32G4 family overview, USB-C/PD slides, physical-attack security bulletin | `stm32g4/microcontrollers-stm32g4-series-product-overview.md`, `stm32g4/stm32-usb-c-pd-solutions-presentation.md`, `stm32g4/tn1489-...md` | slide text only; for figures read the `.images/` |
| STM32G474 SVD (debugger register definitions), IBIS models, BSDL | `stm32g4/svd/STM32G474.svd`, `stm32g4/ibis/stm32g471_473_474_483_484_ufqfpn48.ibs`, `stm32g4/bsdl/STM32G471_473_474_483_484_UFQFPN48.bsd` | other packages are in `stm32g4_{svd,ibis,bsdl}.zip` |

## Things that are easy to get wrong

- **SimpleFOC Mini v1.0 vs v1.1 pin order.** v1.1 reordered IN1/IN2/IN3/EN
  and added a GND pin. The board here is v1.0, with four mounting ears and a
  2×5 header. Its top row, left to right, is `EN IN3 IN2 IN1 GND`.
  Wiring tables for v1.1 or v2 boards don't apply to it.
- **DRV8313 needs VM ≥ 8 V.** UVLO is 6.3 V typical and 8 V maximum
  (rising), so the driver cannot run from USB 5 V directly.
- **SimpleFOC Mini EN goes through a 10 kΩ series resistor** into the three
  ENx pins, each with a 100 kΩ internal pulldown. 3.3 V logic gives about
  2.5 V at the pins, against a VIH of 2.2 V.
- **SimpleFOC Mini `3V3` is the DRV8313's 10 mA regulator output.** Don't
  feed it from an MCU rail.
- **SimpleFOC Mini supply rating is set by its 35 V electrolytic.** The chip
  itself is rated to 60 V. The upstream v1.0 README says 8–24 V; the
  silkscreen and docs say 8–35 V.
- **The SimpleFOC Mini schematic Markdown is labels only.** The PDF is
  vector, so read `Schematic_simplefocmini.png`.
- **DRV8313 Markdown defects.** The table of contents is a garbled wide
  table. Repeated `## [www.ti.com](http://www.ti.com/)` headings mark page
  breaks. Symbols lose their subscripts (`V IN`, `I V3P3`, `f PWM`).
- **Two different WeAct boards carry the STM32G474CEU6.** The square "Core
  Board" (36 × 28 mm, `VCC` input 3.3 to 20 V, 8 MB QSPI flash on
  PA6/PA7/PB0/PB1/PB10/PB11, PB8/BOOT0 on the header) and the "Long" board
  (61 × 18 mm, `5V` input 3.3 to 5.5 V only, no flash) have different
  pinouts. `hdd-driver` uses the square Core Board.
- **WeAct Core Board power.** `VCC` is the LDO input, fed from USB VBUS
  through a B5819W Schottky. VBUS itself is not on a header. Every USB-C,
  UCPD, VBUS-sense and LSE-to-header link goes through a solder bridge
  (SB1 to SB10); on the owner's board all are open.
- **STM32G474: not every pin is 5 V tolerant.** On the 48-pin package, PA0,
  PA1, PA3 to PA7, PB0 to PB2 and PB10 to PB15 are `TT` (3.6 V maximum); the
  rest are `FT`. See `Table 12` in the datasheet.
- **STM32G474 datasheet is DS12288 Rev 6 (November 2021)**, the copy WeAct
  ships, because st.com refused scripted downloads. The rest of `stm32g4/`
  was downloaded from st.com by hand and is current as of 2026-10-18.
- **DS12288 Markdown: `Table 13` (alternate functions) is misaligned.** The
  converter merged the port and AF0 columns, so each cell under the `AF1`
  header holds the AF0 entry followed by the AF1 entry. Read AF numbers from
  the PDF page.
- **`stm32g4/rm0440-markdown/` is ST's own Markdown, not a `pdf2markdown`
  conversion.** Its tables are raw HTML on very long lines, so use
  `grep -o` or strip the tags (`sed -E 's/<[^>]+>/ /g'`) before reading one.
  File names encode `/` as `__47_` and contain parentheses, so quote them.
- **RM0440 and ES0430 cover more than the G474.** RM0440 covers the whole
  G4 family, and the G474 is category 3. ES0430 covers the
  G471/473/474/483/484 and gives a status per silicon revision.

## Sources

| Files | Source |
|---|---|
| `drv8313/drv8313_slvsba5d.pdf` | https://www.ti.com/lit/ds/symlink/drv8313.pdf, fetched 2026-10-25 |
| `drv8313/simplefocmini-v1.0/` | https://github.com/simplefoc/SimpleFOCMini at tag `v1.0` (MIT), fetched 2026-10-25 |
| `drv8313/simplefoc-docs/` | `simplefoc/simplefoc.github.io`, `docs/boards/simplefoc_mini/getting_started/connecting/mini_v1.md` and `extras/Images/`, fetched 2026-10-25 |
| `drv8313/reseller-images/` | Elecrow listing "Simple FOC Mini v1.0 DRV8313" (images on ae01.alicdn.com), fetched 2026-10-25 |
| `weact_stm32G474/` | Copied from `~/demo_imu/datasheets/weact_stm32G474` on 2026-10-25. Originally from https://github.com/WeActStudio/WeActStudio.STM32G474CoreBoard (commit `2bb4e50`, fetched 2026-10-18); the README was written for demo_imu from those files |
| `stm32g4/` | Copied from `~/demo_imu/datasheets/stm32g4` on 2026-10-25. Downloaded there from st.com by hand on 2026-10-18; DS12288 Rev 6 came from https://github.com/WeActStudio/WeActStudio.STM32G474CoreBoard (`Doc/`) |

## Adding or regenerating a document

```sh
/Users/andrei/2026/info2markdown/scripts/pdf2markdown --no-postprocess [-f] datasheets/<dir>/<file>.pdf
```

This writes `<file>.md`, `<file>.images/` and `<file>.image-map.json` next
to the PDF (`-f` overwrites). A PDF that is pure vector graphics, such as a
schematic, yields no images and a label-only `.md`; add a page render next
to it with `pdftoppm -r 200 -png -singlefile <file>.pdf <file>`. Add a
routing-table row here for every new document.
