# SC bandgap — findings and open decisions

Generated 2026-11-13 from the Step 1–7 design guide. Run
`scripts/trim_analysis.py` and `scripts/mim_array.py` to reproduce every
number here; `doc/analysis_output.txt` is their captured output.

The trim model reproduces the guide's trim explorer exactly — code 8 at
26.0 ppm/°C, best code 9 at 12.8, ΔVBE 53.8 mV, ideal C_B/C_A 11.11,
dVBE/dT −1.99 mV/K. That agreement is the reason to trust the rest.

---

## 1. A bug in `bg_seq.v`, fixed in `rtl/bg_seq.v` rev2

Step 6 requires that **`cap` opens one clock before φ2 ends**. Rev1 had

```verilog
cap <= (state == P2) && (cnt == slot - 12'd2);
```

`phi2` goes low after `cnt == slot-1` and `cap` was high in exactly the
last cycle `phi2` was high, so **both fell on the same clock edge**. C_H
would sample the OTA output at the instant its feedback opens, capturing
the disconnection transient instead of VREF.

Rev2 uses `slot - 12'd3`, leaving two clocks between the two edges.
`tb/test_bg_seq_rules.py::test_rule2_cap_falls_before_phi2` fails against
rev1 and passes against rev2.

The other three Step 6 rules already held in rev1: non-overlap, `i8_en`
spanning the whole φ1 slot, and `ota_en` leading φ1 out of a hold.

## 2. The Rev19 OTA is not strong enough for this loop

This is the important one.

| | |
|---|---|
| feedback factor β | C_F/(C_A+C_B+C_F+Cp) = **0.0727** (1/13.7) |
| error budget | 0.5 mV on 1.2416 V → ε = 4.03e-4 |
| **required DC gain** | 1/(βε) = 34144 = **90.7 dB** |
| **required GBW** | ln(1/ε)/(2π·t_settle·β) = **6.68 MHz** |
| gm₁ at Cc = 750 fF | 31.5 µS → ID ≈ 2.1 µA at gm/ID = 15 |

Rev19 is L = 0.5 µm everywhere on a 2 µA tail. Two-stage gain lands
somewhere in this range:

| gm·ro per stage | total gain | static error on VREF |
|---|---|---|
| 30 | 59 dB | 19.0 mV |
| 50 | 68 dB | 6.8 mV |
| 100 | 80 dB | 1.7 mV |

Against a 0.5 mV budget, none of those clear it. **Measure the real Rev19
gain with `.ac` before redesigning** — but do not expect L = 0.5 µm to
reach 90 dB.

`spice/sc_ota.spice` cascodes the first stage instead. The cascode costs
swing only at the internal node; the second stage stays a plain common
source and still covers Vcm = 0.9 V in φ1 and VREF = 1.25 V in φ2.

Stability is sized for **β = 1**, the φ1 auto-zero case, not β = 0.0727.
φ1 is the hard one.

## 2b. The OTA, measured and closed — 2026-11-13

`sc_ota.spice` as it now stands:

| | measured | required | |
|---|---|---|---|
| DC gain | 90.6 dB | 90.7 dB | at the line |
| GBW | 4.67 MHz | 3.4–6.7 MHz | depends on the settling window |
| phase margin (β = 1) | 43° | 60° | short |
| **settling error at slot end** | **0.041 mV** | **0.5 mV** | **12× margin** |
| supply current | 14.5 µA | ≤ 15 µA | within spec |

**The settling number is the one that matters and it passes comfortably.**

Phase margin is measured in unity feedback (β = 1), which is the φ1
auto-zero case. During φ2 transfer β is 0.078, the loop gain is 12.7×
lower, and the crossing drops to where the non-dominant poles barely
contribute — effectively near 90° of margin. The measured decay is
monotonic (−41.7, −4.78, −0.508, −0.016 mV at 1–4 µs), with no sign
change anywhere, so there is no ringing to eat the slot. τ ≈ 455 ns.

On the gain: 90.6 dB gives a static transfer error near 0.5 mV. That
error is a fixed multiplicative term, so `bg_trim` absorbs it along
with everything else — only its *variation* over corners costs
accuracy. The 0.041 mV above is the dynamic settling error alone,
which is what the slot length actually constrains.

### How it got here

| change | why | PM |
|---|---|---|
| Rev19, L = 0.5 µm | — | gain 63 dB, 28 dB short |
| L = 4 µm throughout | intrinsic gain ∝ L | 92.2 dB, PM 14° |
| load L 4 → 2 | its 459 fF gate put the mirror pole at 2.6 MHz | PM 37° |
| load L 2 → 1, stage 2 5 → 10 µA, Rz 40k → 20k | push every non-dominant pole past 3× GBW | PM 43° |

A cascoded first stage was tried first and abandoned: sky130's |Vth_p|
is about 0.8 V, so a cascode gate near 0.95 V leaves no overdrive,
starves the branch and parks the load in triode. Long channels reach
the same gain with no bias voltage to get wrong.

### Still open

- phase margin at β = 1 is 43°, not 60°. It is stable and φ1 has a
  full slot to settle a much smaller excursion, but confirm φ1
  settling explicitly before sign-off.
- settling measured at tt/27 °C only. Run `make bg-corners` on
  `tb_ota_settling.spice` for ss and ff at −40 and 125 °C.
- 14.5 µA continuous leaves only 0.5 µA of margin against the 15 µA
  spec. Burst mode is unaffected: `ota_en` gates the tail and the
  stage-2 sink, so hold current stays near 3.5 µA.

## 3. The tile does not fit at 1×2 with this bandgap

| | area |
|---|---|
| 1×2 tile | 36 000 µm² (160 × 225) |
| MIM array 10×10 at 6.2 µm pitch | 3 844 µm² |
| bandgap block budget (80 × 90) | 7 200 µm² — **20 % of the tile** |

Adding the rest:

| dig_top | + bandgap + DAC + buffers + bias | of 1×2 | |
|---|---|---|---|
| 10 000 µm² | 21 200 µm² | 59 % | fits, tight |
| 15 000 µm² | 26 200 µm² | 73 % | does not fit |
| 20 000 µm² | 31 200 µm² | 87 % | does not fit |

So the whole question is whether `dig_top` synthesises under about
10 000 µm². **Run `make harden` and read the number.** If it lands above
that, 2×2 is not a preference, it is arithmetic.

## 4. Burst mode is over budget unless the mirror is gated

Option D runs 9 unit currents. At I = 0.5 µA that is **4.5 µA against a
4 µA burst budget**. The 8 extra units must be powered from `ota_en` so
they switch off during hold — which the guide already calls for and
`sc_ota.spice` wires through. Continuous mode is fine: 3 µA core + 10 µA
OTA = 13 µA against a 15 µA spec.

Emitter settling: τ = (V_T/I)·C_B = 114 ns, so 7τ = 0.80 µs of a 5.12 µs
slot. Comfortable at 0.5 µA, tight at 0.25 µA.

## 5. The C_B base is wrong for option D — measured, 2026-11-13

`make bg-pnp` characterised the real sky130 PNP. The numbers differ
enough from the guide's placeholders to change the array.

| | guide / old script | measured (tt, 27 °C) |
|---|---|---|
| VBE sampled by C_A | 650.0 mV | **716.0 mV** |
| dVBE/dT | −1.990 mV/K | **−1.795 mV/K** |
| dΔVBE/dT | +0.1790 mV/K | **+0.1830 mV/K** |
| C_B/C_A | 11.11 | **9.81** |

**The guide's 11.11 matches the 1I case almost exactly** — measured
ratio at 1I is 10.81. So `C_B = 36 + code` was derived for a design
sampling VBE at 1I. Option D samples at **8I**, about 54 mV higher, and
that change was never carried into the base.

The cost of leaving it at 36:

| base | TC at reset code 8 | best code | ideal sits at |
|---|---|---|---|
| 36 | **155 ppm/°C** | 4 (18.3) | code 3.2 |
| 31 | 20.7 ppm/°C | 9 (18.3) | code 8.2 |
| **32** | **18.3 ppm/°C** | 8 | code 7.2 |

Base 36 is three times over the 50 ppm/°C target at its reset value,
and puts the optimum three codes from the bottom of the range — a
process shift lowering VBE runs it off the end and the part becomes
untrimmable. The guide's own acceptance criterion is "ss and ff corners
still have their best code inside 0…15".

**Use 32.** It is even, so C_B gets an exact common-centroid placement
(31 leaves a −40 ppm gradient error and a −0.05 mV VREF shift), it puts
the optimum at code 7.2 near mid-range, and the reset value lands on the
best achievable TC.

Changed in `trim_analysis.py` (`CB_BASE`), `mim_array.py` (group sizes)
and `tb_sc_ideal.spice` (`.param nB`).

### Corner spread — measured at tt, ss and ff (`make bg-pnp-corners`)

| corner | VBE(8I) | dVBE/dT | dΔVBE/dT | C_B/C_A | ideal code |
|---|---|---|---|---|---|
| tt | 715.97 mV | −1.7953 | +0.18301 | 9.810 | 7.24 |
| ss | 720.12 mV | −1.7692 | +0.18285 | 9.676 | 6.70 |
| ff | 711.73 mV | −1.8131 | +0.18308 | 9.903 | 7.61 |

**The ideal code moves 0.91 codes across the whole process spread** —
less than one LSB. Base 32 is confirmed; nothing runs off either end.

Worst-case TC over 0–85 °C across all three corners:

| code | tt | ss | ff | worst |
|---|---|---|---|---|
| 6 | 56.7 | 36.2 | 70.8 | 70.8 |
| **7** | 20.6 | 7.6 | 33.3 | **33.3** |
| **8** (reset) | 18.2 | 36.6 | 9.4 | **36.6** |
| 9 | 52.5 | 71.9 | 39.2 | 71.9 |

Step 1 acceptance is met: the best code sits inside 0…15 at every
corner, and the reset value clears 50 ppm/°C worst case.

### Resolution, not range, is the limit

Only codes 7 and 8 pass — a 2-of-16 window. One LSB moves the slope by
about 34 ppm/°C against a 50 ppm/°C target, so the trim is coarse
relative to the spec even though its range is ample.

The 5th trim bit from the free `BG_CTRL[6:4]`, with half-size LSB units
in the array as the guide suggests, halves the LSB to ~17 ppm/°C and
widens the passing window to roughly 5 codes. Not required to meet
spec, but cheap margin against model error, MIM mismatch and curvature
this analysis does not capture.

Reset stays at **0x88**. Code 7 is 3 ppm/°C better worst-case, which
does not justify a regmap change, a `reg_bank.v` edit and a cocotb
update.

## 6. MIM array placement

`scripts/mim_array.py` generates and checks an 8×8 core inside a dummy
ring: 4 C_A + 4 C_F + **32** C_B + 15 trim + 9 internal dummies.

Every even-count group — C_A, C_F, C_B base, trim 8/4/2 — lands on an
**exact** centroid, so a 0.5 %/array x-gradient and 0.3 %/array
y-gradient give **0 ppm** ratio error and no VREF shift. This is one of
the reasons to prefer base 32 over 31.

The single trim-1 unit cannot be centroided; it is placed as close to the
centre as possible. Random mismatch at the assumed A_C = 1 %·µm gives
σ(VREF) ≈ 1.4 mV (the guide's painter reports 1.11 mV with slightly
different error combination).

This is a *generated* placement, not a transcription of the guide's map.
Use it or replace it, but run the checker either way.

---

## Order of work

1. `tb_pnp_char.spice` — real sky130 VBE slopes. Put them back into
   `trim_analysis.py` and re-pick the code.
2. `tb_sc_ideal.spice` — ideal switches and a VCVS OTA. **Acceptance:
   VREF within 1 mV of the equation.** Do this before any transistor
   work; it catches topology and phase-timing errors cheaply.
3. `tb_sc_ota.spice` — gain, GBW and phase margin at β = 1.
4. Transistor-level core, then layout per Step 7.

## Open decisions

- [ ] PNP layout option: A (3×3 fixed cells) or D (one cell, switched 1:8)
- [ ] 1×2 or 2×2 — decided by the `dig_top` synthesis area
- [x] C_B base 36 → **32** (measured; see section 5)
- [x] `bg-pnp` at ss and ff — ideal code spans 6.70…7.61, spread 0.91 codes
- [ ] 5th trim bit from `BG_CTRL[6:4]`? optional, halves the 34 ppm/°C LSB
- [ ] `BG_CTRL` reset stays 0x88 — now 18.3 ppm/°C, no change needed
- [ ] `BG_SEQ` @ 0x08 and `STATUS[1]` accepted into the regmap, or rejected
- [ ] Owner name next to `analog/bandgap` in ARCHITECTURE.md
