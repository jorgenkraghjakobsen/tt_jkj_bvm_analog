## How it works

A single SPI register bank controls every block on this mixed-signal
tile.

The digital macro contains an SPI slave (mode 0, 16-bit frames), a
register bank, two PWM generators sharing one design, and a phase
sequencer for the switched-capacitor reference. The analog side
contains a voltage reference, a trimmed bias generator, a clock
doubler and a PWM-driven DAC.

The reference sets the bias current, which sets the clock doubler's
delay and biases both output buffers. Every trim and enable bit lives
in the register bank.

### SPI frame

CS low, 16 clocks, MSB first:

| Bits | Field |
|---|---|
| [15] | R/W, 1 = read |
| [14:8] | address |
| [7:0] | data |

### Register map

| Addr | Name | Bits | Reset |
|---|---|---|---|
| 0x00 | BG_CTRL | [7] bg_en, [3:0] bg_trim | 0x88 |
| 0x01 | BIAS_CTRL | [7] bias_en, [4:0] bias_trim | 0x90 |
| 0x02 | CLK_CTRL | [0] dbl_en | 0x00 |
| 0x03 | PWM0_DUTY | [7:0] duty | 0x80 |
| 0x04 | PWM0_CTRL | [0] en, [1] width, [2] clk_sel | 0x01 |
| 0x05 | PWM1_DUTY | [7:0] duty | 0x80 |
| 0x06 | PWM1_CTRL | as PWM0_CTRL | 0x01 |
| 0x07 | STATUS | [0] bg_ok, [1] bg_valid | read-only |
| 0x08 | BG_SEQ | [2:0] div_sel, [3] burst, [7:4] hold_exp | 0x04 |

## How to test

Bring-up order matters. Prove the digital path before powering any
analog block.

1. Hold `rst_n` low, then release. With no SPI traffic at all, both
   `uo[0]` and `uo[1]` should show a 50 % square wave.
2. Write `0x40` to `PWM0_DUTY` (0x03). `uo[0]` should move to 25 %
   while `uo[1]` stays at 50 %.
3. Read `PWM0_DUTY` back over SPI. It should return `0x40`.

If step 2 works, the SPI slave, the register bank and the PWM
datapath are all confirmed, and anything still wrong is analog.

4. Read `STATUS` (0x07) and check `bg_valid`.
5. Measure `ua[0]` for the reference, `ua[1]` for the bias current,
   `ua[2]` for the DAC output.
6. Sweep `PWM0_DUTY` and watch `ua[2]` follow.

Keep SPI SCK below about 5 MHz: it is oversampled by the 50 MHz core
clock through a 3-stage synchroniser.

## External hardware

An SPI master (any microcontroller), and a voltmeter or scope on the
analog pins. A high-impedance instrument is assumed -- the output
buffer's drive into the worst-case 500 ohm pad load is limited.
