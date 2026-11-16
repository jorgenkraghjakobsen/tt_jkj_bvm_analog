# Hardening `dig_top` with LibreLane

```bash
cd setup/digital/librelane
librelane config.json
```

## The area question you have to answer first

The `DIE_AREA` in `config.json` is a placeholder. The real number
decides whether this project fits a 1x2 tile.

A 1x2 analog tile is **160 x 225 um = 36 000 um^2 total**, and the
digital macro and every analog block share it.

Run synthesis and read the actual cell area out of the report before
committing. Then add up the analog side:

| Block | Rough area | Note |
|---|---|---|
| `dig_top` | from your synthesis report | the number you are about to measure |
| `pwm_dac` caps | ~1 000 um^2 | from the project's own filter table, 6-bit at 100 MHz |
| `pwm_dac` resistors | 2 x 2 Mohm in high-res poly | ~1 000 squares each, serpentined |
| `out_buf` x2 | two instances | one for ua[0], one inside the DAC |
| `bias_gen` | 31 unit devices plus switches | long-channel for matching, so not small |
| reference | bandgap or `simple_ref` | the SC bandgap needs a MIM array |
| guard rings, spacing | — | analog needs real spacing between blocks |

If digital plus analog exceeds roughly 70 % of 36 000 um^2, go to 2x2.
That costs 140 EUR and removes a week of compaction and DRC fighting.
Decide it from the synthesis number, not from optimism.

## Metal 5

`RT_MAX_LAYER` is pinned to `met4`. Metal 5 is reserved for the Tiny
Tapeout power grid and the macro must leave it clear for integration.

## Clocks

`clk` is 20 ns (50 MHz). `pwm0_clk` and `pwm1_clk` are constrained at
10 ns (100 MHz) because they may be driven by the clock doubler --
sign the PWM datapath off at the faster rate or it is not signed off
at all.

SPI `SCK` is deliberately *not* a clock. It is oversampled through a
3-stage synchroniser, so it is a false path. Keep SCK under about
5 MHz in the bring-up software.
