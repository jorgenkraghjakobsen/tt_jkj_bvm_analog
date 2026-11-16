"""pwm: duty ratio in both widths, plus the enable and end-stop cases.

6-bit mode uses duty[7:2] over a 64-clock period.
8-bit mode uses duty[7:0] over a 256-clock period.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from tb_util import measure_duty

CLK_NS = 20


async def _setup(dut, width_sel, duty, enable=1):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, "ns").start())
    dut.rst_n.value = 0
    dut.enable.value = 0
    dut.width_sel.value = width_sel
    dut.duty.value = duty
    await Timer(100, "ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    dut.enable.value = enable
    # Let the counter run clear of the reset state before measuring.
    for _ in range(300):
        await RisingEdge(dut.clk)


@cocotb.test()
async def test_6bit_half_duty(dut):
    """0x80 in 6-bit mode is duty_6 = 32 of 64, i.e. 50%."""
    await _setup(dut, width_sel=0, duty=0x80)
    high, total = await measure_duty(dut.clk, dut.pwm_out, 64)
    assert high == 32, f"6-bit 0x80 gave {high}/{total}, expected 32/64"


@cocotb.test()
async def test_6bit_quarter_duty(dut):
    """0x40 in 6-bit mode is duty_6 = 16 of 64, i.e. 25%."""
    await _setup(dut, width_sel=0, duty=0x40)
    high, total = await measure_duty(dut.clk, dut.pwm_out, 64)
    assert high == 16, f"6-bit 0x40 gave {high}/{total}, expected 16/64"


@cocotb.test()
async def test_8bit_half_duty(dut):
    """0x80 in 8-bit mode is 128 of 256."""
    await _setup(dut, width_sel=1, duty=0x80)
    high, total = await measure_duty(dut.clk, dut.pwm_out, 256)
    assert high == 128, f"8-bit 0x80 gave {high}/{total}, expected 128/256"


@cocotb.test()
async def test_zero_duty_is_always_low(dut):
    await _setup(dut, width_sel=1, duty=0x00)
    high, _ = await measure_duty(dut.clk, dut.pwm_out, 256)
    assert high == 0, f"duty 0x00 produced {high} high cycles, expected 0"


@cocotb.test()
async def test_full_duty_is_always_high(dut):
    await _setup(dut, width_sel=1, duty=0xFF)
    high, total = await measure_duty(dut.clk, dut.pwm_out, 256)
    assert high == total, f"duty 0xFF produced {high}/{total}, expected all high"


@cocotb.test()
async def test_disabled_output_is_low(dut):
    await _setup(dut, width_sel=1, duty=0x80, enable=0)
    high, _ = await measure_duty(dut.clk, dut.pwm_out, 256)
    assert high == 0, f"output was high for {high} cycles while disabled"
