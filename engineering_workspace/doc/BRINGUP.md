# Bring-up notes

Order matters. Prove the digital path before powering any analog block —
if the PWM duty follows a register write, the SPI slave, the register
bank and the PWM datapath are all confirmed, and anything still wrong is
analog.

## 0. Bench

An SPI master (any microcontroller), a scope on `uo[0]`/`uo[1]`, and a
**high-impedance** meter on the analog pins. The output buffer's drive
into the worst-case 500 Ω pad load is limited by design — see the note
in `analog/out_buf/depend.config`.

Keep SCK under 5 MHz.

## 1. Digital, no analog

| Step | Do | Expect |
|---|---|---|
| 1.1 | Release `rst_n`, send no SPI at all | `uo[0]` and `uo[1]` both 50 % square waves |
| 1.2 | Read 0x00, 0x01, 0x03, 0x04 | 0x88, 0x90, 0x80, 0x01 |
| 1.3 | Write 0x40 to 0x03 (PWM0_DUTY) | `uo[0]` → 25 %, `uo[1]` unchanged at 50 % |
| 1.4 | Read 0x03 back | 0x40 |
| 1.5 | Write 0x03 to 0x04 (8-bit mode), 0x40 to 0x03 | `uo[0]` → 25 % at a 4× longer period |

If 1.3 fails but 1.2 passes, the register bank is fine and the fault is
in the PWM datapath or the clock mux. If 1.2 fails, suspect SPI timing
first — the synchroniser needs SCK well below the core clock.

## 2. Reference

| Step | Do | Expect |
|---|---|---|
| 2.1 | Read 0x07 (STATUS) | `bg_valid` set after a few frames |
| 2.2 | Measure `ua[0]` | ≈ 1.24 V at reset code 8 |
| 2.3 | Sweep `bg_trim` 0→15 via 0x00 | VREF moves ~13.5 mV per code |
| 2.4 | Repeat 2.2 hot and cold | TC under 50 ppm/°C over 0–85 °C |

Each trim code is one C_B unit, so the step is VREF/(C_B) ≈ 13 mV. If
the steps are not monotonic, suspect the MIM array wiring, not the trim
logic.

## 3. Bias

| Step | Do | Expect |
|---|---|---|
| 3.1 | Measure `ua[1]` at `bias_trim` = 16 | ≈ 16 µA |
| 3.2 | Sweep `bias_trim` 1→31 | monotonic, ~1 µA per code |

Non-monotonicity here means the binary weighting came from device width
rather than device count. That is a layout bug, not a trim bug.

## 4. Clock doubler

| Step | Do | Expect |
|---|---|---|
| 4.1 | Write 0x01 to 0x02 (`dbl_en`) | — |
| 4.2 | Set PWM0 `clk_sel` = 1 via 0x04 | `uo[0]` period halves |

Measure the doubled clock's **duty**, not just its frequency. A duty
error feeds straight through PWM 0 into the DAC as a DC offset.

## 5. DAC

| Step | Do | Expect |
|---|---|---|
| 5.1 | Sweep `PWM0_DUTY` 0x00→0xFF | `ua[2]` follows roughly linearly |
| 5.2 | Check ripple at mid-scale | well under one LSB (28 mV at 6 bits) |
| 5.3 | Check the ends of the sweep | curvature near 0 V is the buffer's input common-mode floor |

Step 5.3 is expected, not a fault: the NMOS input pair cannot follow its
input to ground. If the low end is unusable, that is the known
limitation recorded in `analog/out_buf/depend.config`.

## 6. Burst mode

| Step | Do | Expect |
|---|---|---|
| 6.1 | Write `burst` = 1, `hold_exp` = 8 via 0x08 | supply current drops |
| 6.2 | Measure VREF droop between captures | compare with the Step 6 calculator |

Droop at 125 °C is the number that decides how long a hold is usable.
