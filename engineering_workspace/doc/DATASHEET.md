# BVM Mixed-Signal Tile — datasheet

SKY130 · Tiny Tapeout **TTSKY26d** · submission closes 2026-11-30 ·
chips expected 2027-05-25

> Draft. Every number below is a target from the design documents, not
> a measured or simulated result. Nothing in this repository has been
> simulated yet.

## Overview

A single SPI register bank controls every block on the tile. The digital
macro holds an SPI slave, the register bank, two PWM generators sharing
one design, and the phase sequencer for the switched-capacitor
reference. The analog side holds the reference, a trimmed bias
generator, a clock doubler and a PWM-driven DAC.

The reference sets the bias current, which sets the clock doubler delay
and biases both output buffers. Every trim and enable bit is in the
register bank.

## Absolute limits (Tiny Tapeout analog template)

| | |
|---|---|
| Supply | 1.8 V (VDPWR) |
| Clock | up to 50 MHz from the harness |
| Analog pins | `ua[0..2]`, < 500 Ω, < 5 pF, 4 mA max |
| Tile | 1×2, 160 × 225 µm |
| Metal 5 | reserved for the TT power grid |
| PDN | ~20 mA of draw costs 0.1 V |

## Targets

| Item | Target | Set by |
|---|---|---|
| VREF | ≈ 1.24 V at code 8 | C_A/C_F = 1 |
| TC after trim | < 50 ppm/°C, 0–85 °C | trim LSB + curvature |
| Sampled noise | < 1 mV rms | unit cap size |
| Phase slot | 0.32–41 µs, default 5.12 µs | OTA settling |
| Current, continuous | ≤ 15 µA | bias core + OTA |
| Current, burst | ≤ 4 µA | the 8 extra mirror units must be gated |
| Bandgap area | ≈ 80 × 90 µm | mostly the MIM array |

## Register map

| Addr | Name | Bits | Reset |
|---|---|---|---|
| 0x00 | BG_CTRL | [7] bg_en, [3:0] bg_trim | 0x88 |
| 0x01 | BIAS_CTRL | [7] bias_en, [4:0] bias_trim | 0x90 |
| 0x02 | CLK_CTRL | [0] dbl_en | 0x00 |
| 0x03 | PWM0_DUTY | [7:0] duty | 0x80 |
| 0x04 | PWM0_CTRL | [0] en, [1] width, [2] clk_sel | 0x01 |
| 0x05 | PWM1_DUTY | [7:0] duty | 0x80 |
| 0x06 | PWM1_CTRL | as PWM0_CTRL | 0x01 |
| 0x07 | STATUS (ro) | [0] bg_ok, [1] bg_valid | — |
| 0x08 | BG_SEQ | [2:0] div_sel, [3] burst, [7:4] hold_exp | 0x04 |

`BG_SEQ` and `STATUS[1]` are proposed additions and still need a regmap
database entry, or a recorded reason for rejection.

### Trim

Capacitor trim: **C_B = 32 + `bg_trim`** units, C_A = C_F = 4 units.

Based on the measured sky130 PNP (`make bg-pnp`, tt, 27 °C): VBE at the
8I sampling point is 716.0 mV, dVBE/dT −1.795 mV/K, dΔVBE/dT
+0.1830 mV/K, giving an ideal C_B/C_A of 9.81.

| code | C_B | VREF @ 27 °C | TC (0–85 °C) |
|---|---|---|---|
| 7 | 39 | 1.2477 V | 20.7 ppm/°C |
| **8 (reset 0x88)** | 40 | **1.2614 V** | **18.3 ppm/°C** |
| 9 | 41 | 1.2750 V | 52.6 ppm/°C |

The base was 36 in the original plan, which suited a design sampling
VBE at 1I. Option D samples at 8I and needs 32; at 36 the reset value
would have been 155 ppm/°C. See `analog/bandgap/doc/BANDGAP_NOTES.md`
section 5.

Measured at tt, ss and ff. The ideal code spans 6.70–7.61, a spread of
under one LSB, so the 4-bit trim covers the process corners with ample
range. Worst-case TC across corners: code 7 → 33.3 ppm/°C, code 8 →
36.6 ppm/°C; codes 6 and 9 exceed 50.

Only two codes pass, so trim *resolution* is the binding constraint —
one LSB is ~34 ppm/°C. `BG_CTRL[6:4]` remains free for a 5th trim bit
if more margin is wanted.

## SPI

Mode 0, CS active low, 16 clocks, MSB first:
`[15]` R/W (1 = read), `[14:8]` address, `[7:0]` data.

SCK is oversampled by the 50 MHz core clock through a 3-stage
synchroniser. **Keep SCK below about 5 MHz.**

## Pinout

See `analog/tt_analog_top/doc/FLOORPLAN.md`.
