"""Generate the project symbol library lib/hdd-driver.kicad_sym.

    python3 scripts/library/gen_symbols.py

Generated once; the symbols may since have been edited in KiCad, and
rerunning this overwrites them. Pin numbers match the footprints made by
gen_footprints.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import Q, dumps  # noqa: E402

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LIB = os.path.join(PROJ, "lib/hdd-driver.kicad_sym")
FONT = ["effects", ["font", ["size", 1.27, 1.27]]]


def prop(name, value, x, y, hide=False, angle=0):
    eff = ["effects", ["font", ["size", 1.27, 1.27]]]
    if hide:
        eff.append(["hide", "yes"])
    return ["property", Q(name), Q(value), ["at", float(x), float(y), angle], eff]


def pin(etype, x, y, angle, name, number, length=2.54):
    return ["pin", etype, "line", ["at", float(x), float(y), angle], ["length", length],
            ["name", Q(name), FONT], ["number", Q(number), FONT]]


def rect(x0, y0, x1, y1):
    return ["rectangle", ["start", float(x0), float(y0)], ["end", float(x1), float(y1)],
            ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "background"]]]


def text(t, x, y):
    return ["text", Q(t), ["at", float(x), float(y), 0], FONT]


def symbol(name, ref, value_xy, ref_xy, footprint, datasheet, descr, keywords, graphics, pins, fp_filter=""):
    s = ["symbol", Q(name), ["pin_names", ["offset", 1.016]], ["exclude_from_sim", "no"],
         ["in_bom", "yes"], ["on_board", "yes"],
         prop("Reference", ref, *ref_xy),
         prop("Value", name, *value_xy),
         prop("Footprint", footprint, 0, 0, True),
         prop("Datasheet", datasheet, 0, 0, True),
         prop("Description", descr, 0, 0, True),
         prop("ki_keywords", keywords, 0, 0, True)]
    if fp_filter:
        s.append(prop("ki_fp_filters", fp_filter, 0, 0, True))
    s.append(["symbol", Q(name + "_0_1")] + graphics)
    s.append(["symbol", Q(name + "_1_1")] + pins)
    s.append(["embedded_fonts", "no"])
    return s


# --------------------------------------------------------------------------
WEACT_P1 = {1: "VCC", 2: "VCC", 3: "GND", 4: "GND", 5: "PB12", 6: "PB13", 7: "PB14", 8: "PB15",
            9: "PC6/LED", 10: "PA8", 11: "PA9", 12: "PA10", 13: "PA11/USB_DM", 14: "PA12/USB_DP",
            15: "PA15", 16: "PC10", 17: "PC11", 18: "PB3/SWO", 19: "PB4", 20: "PB5", 21: "PB6",
            22: "PB7", 23: "PB8/BOOT0", 24: "PB9"}
WEACT_P2 = {1: "3V3", 2: "3V3", 3: "GND", 4: "GND", 5: "PB10/QSPI_CLK", 6: "PB11/QSPI_NCS",
            7: "PB2", 8: "VREF+", 9: "PB0/QSPI_IO1", 10: "PB1/QSPI_IO0", 11: "PA7/QSPI_IO2",
            12: "PC4", 13: "PA5", 14: "PA6/QSPI_IO3", 15: "PA3", 16: "PA4", 17: "PA1", 18: "PA2",
            19: "NRST", 20: "PA0", 21: "PC14/OSC32_IN", 22: "PC15/OSC32_OUT", 23: "VBAT", 24: "PC13/KEY"}


def weact_type(name):
    if name == "VCC" or name == "GND":
        return "power_in"
    if name == "3V3":
        return "power_out"
    if name in ("VREF+", "VBAT"):
        return "passive"
    return "bidirectional"


def weact():
    pins = []
    for i in range(24):
        y = (11.5 - i) * 2.54
        n = i + 1
        pins.append(pin(weact_type(WEACT_P1[n]), -25.4, y, 0, WEACT_P1[n], f"P1.{n}", 5.08))
        pins.append(pin(weact_type(WEACT_P2[n]), 25.4, y, 180, WEACT_P2[n], f"P2.{n}", 5.08))
    g = [rect(-20.32, 31.75, 20.32, -31.75),
         text("P1 (VCC side)", -12.7, 33.02), text("P2 (3V3 side)", 12.7, 33.02)]
    return symbol("WeAct_STM32G474_CoreBoard", "U", (0, -33.02), (0, 35.56),
                  "hdd-driver:WeAct_STM32G474_CoreBoard_Socketed",
                  "https://github.com/WeActStudio/WeActStudio.STM32G474CoreBoard",
                  "WeAct Studio STM32G474CEU6 Core Board (square, 36x28 mm). Pin P1.n / P2.n = header P1/P2 "
                  "pin n. VCC is the LDO input (3.3-20 V); USB VBUS feeds VCC through a Schottky diode. "
                  "3V3 is the LDO output. PA6/PA7/PB0/PB1/PB10/PB11 drive the on-board QSPI flash.",
                  "STM32G474 STM32G474CEU6 WeAct core board module", g, pins)


def simplefoc():
    P = []
    left = [("input", "EN", "9"), ("input", "IN1", "3"), ("input", "IN2", "5"), ("input", "IN3", "7"),
            ("input", "nSP", "8"), ("input", "nRT", "6"), ("open_collector", "nFT", "10")]
    for i, (t, nm, num) in enumerate(left):
        P.append(pin(t, -12.7, 7.62 - 2.54 * i, 0, nm, num))
    P.append(pin("power_in", 12.7, 7.62, 180, "VM(+)", "11"))
    for i, (nm, num) in enumerate((("M1", "13"), ("M2", "14"), ("M3", "15"))):
        P.append(pin("output", 12.7, 2.54 - 2.54 * i, 180, nm, num))
    P.append(pin("power_out", 0, 12.7, 270, "3V3", "2"))
    for x, num in ((-2.54, "1"), (0, "4"), (2.54, "12")):
        P.append(pin("power_in", x, -15.24, 90, "GND", num))
    g = [rect(-10.16, 10.16, 10.16, -12.7)]
    return symbol("SimpleFOC_Mini_v1.0", "U", (0, -24.13), (0, 15.24),
                  "hdd-driver:SimpleFOC_Mini_v1.0_Socketed",
                  "https://docs.simplefoc.com/mini_v1_connect_hardware",
                  "SimpleFOC Mini v1.0 BLDC driver module (TI DRV8313, 8-35 V, 2.5 A peak). 3-PWM inputs; "
                  "EN through 10k into EN1-3; nSP/nRT/nFT pulled up to the module's 3V3 (10 mA output). "
                  "Pin numbers 1-10 = module header H1, 11 = +, 12 = -, 13-15 = M1-M3.",
                  "BLDC driver DRV8313 SimpleFOC module", g, P)


def mt3608():
    P = [pin("power_in", -10.16, 2.54, 0, "VIN+", "1"), pin("power_in", -10.16, -2.54, 0, "VIN-", "2"),
         pin("power_out", 10.16, 2.54, 180, "VOUT+", "3"), pin("passive", 10.16, -2.54, 180, "VOUT-", "4")]
    g = [rect(-7.62, 5.08, 7.62, -5.08)]
    return symbol("MT3608_Boost_Module", "U", (0, -7.62), (0, 7.62),
                  "hdd-driver:MT3608_Boost_Module",
                  "https://components101.com/modules/mt3608-2a-dc-dc-step-up-power-module",
                  "MT3608 2 A boost converter module (input 2-24 V, output up to 28 V, set by trimmer). "
                  "VIN- and VOUT- are the same ground.",
                  "boost step-up converter MT3608 module", g, P)


def springs():
    P = [pin("passive", -7.62, 2.54, 0, "A", "1"), pin("passive", -7.62, 0, 0, "B", "2"),
         pin("passive", -7.62, -2.54, 0, "C", "3"), pin("passive", 0, -10.16, 90, "MH", "4")]
    g = [rect(-5.08, 5.08, 5.08, -7.62),
         ["circle", ["center", 1.27, 0.0], ["radius", 2.54], ["stroke", ["width", 0.254], ["type", "default"]],
          ["fill", ["type", "none"]]],
         text("M", 1.27, 0)]
    return symbol("HDD_Motor_SpringContacts", "J", (0, 7.62), (0, 10.16),
                  "hdd-driver:HDD_SpringContacts_3P_P2.0mm", "",
                  "3.5in HDD spindle motor: three spring contacts pressing on PCB pads (phases A/B/C, no centre "
                  "tap), plus the M2 screw of the contact block (MH).",
                  "HDD spindle motor BLDC spring contact", g, P)


def main():
    lib = ["kicad_symbol_lib", ["version", 20251024], ["generator", Q("kicad_symbol_editor")],
           ["generator_version", Q("10.0")], weact(), simplefoc(), mt3608(), springs()]
    with open(LIB, "w") as f:
        f.write(dumps(lib) + "\n")
    print("wrote", LIB)


if __name__ == "__main__":
    main()
