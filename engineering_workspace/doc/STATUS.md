# Project status

Target: Tiny Tapeout **TTSKY26d**, SkyWater SKY130, 2x2 analog tile
(334.88 x 225.76 um = 75,608 um2). Shuttle closes **2026-11-30**.

Scope was cut to **4 blocks**: bandgap, bias_gen, out_buf, resistor_ref.
`pwm_dac` and `clk_doubler` are dropped from the tile; their SPICE and
testbenches are kept in the tree for reference but are not built.

---

## Done

### Digital
| Item | Result |
|---|---|
| `dig_top` hardened (LibreLane) | LVS / DRC / antenna clean |
| `DIE_AREA` | `[0, 0, 190, 130]`, `FP_SIZING absolute` |
| cocotb regression | 26 / 26 passing |
| SPI CDC bug | fixed (edge detect on `sck_sync[2:1]`) |
| SDC | 3 clocks, async groups, false paths; `STA-0441` cleared |

Accepted/deferred: slew + max-cap violations in `ss` corners; `RSZ-0020`
noted as benign.

### Analog -- simulation
| Block | Headline numbers |
|---|---|
| `bias_gen` | monotonic, LSB 1.0499 uA, FS 32.468 uA |
| `out_buf` | all checks pass, 0.7-1.6 V window |
| `resistor_ref` | 1.001 uA, cold start < 1 us, PSRR +/-15.5 %, 0.030 %/degC |

`resistor_ref` tempco used an *ideal* resistor -- optimistic until the
real `res_xhigh_po` serpentine goes in.

### Analog -- layout
| Cell | Size (um) | DRC | Interface |
|---|---|---|---|
| `mim_array` | 83.66 x 65.70 | 0 | `SUM VBE DVBE OTAOUT TRIM8 TRIM4 TRIM2 TRIM1 VSS` |
| `ota_pair` | 43.24 x 15.25 | 0 | `ntail n1a n1 vinn vinp` |
| `nwell_ring` | 10.83 x 15.53 | 0 | (PDK-generated well + tap ring) |
| `mirror_load` | ~10.83 x 15.53 | *pending* | `vdd pg n1a n1` (expected) |

`mim_array` gradient error is **+0.0 ppm** on all three banks;
sigma(VREF) 1.45 mV assuming A_C = 1.0 %*um.

`ota_pair` uses **met4 internally**, so it must not be placed under the
`ua[2..7]` pin locations at top level.

---

## Remaining

1. **OTA devices**: `dev_n16_l4`, `dev_p80_l2_f4`, `dev_n80_l4_f2`,
   2x `dev_n10_l015`, the 750 fF Miller MIM, the 20 kOhm `res_high_po`.
2. **Bandgap core**: PNP devices + SC switch network, assembly,
   DRC/LVS, post-layout sim.
3. **Other blocks**: `bias_gen` (31-unit common-centroid array),
   `out_buf`, `resistor_ref` (1.2 MOhm `res_xhigh_po` serpentine).
4. **Top level**: place the 190x130 digital macro + 4 analog blocks in
   334.88 x 225.76; route control; connect `ua[0]`/`ua[1]`, keep
   `ua[2..7]` clear of met4 and vias; power below met5; merge to
   GDS + LEF.
5. **Submission**: repo from the TT template, local precheck (11
   checks), push.
6. **Bookkeeping**: DATASHEET numbers, 10 empty `OWNER` fields.

---

## Conventions that cost time -- do not re-derive

**Scale.** `.mag` files are in **internal units, 1 unit = 0.005 um**.
Magic's `box` command takes **lambda = 2 internal units**, so any box
argument is *half* the number in the file. Tech-file rule values are in
**nanometres**: divide by 5 for file units.

**Contacts are painted as cut + enclosure.** A painted via must be at
least cut + 2*enclosure; magic insets the real GDS cut itself.
via1 >= 52, via2 >= 56, via3 >= 64 units. Painting the bare cut
dimension from the DRC manual produces `via width < 0.26um` errors.

**Device cell gate rails claim met1 at both ends.** `unit_n10_l4` has a
met1 gate rail at x +/-396, y +/-(1032..1078); `unit_p10_l1` at x +/-96,
y +/-(1041..1087). Each comes within 10 units (0.05 um) of its terminal
strips, legal only via a corner diagonal. **met1 cannot escape a device
cell vertically** -- route on met2 and above, and use met1 only for
local 90x90 widenings (a via1 cannot meet enclosure on a 46-unit strip).

**Magic `w` is per finger; SPICE `W` is total.** Generate multi-finger
devices with `w_magic = W_spice / nf`.

**Magic boots in `minimum.tech`** and only switches when it loads a cell
that declares sky130A. `load` of a *non-existent* cell creates it in the
current tech -- so load a real sky130A cell first.

**nwell.4 is enforced**: every nwell needs a metal-connected N+ tap.
`sky130::nwell_draw` draws the well plus an `nsc`/`nsd` guard ring, but
stops at `li` -- add `viali` + met1 to reach a supply bus.
`nwell.2a` is `touching_ok`, so abutting wells merge legally.

**ngspice**: `ln` is a reserved function name; `.control` cannot read
`.param`; decks need `quit` in `.control` or they hang.
**OpenSTA** has no `remove_from_collection` (PrimeTime only).
**WSL2**: never `find /` -- it crawls `/mnt/c` over 9p.

---

## Not in this archive

`.mag` layout files are **not** stored in the repo. They are produced by
the generators in `analog/bandgap/scripts/` and live in the WSL2 tree
where magic runs. See `analog/bandgap/layout/README.md` for the exact
regeneration commands, including the `nwell_ring` PDK invocation.
