"""dig_top: the bring-up test the project brief calls for.

  "Both PWMs run at 50 % from reset. If the duty follows the register
   after an SPI write, SPI and the register bank work before any analog
   block is measured."

That is exactly what test_bringup_duty_follows_register does, and it is
the single most important digital test on this tile.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from spi_bfm import (
    spi_write, spi_read, spi_idle, CLK_PERIOD_NS,
    ADDR_BG_CTRL, ADDR_BIAS_CTRL, ADDR_CLK_CTRL,
    ADDR_PWM0_DUTY, ADDR_PWM0_CTRL, ADDR_PWM1_DUTY, ADDR_STATUS,
)
from tb_util import measure_duty


async def _boot(dut):
    """Reset the macro with all three clocks running and ena asserted."""
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, "ns").start())
    cocotb.start_soon(Clock(dut.pwm0_clk, CLK_PERIOD_NS, "ns").start())
    cocotb.start_soon(Clock(dut.pwm1_clk, CLK_PERIOD_NS, "ns").start())

    dut.ena.value = 1
    dut.bias_ok.value = 0
    dut.rst_n.value = 0
    await spi_idle(dut)
    await Timer(300, "ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    # Let both PWM phase counters leave their reset state.
    for _ in range(300):
        await RisingEdge(dut.pwm0_clk)


@cocotb.test()
async def test_reset_defaults_readback(dut):
    """The reset values in reg_bank match the published register map."""
    await _boot(dut)

    expected = {
        ADDR_BG_CTRL:   0x88,   # bg_en=1, bg_trim=8
        ADDR_BIAS_CTRL: 0x90,   # bias_en=1, bias_trim=16
        ADDR_CLK_CTRL:  0x00,   # doubler off
        ADDR_PWM0_DUTY: 0x80,   # 50 %
        ADDR_PWM1_DUTY: 0x80,   # 50 %
        ADDR_PWM0_CTRL: 0x01,   # en=1, 6-bit, core clock
    }

    for addr, want in expected.items():
        got = await spi_read(dut, addr)
        assert got == want, \
            f"reg 0x{addr:02X} read back 0x{got:02X}, expected 0x{want:02X}"


@cocotb.test()
async def test_both_pwms_50_percent_from_reset(dut):
    """Both outputs sit at 50 % with no SPI traffic at all."""
    await _boot(dut)

    h0, t0 = await measure_duty(dut.pwm0_clk, dut.pwm0_out, 64)
    assert h0 == 32, f"PWM0 at reset gave {h0}/{t0}, expected 32/64"

    h1, t1 = await measure_duty(dut.pwm1_clk, dut.pwm1_out, 64)
    assert h1 == 32, f"PWM1 at reset gave {h1}/{t1}, expected 32/64"


@cocotb.test()
async def test_bringup_duty_follows_register(dut):
    """THE bring-up test: an SPI write changes the PWM duty.

    Passing this proves the SPI slave, the register bank and the PWM
    datapath are all working, before any analog block is powered.
    """
    await _boot(dut)

    h, t = await measure_duty(dut.pwm0_clk, dut.pwm0_out, 64)
    assert h == 32, f"precondition failed: PWM0 was {h}/{t}, expected 32/64"

    await spi_write(dut, ADDR_PWM0_DUTY, 0x40)       # 6-bit -> 16/64
    await Timer(2, "us")

    h, t = await measure_duty(dut.pwm0_clk, dut.pwm0_out, 64)
    assert h == 16, f"after writing 0x40, PWM0 gave {h}/{t}, expected 16/64"

    readback = await spi_read(dut, ADDR_PWM0_DUTY)
    assert readback == 0x40, \
        f"PWM0_DUTY read back 0x{readback:02X}, expected 0x40"

    # PWM1 must be untouched.
    h1, t1 = await measure_duty(dut.pwm1_clk, dut.pwm1_out, 64)
    assert h1 == 32, f"PWM1 disturbed by a PWM0 write: {h1}/{t1}"


@cocotb.test()
async def test_width_select_switches_period(dut):
    """Setting PWM0_CTRL bit1 moves PWM0 to the 256-clock period."""
    await _boot(dut)

    await spi_write(dut, ADDR_PWM0_CTRL, 0x03)       # en=1, width=1 (8-bit)
    await spi_write(dut, ADDR_PWM0_DUTY, 0x40)       # 64/256 = 25 %
    await Timer(5, "us")

    h, t = await measure_duty(dut.pwm0_clk, dut.pwm0_out, 256)
    assert h == 64, f"8-bit 0x40 gave {h}/{t}, expected 64/256"


@cocotb.test()
async def test_trim_outputs_follow_registers(dut):
    """Analog control pins change when their registers are written."""
    await _boot(dut)

    await spi_write(dut, ADDR_BG_CTRL, 0x8F)         # bg_en=1, trim=15
    await Timer(1, "us")
    assert int(dut.bg_trim.value) == 15, \
        f"bg_trim = {int(dut.bg_trim.value)}, expected 15"
    assert int(dut.bg_en.value) == 1

    await spi_write(dut, ADDR_BIAS_CTRL, 0x81)       # bias_en=1, trim=1
    await Timer(1, "us")
    assert int(dut.bias_trim.value) == 1, \
        f"bias_trim = {int(dut.bias_trim.value)}, expected 1"

    await spi_write(dut, ADDR_CLK_CTRL, 0x01)        # doubler on
    await Timer(1, "us")
    assert int(dut.dbl_en.value) == 1, "dbl_en did not follow CLK_CTRL"


@cocotb.test()
async def test_status_combines_bias_ok_and_bg_valid(dut):
    """STATUS[0] is bias_ok (synchronised) AND bg_valid."""
    await _boot(dut)

    dut.bias_ok.value = 0
    await Timer(20, "us")
    status = await spi_read(dut, ADDR_STATUS)
    assert (status & 0x01) == 0, "bg_ok set while bias_ok was low"

    dut.bias_ok.value = 1
    await Timer(40, "us")       # allow bg_seq to reach four updates
    status = await spi_read(dut, ADDR_STATUS)
    assert (status & 0x02) != 0, "bg_valid never set"
    assert (status & 0x01) != 0, "bg_ok not set with bias_ok high and bg_valid"


@cocotb.test()
async def test_phases_never_overlap_at_top(dut):
    """Non-overlap holds through the integrated macro too."""
    await _boot(dut)
    for _ in range(5000):
        await RisingEdge(dut.clk)
        if int(dut.phi1.value) and int(dut.phi2.value):
            raise AssertionError("phi1 and phi2 overlapped in dig_top")
