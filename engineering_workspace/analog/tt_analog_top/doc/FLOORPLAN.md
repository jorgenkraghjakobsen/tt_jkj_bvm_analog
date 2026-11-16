# tt_analog_top — floorplan and pins

Template `tt_analog_1x2.def`, **160 × 225 µm = 36 000 µm²**.

## The area question

| | µm² | of tile |
|---|---|---|
| bandgap (80 × 90 budget) | 7 200 | 20 % |
| └ of which MIM array 10×10 @ 6.2 µm | 3 844 | 11 % |
| pwm_dac capacitors | ~1 000 | 3 % |
| pwm_dac resistors (2 × 2 MΩ poly) | ~2 000 | 6 % |
| out_buf × 2 | ~400 | 1 % |
| bias_gen + clk_doubler | ~600 | 2 % |
| **analog subtotal** | **~11 200** | **31 %** |
| dig_top | *measure it* | |

So `dig_top` has roughly 14 000 µm² before the tile passes 70 %
utilisation, and analog needs real spacing and guard rings on top.

**Run `make harden` and read the cell area.** Above about 10 000 µm²,
2×2 stops being a preference and becomes arithmetic. See
`setup/digital/librelane/README.md`.

## Placement rules

- **Metal 5 is reserved** for the Tiny Tapeout power grid. Nothing in
  any block may use it. `RT_MAX_LAYER` is pinned to met4 for `dig_top`.
- Keep the bandgap's MIM array away from the digital macro: phase lines
  and digital switching over node X inject charge every cycle.
- The phase buffers are the noisy part of the bandgap — keep them at the
  block edge, in their own guard ring.
- `pwm_dac`'s second filter node is high impedance. Any leakage or
  coupling there is a DC error straight onto `ua[2]`.
- Every n-well needs an N-tap, every NMOS region a nearby P-tap. A
  floating well shows up as an unexpected bulk net at LVS.

## Pins

| Pin | Direction | Net |
|---|---|---|
| `ua[0]` | analog out | VREF through `out_buf` instance 1 |
| `ua[1]` | analog out | bias current monitor |
| `ua[2]` | analog out | DAC output through `out_buf` instance 2 |
| `uio[0]` | in | SPI CS_N |
| `uio[1]` | in | SPI MOSI |
| `uio[2]` | out | SPI MISO |
| `uio[3]` | in | SPI SCK |
| `uo[0]` | out | PWM 0 (also drives the DAC filter) |
| `uo[1]` | out | PWM 1 |
| `clk` `ena` `rst_n` | in | TT harness |
| `VDPWR` `VGND` | power | 1.8 V and ground |

Unused `uo_out`, `uio_out` and `uio_oe` bits are tied low in
`tapeout/src/project.v`. The TT analog spec requires it.

## Analog pin cost

40 € each for the first two, 100 € for each one after. The third pin
costs more than the first two together — if `ua[1]` is diagnostic
rather than essential, dropping it saves 100 € and some routing.
