# WeAct Studio STM32G474 Core Board (STM32G474CEU6)

A small development board from WeAct Studio built around the STM32G474CEU6 MCU (Arm Cortex-M4F at 170 MHz, 512 KB flash, 128 KB SRAM, UFQFPN48 package). It has a USB-C connector, a 3.3 V LDO, 8 MHz and 32.768 kHz crystals, NRST/BOOT0/user buttons, two LEDs and a 4-pin SWD header. WeAct publishes no datasheet for the board. This file collects what can be read from WeAct's schematics, outline drawings and example code, plus the parts of ST's MCU datasheet that matter when wiring the board.

Project page: **https://github.com/WeActStudio/WeActStudio.STM32G474CoreBoard** (cloned 2026-10-18 at commit `2bb4e50`, 2026-05-20).

Source tags used below: **[S]** WeAct schematic, **[R]** WeAct outline drawing or 3D render, **[E]** WeAct example code (`Examples/` in the repo), **[DS]** ST datasheet DS12288 Rev 6 (`../stm32g4/`), **[RM]** ST reference manual RM0440 Rev 9 (`../stm32g4/`), **[AN]** ST AN2606 (bootloader), **[?]** not documented, check on the actual board.

## Which board

WeAct sells the STM32G474CEU6 on **two different PCBs**. Both are V1.0 and use the same MCU, but their pinouts, power input ranges and parts differ. Check which one you have before using a pin table.

| | **Core Board** (`WeAct-STM32G474CoreBoard_V10`) | **Long Core Board** (`..._Long_V10`, "STM32G4xx Core Board Long") |
|---|---|---|
| Photo | `product-image-ceu6-coreboard.png` | `product-image-ceu6-long.png` |
| Size | 36.28 × 28.14 mm, nearly square | 61.42 × 18.24 mm, DIP-style strip |
| Headers | 2 × (2 × 12) pins, the two double rows 25.4 mm apart | 2 × 24 pins, single rows 15.24 mm (0.6") apart |
| Supply input pin | `VCC`, **3.3 to 20 V** [S] | `5V` (net `VDD5V`), **3.3 to 5.5 V** [S] |
| LDO | ME6216A33XG, or ME6239A33M3G as alternate [S] | ME6231A33M3G [S] |
| Reverse-polarity protection | none | AP40P05 P-MOSFET on `VDD5V` [S] |
| QSPI flash | W25Q64JV, 8 MB, on the bottom side [S][R] | none |
| USB-C CC handling | 5.1 kΩ pull-downs and UCPD links, all through solder bridges [S] | 5.1 kΩ pull-downs fitted directly [S] |
| VBUS sense ADC input | PB2 through solder bridge SB4 [S] | none |
| PB8/BOOT0 on header | yes | **no** |
| PC14/PC15 on header | through solder bridges SB1/SB2 | test points TP1/TP2 only |
| LSE load capacitors | 6 pF | 12 pF |
| SWD lines | direct | 33 Ω series resistors |

Unless a row says otherwise, the rest of this file describes the **Core Board**. The Long board has its own section near the end.

The repo also documents STM32G474**CBT6** boards (LQFP48, 128 KB flash: `Hardware/QFP48/`, `Images/2.png`, `Images/3.png`) and a "Lite" schematic (`WeAct-STM32G474CoreBoard_L_V10_SchDoc.pdf`) that carries an STM32G431CBU6 with no flash. None of these are copied here. On the CBT6 board the user LED is on PA8, not PC6 [E].

## Files

| File | What it is |
|---|---|
| `weact-stm32g474-coreboard-v10_schematic.pdf` / `.png` | Core Board schematic (Altium, one A4 page, vector, 2023-11-09) and a 200 dpi render. The PDF is the ground truth for the tables below. |
| `weact-stm32g474-coreboard-v10_board-shape.pdf` / `-1.png` … `-3.png` | Core Board outline drawing. Page 1 has the dimensions, page 2 is a top render, page 3 a bottom render (shows the flash and the solder bridges). |
| `weact-stm32g474-coreboard-v10_3d.step` | Core Board 3D model (STEP). |
| `weact-stm32g474-coreboard-long-v10_schematic.pdf` / `.png` | Long board schematic (2024-07-20) and a 200 dpi render. |
| `weact-stm32g474-coreboard-long-v10_board-shape.pdf` / `-1.png` … `-3.png` | Long board outline drawing and renders. |
| `weact-stm32g474-coreboard-long-v10_3d.step` | Long board 3D model (STEP). |
| `product-image-ceu6-coreboard.png`, `product-image-ceu6-long.png` | WeAct's product renders with the silkscreen pin labels. |
| `me6239-ldo-datasheet-cn.pdf` | Microne ME6239 LDO datasheet (Chinese), the alternate regulator on the Core Board. WeAct ships it in `Doc/`. |

MCU documentation is in `../stm32g4/`: the datasheet DS12288 Rev 6, the reference manual RM0440 Rev 9, the errata sheet ES0430, the Cortex-M4 programming manual PM0214, application notes, and the SVD/IBIS/BSDL files (see `../CLAUDE.md` for the routing). Not stored here, but in the WeAct repo under `Doc/`: AN2606 (system-memory bootloader; the copy there is ST's Chinese translation) and AN5225 (USB Type-C PD with STM32 UCPD).

## MCU summary (STM32G474CEU6)

From DS12288 Rev 6 [DS]. `C` = 48 pins, `E` = 512 KB flash, `U` = UFQFPN48 (7 × 7 mm), `6` = −40 to 85 °C ambient.

| Item | Value |
|---|---|
| Core | Arm Cortex-M4 with FPU, MPU and DSP instructions, up to 170 MHz (213 DMIPS); ART accelerator for 0-wait-state execution from flash |
| Flash | 512 KB with ECC, two banks with read-while-write, 1 KB OTP |
| SRAM | 128 KB = 80 KB SRAM1 + 16 KB SRAM2 + 32 KB CCM SRAM (CCM sits on the instruction and data buses) |
| Math accelerators | CORDIC (trigonometric functions), FMAC (filter MAC) |
| GPIO | 42 in UFQFPN48 |
| ADC | 5 × 12-bit, 0.25 µs conversion (4 Msps), up to 16-bit with hardware oversampling; 21 external channels on UFQFPN48 |
| DAC | 7 channels: 3 buffered external (1 Msps), 4 unbuffered internal (15 Msps) |
| Analog | 7 comparators, 6 op-amps (PGA mode), VREFBUF (2.048 / 2.5 / 2.9 V) |
| Timers | HRTIM (6 × 16-bit counters, 184 ps resolution), 3 advanced 16-bit motor-control timers (TIM1/8/20), 2 × 32-bit (TIM2/5), 16-bit general-purpose, basic and low-power timers, 2 watchdogs, SysTick |
| Communication on the 48-pin part | 3 × SPI (2 with I2S), 4 × I2C (Fm+, 1 Mbit/s), 3 × USART, 1 × LPUART, 3 × FDCAN, USB 2.0 full-speed device, UCPD (USB Type-C / Power Delivery), SAI, QUADSPI |
| Other | RTC with 2 tamper pins, true RNG, CRC, 96-bit unique ID, 16-channel DMA, SWD/JTAG |
| Supply | VDD and VDDA 1.71 to 3.6 V; VBAT 1.55 to 3.6 V |

DS12288 `Table 2` lists 0 UARTs for the 48-pin part, but ST's pin database (and the AF table below) maps UART4_TX/RX to PC10/PC11 on this package. Check in CubeMX before relying on UART4.

## Mechanical dimensions (Core Board)

From the outline drawing, page 1 [R]. Top view: USB-C on the left, SWD header on the right.

| Measurement | Value |
|---|---|
| PCB | 36.28 × 28.14 mm |
| Pin pitch | 2.54 mm |
| Inner header rows, centre to centre | 20.32 mm (0.8") |
| Outer header rows, centre to centre | 25.40 mm (1.0"), i.e. 20.32 + 2 × 2.54 |
| Board edge (top or bottom) to the outer row's centre | 1.37 mm |
| Left board edge (USB-C end) to the first pin column | 6.97 mm |
| Right board edge to the last pin column | 1.37 mm (36.28 − 6.97 − 11 × 2.54) |
| Header arrangement | top P2 and bottom P1, each 2 × 12; SWD header P3 (1 × 4, right-angle) at the right end |

The 1.37 mm right margin is calculated from the other dimensions, not printed on the drawing. Both double rows sit on the same 2.54 mm grid, so the board plugs into a breadboard only across a gap of nine rows (20.32 mm inner spacing). The Long board is the breadboard-friendly variant.

## Header pinout (Core Board)

Schematic pin numbers [S] against the two silkscreen label lines [R]. Columns are counted from the USB-C end (left in the top view). Each column holds one odd and one even pin.

### P2: top header (3V3 / analog side)

| Column | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Upper silkscreen line = even pin, outer row at the board edge | 3V3 | GND | PB11 | VREF+ (`V+`) | PB1 | PC4 | PA6 | PA4 | PA2 | PA0 | PC15 | PC13 |
| Lower silkscreen line = odd pin, inner row | 3V3 | GND | PB10 | PB2 | PB0 | PA7 | PA5 | PA3 | PA1 | NRST | PC14 | VB |
| Pins | 1, 2 | 3, 4 | 5, 6 | 7, 8 | 9, 10 | 11, 12 | 13, 14 | 15, 16 | 17, 18 | 19, 20 | 21, 22 | 23, 24 |

### P1: bottom header (VCC / digital side)

| Column | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Upper silkscreen line = even pin, inner row | VCC | GND | PB13 | PB15 | PA8 | PA10 | PA12 | PC10 | PB3 | PB5 | PB7 | PB9 |
| Lower silkscreen line = odd pin, outer row at the board edge | VCC | GND | PB12 | PB14 | PC6 | PA9 | PA11 | PA15 | PC11 | PB4 | PB6 | PB8 (BOOT0) |
| Pins | 1, 2 | 3, 4 | 5, 6 | 7, 8 | 9, 10 | 11, 12 | 13, 14 | 15, 16 | 17, 18 | 19, 20 | 21, 22 | 23, 24 |

Which label line belongs to which physical row is inferred from the label order on the render (labels sit between the MCU and the headers, in row order). The pin-to-label pairing per column is exact. Confirm the row with a meter before soldering to a single row.

### P3: SWD header (right end, right-angle pins)

Top to bottom in the top view: `GND`, `CLK` (PA14, SWCLK), `DIO` (PA13, SWDIO), `3V3` [R]. Schematic numbering: 1 = 3.3 V, 2 = SWDIO, 3 = SWCLK, 4 = GND [S]. There is no NRST and no SWO pin on this header. NRST is on P2-19, and SWO (PB3) is on P1-18.

The bottom silkscreen also prints `BOOT0 -> B8` and `NRST -> G10` [R].

## On-board circuits (Core Board) [S]

### Power

- **`VCC` (P1-1/2)** is the LDO input. The schematic says "VCC IN: 3.3V - 20V". USB VBUS feeds `VCC` through a B5819W Schottky diode (D4), so an external supply on `VCC` does not back-feed the USB host. Solder bridge **SB10** shorts D4 (open or closed by default: [?]).
- **LDO U2**: ME6216A33XG, with ME6239A33M3G as the alternate part. Input capacitors 4.7 µF/25 V (0603) and 1 µF/25 V; output 10 µF. The ME6239 datasheet in this directory gives 30 V maximum input and 250 mA maximum output. No ME6216 datasheet is in the repo, so its limits are [?]. The schematic does not say which part is fitted on a given board. Plan on about **250 mA** total from the 3.3 V rail, minus what the board itself draws.
- Powering from `VCC` = 3.3 V gives a 3.3 V rail one LDO dropout lower. To run from an external 3.3 V supply, feed the `3V3` pins directly instead.
- **`3V3` (P2-1/2, SWD pin 4)** is the LDO output and supplies VDD (pins 23/35/48) with 3 × 100 nF decoupling.
- **VDDA** = 3V3 through ferrite bead FB1 (1 kΩ at 100 MHz), with 10 nF + 1 µF. **VREF+** = VDDA through **R6 = 0 Ω**, with 100 nF. The `V+` header pin (P2-8) is therefore the filtered analog 3.3 V, not an input. To use an external ADC reference or the internal VREFBUF output, remove R6.
- **VBAT** comes from 3V3 and from the **`VB`** header pin (P2-23) through a BAT54C dual diode, with 100 nF. Put a backup cell on `VB` to keep the RTC and backup registers alive while 3V3 is off.
- **Power LED** D2 (red) on 3V3 through 5.1 kΩ.

### Clocks

| Clock | Part | Load capacitors | Pins |
|---|---|---|---|
| HSE | 8 MHz crystal, 3225 package, ±10 ppm, 10 pF load (X2) | C5, C6 = 10 pF | PF0-OSC_IN, PF1-OSC_OUT (not on a header) |
| LSE | NX3215SA 32.768 kHz (X1) | C3, C4 = 6 pF | PC14-OSC32_IN, PC15-OSC32_OUT |

PC14/PC15 reach the header pins `C14`/`C15` only through solder bridges SB1/SB2 (pads on the bottom side). With the crystal fitted, leave them open.

WeAct's examples run the PLL from HSE: 8 MHz / M=2 × N=85 / R=2 = **170 MHz** SYSCLK, with AHB, APB1 and APB2 all at 170 MHz. USB takes 48 MHz from **HSI48 + CRS**, and the RTC is clocked from LSE [E].

### Buttons and LEDs

| Part | Net | Behaviour |
|---|---|---|
| NRST button (SW1) | PG10-NRST | Pulls NRST to GND. 100 nF to GND. R3 (10 kΩ pull-up) is marked **NC** (not fitted), so the internal 25 to 55 kΩ pull-up does the work [DS]. |
| BOOT0 button (SW3) | PB8-BOOT0 | Pulls PB8 to 3V3. R2 = 10 kΩ pull-down. |
| KEY button (SW2) | PC13 | Connects PC13 to 3V3 through R4 = 330 Ω. **Active high.** The WeAct BSP sets the internal pull-down [E]. |
| Blue LED D1 | PC6 | PC6 → 5.1 kΩ → LED → GND. **Active high** [S][E]. |
| Red LED D2 | 3V3 | Power indicator. |

PC13 can only sink about 3 mA and is limited to 2 MHz and 30 pF, and it must not source current (for example to drive an LED) [DS `Table 12` note 2]. Here it is used only as the button input.

### QSPI flash (U3)

Winbond **W25Q64JV** (SOIC-8 208 mil, the schematic part is `W25QxxJVSSIQ`), 64 Mbit = **8 MB**, on the **bottom side**. It is on QUADSPI1 bank 1 [S][E]:

| Flash pin | MCU pin | Signal (AF10) |
|---|---|---|
| /CS (1) | PB11 | QUADSPI1_BK1_NCS (100 kΩ pull-up R11) |
| DO/IO1 (2) | PB0 | QUADSPI1_BK1_IO1 |
| /WP/IO2 (3) | PA7 | QUADSPI1_BK1_IO2 |
| DI/IO0 (5) | PB1 | QUADSPI1_BK1_IO0 |
| CLK (6) | PB10 | QUADSPI1_CLK |
| /HOLD/IO3 (7) | PA6 | QUADSPI1_BK1_IO3 |

These six pins are also on header P2. With the flash fitted, they are not free for other uses. In particular, the SPI1 default pins PA6/PA7 and USART3 on PB10/PB11 collide with it. The renders show the flash fitted. Whether every board ships with it is [?]. WeAct's `05-QSPI_Flash` example drives it at a 136 MHz QSPI kernel clock [E].

### USB-C and solder bridges

J1 is a 16-pin USB-C receptacle. D+ goes to PA12 and D− to PA11 (USB FS device; no external pull-up is needed). Everything else is optional and set by 0603 solder-bridge footprints (`SBx`), drawn as jumpers in the schematic:

| Bridge | Connects | Purpose |
|---|---|---|
| SB8, SB9 | CC1, CC2 → R10, R9 = 5.1 kΩ → GND | Fixed Rd pull-downs: without them a USB-C-to-C cable/charger supplies no VBUS. Top side, next to the USB-C connector |
| SB6, SB7 | CC1 → PB6, CC2 → PB4 | Route the CC lines to the MCU's UCPD1_CC1/CC2 pins (USB-PD with the internal UCPD) |
| SB3, SB5 | PA9 ↔ PB6, PA10 ↔ PB4 | Dead-battery wiring: UCPD1_DBCC1/2 (PA9/PA10) tied to CC1/CC2 so that the MCU's own 5.1 kΩ Rd is switched in while it is unpowered [DS `Table 12` note 6] |
| SB4 | PB2 ← VBUS × 10 / 110 (R7 100 kΩ, R8 10 kΩ, C16 10 nF) | VBUS voltage sense on ADC2_IN12. WeAct's `03-ADC_Test` reads PB2 as ADC2_IN12 [E] |
| SB10 | shorts D4 | Removes the Schottky drop between VBUS and `VCC` (and the back-feed protection) |
| SB1, SB2 | PC14 ↔ header `C14`, PC15 ↔ header `C15` | Brings the LSE pins out to the header |

**The owner's board (2026-10-18) has every bridge open**, SB1 to SB10. On it, a USB-C source with a C-to-C cable supplies no VBUS (no Rd on CC1/CC2): use a USB-A-to-C cable. With SB10 open, `VCC` is VBUS minus the B5819W drop. **The factory default for other boards is [?].** The renders draw every SB as the same 0603 body, so they don't show which ones are closed. Measure before relying on one. With SB8/SB9 fitted, CC1/CC2 read about 5.1 kΩ to GND with the board unpowered. If SB3/SB6 (or SB5/SB7) are closed, PA9/PA10/PB4/PB6 are tied to the USB-C CC lines and are no longer free GPIOs; that would also cost USART1 on PA9/PA10. Unless you need USB-PD, leave SB3/SB5/SB6/SB7 open.

Related MCU behaviour [DS `Table 12` note 6]: a high level on PA9 (or PA10) turns on the internal 5.1 kΩ pull-down on PB6 (or PB4) after reset, until firmware sets `UCPD1_DBDIS` in `PWR_CR3`. Using PA9 as a UART TX that idles high can therefore load PB6 with 5.1 kΩ to GND until that bit is set.

## Pins with an on-board function, and which pins are free (Core Board)

| Pin | On-board function | Free on the header? |
|---|---|---|
| PA11, PA12 | USB D−/D+ | only when USB is not used |
| PA13, PA14 | SWD | only after giving up debugging (pulled up / down at reset) |
| PB8 | BOOT0, 10 kΩ pull-down + button | usable after boot, but it must be low at reset (see Programming) |
| PC6 | blue LED (5.1 kΩ load) | yes; the LED lights when the pin is high |
| PC13 | KEY button | input only in practice (power-switch domain) |
| PC14, PC15 | 32.768 kHz crystal | no (header via SB1/SB2 only) |
| PA6, PA7, PB0, PB1, PB10, PB11 | QSPI flash | no if the flash is fitted |
| PB2 | VBUS sense if SB4 is closed | yes if SB4 is open |
| PA9, PA10, PB4, PB6 | UCPD/CC if SB3/SB5/SB6/SB7 are closed | yes if they are open |
| PB3 | JTDO/SWO after reset | yes (reconfigure it) |
| PA15, PB4 | JTDI, NJTRST after reset, internal pull-up | yes (reconfigure them) |
| PF0, PF1, PG10 | HSE crystal, NRST | no |

All other header pins (PA0–PA5, PA8, PA15, PB3, PB5, PB7, PB9, PB12–PB15, PC4, PC10, PC11) have no on-board load.

### Voltage tolerance: not every pin is 5 V tolerant

- **TT_xx pins (3.6 V tolerant only): PA0, PA1, PA3–PA7, PB0–PB2, PB10–PB15.** They take at most VDD + 0.3 V in operation and 4.0 V absolute maximum [DS `Table 14`, `Table 17`]. Never drive these from 5 V logic.
- **FT_xx pins (5 V tolerant):** all the other port pins, including PA2, PA8–PA15, PB3–PB9, PC4, PC6, PC10, PC11 and PC13–PC15. The limit is min(VDD, VDDA) + 3.6 V, capped at 5.5 V. Above VDD + 0.3 V the internal pull-up/pull-down must be disabled. A pin configured as an analog input is not 5 V tolerant.
- FT_c (PB4, PB6): 5.0 V maximum in operation [DS `Table 17`].

### Default SPI / UART / I2C / CAN pin choices that avoid the board's own loads

All signals come from the AF table below. "Free" assumes the flash is fitted and SB3–SB7 are open.

| Peripheral | Pins (AF) | Notes |
|---|---|---|
| SPI2 | SCK PB13, MISO PB14, MOSI PB15, NSS PB12 (all AF5) | Free. All four are TT (3.3 V logic only). Also the SPI2 bootloader pins [AN]. |
| SPI1 (alternate) | SCK PB3, MISO PB4, MOSI PB5 (AF5); NSS PA4 or PA15 (AF5) | Free if SWO and JTAG are not needed. The default PA5/PA6/PA7 collide with the flash. |
| SPI3 | SCK PC10, MISO PC11, MOSI PB5 (AF6); NSS PA4 or PA15 (AF6) | Free. 5 V-tolerant pins. |
| USART1 | TX PA9, RX PA10 (AF7) | Free (see the UCPD note above). Bootloader UART. Alternates: TX PB6 / RX PB7, TX PC4. |
| USART2 | TX PA2, RX PA3 (AF7) | Free. Bootloader UART. Alternates: TX PB3 / RX PB4, TX PA14 / RX PA15. |
| USART3 | TX PC10, RX PC11 (AF7) | Free. Bootloader UART. PB10/PB11 is the flash. |
| LPUART1 | TX PA2, RX PA3 (AF12) | Shares pins with USART2. |
| I2C1 | SCL PA15 (AF4), SDA PB7 (AF4) | Free. The other choice, PB8/PB9, puts SCL on BOOT0. |
| I2C2 | SCL PC4, SDA PA8 (AF4) | Free. Bootloader I2C [AN]. |
| I2C3 | SCL PA8 (AF2), SDA PB5 or PC11 (AF8) | Free. |
| FDCAN1 | RX PB8, TX PB9 (AF9) | PB8 is BOOT0: the transceiver's RXD must not hold it high during reset. PA11/PA12 is USB. |
| FDCAN2 | RX PB12, TX PB13 (AF9); or RX PB5, TX PB6 (AF9) | Free. |
| FDCAN3 | RX PA8, TX PA15 (AF11); or RX PB3, TX PB4 (AF11) | Free. |
| Timer capture / PWM, 32-bit | TIM2 CH1–CH4 on PA0, PA1, PA2, PA3 (AF1); TIM5 CH1–CH4 on the same pins (AF2) | Useful for timestamping external sync pulses. |

SPI clock limits: up to 75 MHz in master mode at 2.7 to 3.6 V [DS `Table 89`]. The SPI kernel clock is PCLK (170 MHz in WeAct's clock setup), so the SCK choices are 85, 42.5, 21.25, 10.6, 5.3, ... MHz. Divide-by-2 (85 MHz) is over the limit, so 42.5 MHz is the fastest usable SCK unless PCLK is lowered.

## Programming and boot

- **SWD** on header P3 with an ST-LINK or any CMSIS-DAP probe. PA13/PA14 are not on the main headers. Connect NRST (P2-19) too if you need connect-under-reset.
- **USB DFU** (ST system bootloader). Hold BOOT0, then plug in USB or press and release NRST; release BOOT0 about 0.5 s later. The device enumerates as "STM32 BOOTLOADER" (DFU), and STM32CubeProgrammer or `dfu-util` can flash it. WeAct's Windows tool is in `Tools/` of the repo. The bootloader uses HSI48 + CRS for USB, so the 8 MHz crystal is not needed [AN].
- **System-bootloader interfaces** on this package [AN `Table 101`]: USART1 (PA9 TX / PA10 RX), USART2 (PA2 / PA3), USART3 (PC10 / PC11), all 8E1; I2C2 (SCL PC4 / SDA PA8, 7-bit address 0x53); SPI1 (PA4 NSS, PA5 SCK, PA6 MISO, PA7 MOSI; this collides with the flash on the Core Board); SPI2 (PB12 NSS, PB13 SCK, PB14 MISO, PB15 MOSI); USB DFU (PA11/PA12). The I2C3/I2C4 bootloader pins (PC8/PC9, PC6/PC7) are not all bonded on the 48-pin package.
- **BOOT0 is PB8.** BOOT0 is read from the PB8 pin only while the option bit `nSWBOOT0` = 1; with `nSWBOOT0` = 0 the `nBOOT0` option bit decides. The ST production value of `FLASH_OPTR` is 0xFFEF F8AA, which has `nSWBOOT0` = 1, so new chips read the pin [RM] (`FLASH_OPTR`, Rev 7 and Rev 9 agree). Clearing `nSWBOOT0` frees PB8 completely and makes the board ignore the BOOT0 button. Anything connected to PB8 must not pull it high during reset.
- **NRST is PG10.** In the production setting (`NRST_MODE` = 11) it is a bidirectional reset pin. Setting `NRST_MODE` = 10 makes it the GPIO PG10, but then the NRST button and SWD connect-under-reset stop working.

## Silicon errata that touch this board

From ES0430 Rev 9 (June 2024, `../stm32g4/es0430-...-device-errata-stmicroelectronics.pdf`), which covers the STM32G474CE. The silicon revision is the marking letter Z, Y or X; `DBGMCU_IDCODE.REV_ID` reads 0x2001, 0x2002 or 0x2003. All of these apply to every revision unless noted.

| Erratum | Why it matters here | Workaround |
|---|---|---|
| 2.2.9 LSE crystal disturbed by transitions on PC13 (LQFP and UFQFPN packages; not fixed) | The KEY button is on PC13, next to the 32.768 kHz crystal. Pressing the button, or using PC13 as RTC_OUT1, can pull the LSE frequency off and with it the RTC. | None from ST other than "avoid toggling PC13 while LSE is used". If RTC accuracy matters, don't use the KEY button while the RTC runs, or clock the RTC from something else. |
| 2.6.1 to 2.6.4 QUADSPI | The 8 MB flash is on QUADSPI1. | Indirect read with only a data phase hangs: add at least two dummy cycles. Never write 0 to `QUADSPI_CCR`. Apply ST's reset-time code sequence from 2.6.3 (internal timing) on every reset and every exit from memory-mapped mode. A memory-mapped read of the last byte of the `FSIZE` region returns 0x00 and stalls the bus on a retry. |
| 2.8.1 VREF+ disturbed by GPIO toggling | Only when VREFBUF drives VREF+ (R6 removed): toggling PB10, PB11, PB13 or PB14 disturbs the reference. Those pins are the flash CLK and /CS and SPI2 SCK and MISO. | Keep these pins static while using VREFBUF, or keep the default VREF+ = VDDA. |
| 2.18.1 SPI BSY may stay high when SPI is disabled | Affects SPI drivers that wait for BSY = 0 before disabling the peripheral. | Master transmit: disable only when TXE = 1 and BSY = 0. Master receive-only: ignore BSY. |
| 2.7.x ADC (11 items) | Concurrent conversions on ADC1/2 and ADC3/4/5 with a synchronous clock can disturb each other (2.7.11). Several injected-context and dual-mode issues. | Read the section before using injected or dual modes. Using the asynchronous ADC clock avoids 2.7.11 between ADC1 and ADC2. |

ES0430 also lists the Cortex-M4 core errata (2.1.x), I2C, USART, FDCAN, USB and UCPD items. `Table 3. Summary of device limitations` on pages 2 to 4 is the index.

## Selected MCU electrical limits [DS]

| Parameter | Value | Source |
|---|---|---|
| VDD, VDDA operating | 1.71 to 3.6 V (VDDA ≥ 1.62 V for ADC/COMP, ≥ 2.0 V for OPAMP, ≥ 2.4 V with VREFBUF) | `Table 17` |
| VDD absolute maximum | 4.0 V | `Table 14` |
| Input voltage, TT pins | −0.3 to VDD + 0.3 V operating; 4.0 V absolute maximum | `Table 14`, `Table 17` |
| Input voltage, FT pins | up to min(min(VDD, VDDA) + 3.6 V, 5.5 V) | `Table 17` |
| VIL / VIH (all except FT_c) | ≤ 0.3 × VDD / ≥ 0.7 × VDD | `Table 54` |
| Output drive | ±8 mA at VOL/VOH within 0.4 V of the rail; 20 mA with a 1.3 V drop; 20 mA maximum per pin, 100 mA total per direction | `Table 55`, `Table 15` |
| Weak pull-up / pull-down | 25 / 40 / 55 kΩ min / typ / max | `Table 54` |
| HSE crystal range | 4 to 48 MHz (8 MHz fitted) | `Table 41` |
| SPI SCK, master | 75 MHz (2.7 to 3.6 V), 50 MHz (1.71 to 3.6 V) | `Table 89` |
| Ambient temperature (suffix 6) | −40 to 85 °C at maximum power dissipation | `Table 17` |

## Full pin table (STM32G474CEU6, UFQFPN48)

Generated from ST's machine-readable pin database (`STM32_open_pin_data`: `mcu/STM32G474C(B-C-E)Ux.xml` and `mcu/IP/GPIO-STM32G47x_gpio_v1_0_Modes.xml`, fetched 2026-10-18), which is what CubeMX uses. The I/O structure column comes from DS12288 `Table 12`. EVENTOUT (AF15 on every port pin) and the ADC/DAC EXTI trigger inputs are left out. "Header" uses the Core Board numbering (P1-n / P2-n). The authoritative AF table is DS12288 `Table 13`, `4.11 Alternate functions`.

| MCU pin | Name | I/O | Core Board header | On-board use | Alternate functions (AFn) | Additional (analog, wake-up, ...) |
|---|---|---|---|---|---|---|
| 1 | VBAT | S | P2-23 (VB) | fed from 3V3 and from header pin VB through BAT54C diodes |  |  |
| 2 | PC13 | FT | P2-24 | KEY button (to 3V3 via 330 Ω, active high) | AF2 TIM1_BKIN, AF4 TIM1_CH1N, AF6 TIM8_CH4N | RTC_OUT1, RTC_TAMP1, RTC_TS, SYS_WKUP2 |
| 3 | PC14-OSC32_IN | FT | P2-21 | LSE 32.768 kHz crystal; header only via SB1 |  | RCC_OSC32_IN |
| 4 | PC15-OSC32_OUT | FT | P2-22 | LSE 32.768 kHz crystal; header only via SB2 |  | RCC_OSC32_OUT |
| 5 | PF0-OSC_IN | FT_fa | — | HSE 8 MHz crystal (not on header) | AF4 I2C2_SDA, AF5 I2S2_WS, AF5 SPI2_NSS, AF6 TIM1_CH3N | ADC1_IN10, RCC_OSC_IN |
| 6 | PF1-OSC_OUT | FT_a | — | HSE 8 MHz crystal (not on header) | AF5 I2S2_CK, AF5 SPI2_SCK | ADC2_IN10, COMP3_INM, RCC_OSC_OUT |
| 7 | PG10-NRST | NRST (FT as PG10) | P2-19 | NRST button + 100 nF | AF0 RCC_MCO |  |
| 8 | PA0 | TT_a | P2-20 |  | AF1 TIM2_CH1, AF2 TIM5_CH1, AF7 USART2_CTS, AF7 USART2_NSS, AF8 COMP1_OUT, AF9 TIM8_BKIN, AF10 TIM8_ETR, AF14 TIM2_ETR | ADC1_IN1, ADC2_IN1, COMP1_INM, COMP3_INP, RTC_TAMP2, SYS_WKUP1 |
| 9 | PA1 | TT_a | P2-17 |  | AF0 RTC_REFIN, AF1 TIM2_CH2, AF2 TIM5_CH2, AF7 USART2_DE, AF7 USART2_RTS, AF9 TIM15_CH1N | ADC1_IN2, ADC2_IN2, COMP1_INP, OPAMP1_VINP, OPAMP3_VINP, OPAMP6_VINM, OPAMP6_VINM0 |
| 10 | PA2 | FT_a | P2-18 |  | AF1 TIM2_CH3, AF2 TIM5_CH3, AF7 USART2_TX, AF8 COMP2_OUT, AF9 TIM15_CH1, AF10 QUADSPI1_BK1_NCS, AF12 LPUART1_TX, AF14 UCPD1_FRSTX1, AF14 UCPD1_FRSTX2 | ADC1_IN3, COMP2_INM, OPAMP1_VOUT, RCC_LSCO, SYS_WKUP4 |
| 11 | PA3 | TT_a | P2-15 |  | AF1 TIM2_CH4, AF2 TIM5_CH4, AF3 SAI1_CK1, AF7 USART2_RX, AF9 TIM15_CH2, AF10 QUADSPI1_CLK, AF12 LPUART1_RX, AF13 SAI1_MCLK_A | ADC1_IN4, COMP2_INP, OPAMP1_VINM, OPAMP1_VINM0, OPAMP1_VINP, OPAMP5_VINM, OPAMP5_VINM1 |
| 12 | PA4 | TT_a | P2-16 |  | AF2 TIM3_CH2, AF5 SPI1_NSS, AF6 I2S3_WS, AF6 SPI3_NSS, AF7 USART2_CK, AF13 SAI1_FS_B | ADC2_IN17, COMP1_INM, DAC1_OUT1 |
| 13 | PA5 | TT_a | P2-13 |  | AF1 TIM2_CH1, AF2 TIM2_ETR, AF5 SPI1_SCK, AF14 UCPD1_FRSTX1, AF14 UCPD1_FRSTX2 | ADC2_IN13, COMP2_INM, DAC1_OUT2, OPAMP2_VINM, OPAMP2_VINM0 |
| 14 | PA6 | TT_a | P2-14 | QSPI flash IO3 | AF1 TIM16_CH1, AF2 TIM3_CH1, AF4 TIM8_BKIN, AF5 SPI1_MISO, AF6 TIM1_BKIN, AF8 COMP1_OUT, AF10 QUADSPI1_BK1_IO3, AF12 LPUART1_CTS | ADC2_IN3, DAC2_OUT1, OPAMP2_VOUT |
| 15 | PA7 | TT_a | P2-11 | QSPI flash IO2 | AF1 TIM17_CH1, AF2 TIM3_CH2, AF4 TIM8_CH1N, AF5 SPI1_MOSI, AF6 TIM1_CH1N, AF8 COMP2_OUT, AF10 QUADSPI1_BK1_IO2, AF14 UCPD1_FRSTX1, AF14 UCPD1_FRSTX2 | ADC2_IN4, COMP2_INP, OPAMP1_VINP, OPAMP2_VINP |
| 16 | PC4 | FT_fa | P2-12 |  | AF2 TIM1_ETR, AF4 I2C2_SCL, AF7 USART1_TX, AF10 QUADSPI1_BK2_IO3 | ADC2_IN5 |
| 17 | PB0 | TT_a | P2-9 | QSPI flash IO1 | AF2 TIM3_CH3, AF4 TIM8_CH2N, AF6 TIM1_CH2N, AF10 QUADSPI1_BK1_IO1, AF13 HRTIM1_FLT5, AF14 UCPD1_FRSTX1, AF14 UCPD1_FRSTX2 | ADC1_IN15, ADC3_IN12, COMP4_INP, OPAMP2_VINP, OPAMP3_VINP |
| 18 | PB1 | TT_a | P2-10 | QSPI flash IO0 | AF2 TIM3_CH4, AF4 TIM8_CH3N, AF6 TIM1_CH3N, AF8 COMP4_OUT, AF10 QUADSPI1_BK1_IO0, AF12 LPUART1_DE, AF12 LPUART1_RTS, AF13 HRTIM1_SCOUT | ADC1_IN12, ADC3_IN1, COMP1_INP, OPAMP3_VOUT, OPAMP6_VINM, OPAMP6_VINM1 |
| 19 | PB2 | TT_a | P2-7 | VBUS/11 sense via SB4 (R7 100 kΩ / R8 10 kΩ) | AF0 RTC_OUT2, AF1 LPTIM1_OUT, AF2 TIM5_CH1, AF3 TIM20_CH1, AF4 I2C3_SMBA, AF10 QUADSPI1_BK2_IO1, AF13 HRTIM1_SCIN | ADC2_IN12, COMP4_INM, OPAMP3_VINM, OPAMP3_VINM0 |
| 20 | VREF+ | S | P2-8 | VDDA via R6 0 Ω |  | VREFBUF_OUT |
| 21 | VDDA | S | — | 3V3 via ferrite bead FB1 |  |  |
| 22 | PB10 | TT_a | P2-5 | QSPI flash CLK | AF1 TIM2_CH3, AF7 USART3_TX, AF8 LPUART1_RX, AF10 QUADSPI1_CLK, AF12 TIM1_BKIN, AF13 HRTIM1_FLT3, AF14 SAI1_SCK_A | COMP5_INM, OPAMP3_VINM, OPAMP3_VINM1, OPAMP4_VINM, OPAMP4_VINM0 |
| 23 | VDD | S | — |  |  |  |
| 24 | PB11 | TT_a | P2-6 | QSPI flash /CS (100 kΩ pull-up) | AF1 TIM2_CH4, AF7 USART3_RX, AF8 LPUART1_TX, AF10 QUADSPI1_BK1_NCS, AF13 HRTIM1_FLT4 | ADC1_IN14, ADC2_IN14, COMP6_INP, OPAMP4_VINP, OPAMP6_VOUT |
| 25 | PB12 | TT_a | P1-5 |  | AF2 TIM5_ETR, AF4 I2C2_SMBA, AF5 I2S2_WS, AF5 SPI2_NSS, AF6 TIM1_BKIN, AF7 USART3_CK, AF8 LPUART1_DE, AF8 LPUART1_RTS, AF9 FDCAN2_RX, AF13 HRTIM1_CHC1 | ADC1_IN11, ADC4_IN3, COMP7_INM, OPAMP4_VOUT, OPAMP6_VINP |
| 26 | PB13 | TT_a | P1-6 |  | AF5 I2S2_CK, AF5 SPI2_SCK, AF6 TIM1_CH1N, AF7 USART3_CTS, AF7 USART3_NSS, AF8 LPUART1_CTS, AF9 FDCAN2_TX, AF13 HRTIM1_CHC2 | ADC3_IN5, COMP5_INP, OPAMP3_VINP, OPAMP4_VINP, OPAMP6_VINP |
| 27 | PB14 | TT_a | P1-7 |  | AF1 TIM15_CH1, AF5 SPI2_MISO, AF6 TIM1_CH2N, AF7 USART3_DE, AF7 USART3_RTS, AF8 COMP4_OUT, AF13 HRTIM1_CHD1 | ADC1_IN5, ADC4_IN4, COMP7_INP, OPAMP2_VINP, OPAMP5_VINP |
| 28 | PB15 | TT_a | P1-8 |  | AF0 RTC_REFIN, AF1 TIM15_CH2, AF2 TIM15_CH1N, AF3 COMP3_OUT, AF4 TIM1_CH3N, AF5 I2S2_SD, AF5 SPI2_MOSI, AF13 HRTIM1_CHD2 | ADC2_IN15, ADC4_IN5, COMP6_INM, OPAMP5_VINM, OPAMP5_VINM0 |
| 29 | PC6 | FT_f | P1-9 | blue LED D1 (5.1 kΩ, active high) | AF2 TIM3_CH1, AF3 HRTIM1_EEV10, AF4 TIM8_CH1, AF6 I2S2_MCK, AF7 COMP6_OUT, AF8 I2C4_SCL, AF13 HRTIM1_CHF1 |  |
| 30 | PA8 | FT_a | P1-10 |  | AF0 RCC_MCO, AF2 I2C3_SCL, AF4 I2C2_SDA, AF5 I2S2_MCK, AF6 TIM1_CH1, AF7 USART1_CK, AF8 COMP7_OUT, AF10 TIM4_ETR, AF11 FDCAN3_RX, AF12 SAI1_CK2, AF13 HRTIM1_CHA1, AF14 SAI1_SCK_A | ADC5_IN1, OPAMP5_VOUT |
| 31 | PA9 | FT_fda | P1-11 | UCPD DBCC1 via SB3 (to PB6) | AF2 I2C3_SMBA, AF4 I2C2_SCL, AF5 I2S3_MCK, AF6 TIM1_CH2, AF7 USART1_TX, AF8 COMP5_OUT, AF9 TIM15_BKIN, AF10 TIM2_CH3, AF13 HRTIM1_CHA2, AF14 SAI1_FS_A | ADC5_IN2, UCPD1_DBCC1 |
| 32 | PA10 | FT_fda | P1-12 | UCPD DBCC2 via SB5 (to PB4) | AF1 TIM17_BKIN, AF3 CRS_SYNC, AF4 I2C2_SMBA, AF5 SPI2_MISO, AF6 TIM1_CH3, AF7 USART1_RX, AF8 COMP6_OUT, AF10 TIM2_CH4, AF11 TIM8_BKIN, AF12 SAI1_D1, AF13 HRTIM1_CHB1, AF14 SAI1_SD_A | SYS_PVD_IN, UCPD1_DBCC2 |
| 33 | PA11 | FT_u | P1-13 | USB-C D− | AF5 I2S2_SD, AF5 SPI2_MOSI, AF6 TIM1_CH1N, AF7 USART1_CTS, AF7 USART1_NSS, AF8 COMP1_OUT, AF9 FDCAN1_RX, AF10 TIM4_CH1, AF11 TIM1_CH4, AF12 TIM1_BKIN2, AF13 HRTIM1_CHB2 | USB_DM |
| 34 | PA12 | FT_u | P1-14 | USB-C D+ | AF1 TIM16_CH1, AF5 I2S_CKIN, AF6 TIM1_CH2N, AF7 USART1_DE, AF7 USART1_RTS, AF8 COMP2_OUT, AF9 FDCAN1_TX, AF10 TIM4_CH2, AF11 TIM1_ETR, AF13 HRTIM1_FLT1 | USB_DP |
| 35 | VDD | S | — |  |  |  |
| 36 | PA13 | FT_f | — | SWD header SWDIO | AF0 SYS_JTMS-SWDIO, AF1 TIM16_CH1N, AF3 I2C4_SCL, AF4 I2C1_SCL, AF5 IR_OUT, AF7 USART3_CTS, AF7 USART3_NSS, AF10 TIM4_CH3, AF13 SAI1_SD_B |  |
| 37 | PA14 | FT_f | — | SWD header SWCLK | AF0 SYS_JTCK-SWCLK, AF1 LPTIM1_OUT, AF3 I2C4_SMBA, AF4 I2C1_SDA, AF5 TIM8_CH2, AF6 TIM1_BKIN, AF7 USART2_TX, AF13 SAI1_FS_B |  |
| 38 | PA15 | FT_f | P1-15 |  | AF0 SYS_JTDI, AF1 TIM2_CH1, AF2 TIM8_CH1, AF4 I2C1_SCL, AF5 SPI1_NSS, AF6 I2S3_WS, AF6 SPI3_NSS, AF7 USART2_RX, AF8 UART4_DE, AF8 UART4_RTS, AF9 TIM1_BKIN, AF11 FDCAN3_TX, AF13 HRTIM1_FLT2, AF14 TIM2_ETR |  |
| 39 | PC10 | FT | P1-16 |  | AF4 TIM8_CH1N, AF5 UART4_TX, AF6 I2S3_CK, AF6 SPI3_SCK, AF7 USART3_TX, AF13 HRTIM1_FLT6 |  |
| 40 | PC11 | FT_f | P1-17 |  | AF3 HRTIM1_EEV2, AF4 TIM8_CH2N, AF5 UART4_RX, AF6 SPI3_MISO, AF7 USART3_RX, AF8 I2C3_SDA |  |
| 41 | PB3 | FT | P1-18 |  | AF0 SYS_JTDO-SWO, AF1 TIM2_CH2, AF2 TIM4_ETR, AF3 CRS_SYNC, AF4 TIM8_CH1N, AF5 SPI1_SCK, AF6 I2S3_CK, AF6 SPI3_SCK, AF7 USART2_TX, AF10 TIM3_ETR, AF11 FDCAN3_RX, AF12 HRTIM1_SCOUT, AF13 HRTIM1_EEV9, AF14 SAI1_SCK_B |  |
| 42 | PB4 | FT_c | P1-19 | USB-C CC2 via SB7 | AF0 SYS_JTRST, AF1 TIM16_CH1, AF2 TIM3_CH1, AF4 TIM8_CH2N, AF5 SPI1_MISO, AF6 SPI3_MISO, AF7 USART2_RX, AF10 TIM17_BKIN, AF11 FDCAN3_TX, AF13 HRTIM1_EEV7, AF14 SAI1_MCLK_B | UCPD1_CC2 |
| 43 | PB5 | FT_f | P1-20 |  | AF1 TIM16_BKIN, AF2 TIM3_CH2, AF3 TIM8_CH3N, AF4 I2C1_SMBA, AF5 SPI1_MOSI, AF6 I2S3_SD, AF6 SPI3_MOSI, AF7 USART2_CK, AF8 I2C3_SDA, AF9 FDCAN2_RX, AF10 TIM17_CH1, AF11 LPTIM1_IN1, AF12 SAI1_SD_B, AF13 HRTIM1_EEV6 |  |
| 44 | PB6 | FT_c | P1-21 | USB-C CC1 via SB6 | AF1 TIM16_CH1N, AF2 TIM4_CH1, AF5 TIM8_CH1, AF6 TIM8_ETR, AF7 USART1_TX, AF8 COMP4_OUT, AF9 FDCAN2_TX, AF10 TIM8_BKIN2, AF11 LPTIM1_ETR, AF12 HRTIM1_SCIN, AF13 HRTIM1_EEV4, AF14 SAI1_FS_B | UCPD1_CC1 |
| 45 | PB7 | FT_f | P1-22 |  | AF1 TIM17_CH1N, AF2 TIM4_CH2, AF3 I2C4_SDA, AF4 I2C1_SDA, AF5 TIM8_BKIN, AF7 USART1_RX, AF8 COMP3_OUT, AF10 TIM3_CH4, AF11 LPTIM1_IN2, AF13 HRTIM1_EEV3, AF14 UART4_CTS |  |
| 46 | PB8-BOOT0 | FT_f | P1-23 | BOOT0 button (to 3V3) + 10 kΩ pull-down | AF1 TIM16_CH1, AF2 TIM4_CH3, AF3 SAI1_CK1, AF4 I2C1_SCL, AF7 USART3_RX, AF8 COMP1_OUT, AF9 FDCAN1_RX, AF10 TIM8_CH2, AF12 TIM1_BKIN, AF13 HRTIM1_EEV8, AF14 SAI1_MCLK_A |  |
| 47 | PB9 | FT_f | P1-24 |  | AF1 TIM17_CH1, AF2 TIM4_CH4, AF3 SAI1_D2, AF4 I2C1_SDA, AF6 IR_OUT, AF7 USART3_TX, AF8 COMP2_OUT, AF9 FDCAN1_TX, AF10 TIM8_CH3, AF12 TIM1_CH3N, AF13 HRTIM1_EEV5, AF14 SAI1_FS_A |  |
| 48 | VDD | S | — |  |  |  |

I/O structure legend [DS `Table 11`]: `FT` = 5 V tolerant, `TT` = 3.6 V tolerant, `_a` = analog switch supplied by VDDA, `_c` = USB Type-C PD capable, `_d` = dead-battery function, `_f` = Fm+ (20 mA I2C) capable, `_u` = USB. `S` = supply.

## Long Core Board (STM32G4xx Core Board Long V1.0)

Schematic `weact-stm32g474-coreboard-long-v10_schematic.pdf` (shared with the STM32G431CBU6 variant) [S]; outline drawing page 1 [R].

### Dimensions

| Measurement | Value |
|---|---|
| PCB | 61.42 × 18.24 mm |
| Header rows, centre to centre | 15.24 mm (0.6", DIP width) |
| Pin pitch / count | 2.54 mm, 2 × 24 |
| Right board edge to the SWD header column | 9.12 mm |
| Top board edge to the first SWD pin | 5.31 mm |

### Header pinout (top view, USB-C on the left, read left to right)

| Row | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Top | GND | GND | 3V3 | 3V3 | PB11 | PB10 | VREF+ (`V+`) | PB2 | PB1 | PB0 | PC4 | PA7 | PA6 | PA5 | PA4 | PA3 | PA2 | PA1 | PA0 | NRST | PC13 | VB | 3V3 | GND |
| Bottom | GND | GND | 5V | 5V | PB12 | PB13 | PB14 | PB15 | PC6 | PA8 | PA9 | PA10 | PA11 | PA12 | PA15 | PC10 | PC11 | PB3 | PB4 | PB5 | PB6 | PB7 | PB9 | GND |

In the schematic, the top row is P4 (GND, GND, 3V3, 3V3; positions 1–4) plus P2 (20 pins, numbered from the right-hand end: P2-1 = GND, 2 = 3V3, 3 = VB, 4 = PC13, …, 20 = PB11). The bottom row is P3 (GND, GND, VDD5V, VDD5V) plus P1 (P1-1 = GND, 2 = PB9, …, 20 = PB12). **PB8/BOOT0, PC14 and PC15 are not on the headers.** The SWD header P5 (right-angle, near the right end) reads `G`, `CLK`, `DIO`, `3V3` from top to bottom.

### Differences from the Core Board

- **Power:** `5V` pins = `VDD5V`, **3.3 to 5.5 V** ("VCC IN: 3.3V - 5.5V"). VBUS feeds `VDD5V` through a B5819WS Schottky (D4), and solder bridge SB1 bypasses it. An AP40P05 P-MOSFET (U3, gate to GND via 10 kΩ) protects against reverse polarity ahead of the ME6231A33M3G LDO (U2). Input 10 µF + 100 nF; output 10 µF + 2.2 µF. Do **not** connect a 12 V supply to this board.
- **No QSPI flash**, so PA6, PA7, PB0, PB1, PB10 and PB11 are free, and SPI1 can use its default pins PA4–PA7.
- **USB-C CC:** CC1/CC2 → 5.1 kΩ to GND fitted directly (test points TP3/TP4). There are no UCPD links and no VBUS-sense divider.
- **LSE** load capacitors 12 pF. PC14/PC15 go only to test points TP1/TP2.
- **BOOT0 button** pulls PB8 to 3V3 through R6 = 330 Ω (R2 = 10 kΩ pull-down).
- **SWD** lines have 33 Ω series resistors (R11, R12).
- The LEDs (blue on PC6, red power), KEY on PC13, NRST, VBAT (BAT54C from 3V3 and `VB`), the VDDA filter and VREF+ (0 Ω, here R7) match the Core Board.
