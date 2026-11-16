# bvm_analog_tapeout

SKY130 · Tiny Tapeout **TTSKY26d** · submission closes **2026-11-30**

One folder per block, each with its own `depend.config`, all listed in
`workspace.config`.

```
bvm_analog_tapeout/
├── workspace.config          components in this project
├── setup/
│   ├── analog/               xschemrc, corner runner, layout tech files
│   └── digital/              LibreLane flow, cocotb common
├── analog/
│   ├── bandgap/  bias_gen/  clk_doubler/  out_buf/  pwm_dac/
│   └── tt_analog_top/        top schematic + layout, LVS
├── digital/
│   ├── spi_slave/  reg_bank/  pwm/
│   └── dig_top/              integration and harden
├── tapeout/                  the Tiny Tapeout repo we submit
├── obj/                      build outputs (not in git)
└── doc/                      datasheet, bring-up notes
```

```bash
make status      # component table + build order, read from depend.config
make help        # everything runnable
```

---

## Verification state

**Nothing here has been simulated.** It was written without a simulator
or the PDK. Python, shell, JSON and YAML are syntax-checked; the SPI
framing and the register map were hand-traced against the RTL. Treat
every file as a reviewable draft.

| | state |
|---|---|
| Digital RTL | yours, unchanged, except `bg_seq.v` rev2 (see below) |
| cocotb benches | new, never executed |
| LibreLane config | new, never run — `DIE_AREA` is a placeholder |
| Analog SPICE | new, never simulated |
| **Analog layout** | **does not exist** — and cannot be generated here |

Layout is the long pole and it is entirely yours. Schematics and
netlists are the easy half.

## `make status`

Reads `workspace.config`, follows each block's `depend.config`, checks
the graph and prints a build order:

```
pwm -> reg_bank -> spi_slave -> dig_top -> bandgap
    -> bias_gen -> clk_doubler -> out_buf -> pwm_dac -> tt_analog_top
```

It also reports every component with no `OWNER` set. Filling those in is
a "done when" item in the design guide.

## Three findings

Full reasoning in `analog/bandgap/doc/BANDGAP_NOTES.md`.

**1. `bg_seq.v` had a timing bug.** `cap` and `phi2` fell on the same
clock edge, so C_H would sample the OTA's disconnection transient rather
than VREF. Fixed in rev2. `make sim-bgrules` is the test that catches it;
it fails against rev1.

**2. The Rev19 OTA cannot drive this loop.** β = 0.0727 and a 0.5 mV
budget demand **90.7 dB** and **6.68 MHz GBW**. L = 0.5 µm everywhere
reaches 60–80 dB, i.e. 1.7–19 mV of static error.
`analog/bandgap/spice/sc_ota.spice` cascodes the first stage instead.

**3. The tile may not fit at 1×2.** The bandgap alone budgets 7 200 µm²
of 36 000. `make harden` gives the `dig_top` area that settles it.
See `analog/tt_analog_top/doc/FLOORPLAN.md`.

The trim model reproduces the design guide's explorer exactly — code 8 →
26.0 ppm/°C, best code 9 → 12.8, ΔVBE 53.8 mV — which is the reason to
trust the rest of the arithmetic.

## Order of work

```bash
make bringup       # proves SPI + register bank + PWM datapath
make harden        # the area number that decides 1x2 vs 2x2
make bg-pnp        # real sky130 VBE slopes
make bg-ideal      # SC topology with ideal switches: within 1 mV
make bg-ota        # gain, GBW, phase margin at beta = 1
```

Then transistor-level analog, then layout.

## Setup

```bash
source ~/eda-venv/bin/activate
export PDK_ROOT=$HOME/.ciel/ciel/sky130/versions/<hash>
```

`PDK_ROOT` is also set at the top of the Makefile — check it matches.

## Before submitting

- [ ] Copy the real port declaration into `tapeout/src/project.v`
- [ ] Check every field in `info.yaml` against the current template
- [ ] Set `DIE_AREA` from a real synthesis report
- [ ] Confirm no digital output pin floats
- [ ] Confirm Metal 5 is clear in every macro
- [ ] `BG_SEQ` @ 0x08 and `STATUS[1]` entered in the regmap, or rejected
- [ ] An `OWNER` in every `depend.config` (`make status` lists the gaps)
- [ ] Push a trivial design through the whole flow before the real one
