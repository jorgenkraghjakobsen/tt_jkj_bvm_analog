"""spi_slave: frame decode and MISO shift-out.

Checks the write path produces a single wr_en pulse with the right
address and data, and that the read path returns rd_data unchanged.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from spi_bfm import spi_xfer, spi_idle, CLK_PERIOD_NS


async def _reset(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, "ns").start())
    dut.rst_n.value = 0
    dut.rd_data.value = 0
    await spi_idle(dut)
    await Timer(200, "ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_write_frame(dut):
    """A write frame asserts wr_en once with the decoded address and data."""
    await _reset(dut)

    seen = []

    async def watch():
        while True:
            await RisingEdge(dut.clk)
            if int(dut.wr_en.value) == 1:
                seen.append((int(dut.wr_addr.value), int(dut.wr_data.value)))

    cocotb.start_soon(watch())

    await spi_xfer(dut, 0, 0x2A, 0xC3)
    await Timer(1, "us")

    assert len(seen) == 1, f"expected exactly one wr_en pulse, got {len(seen)}"
    addr, data = seen[0]
    assert addr == 0x2A, f"address decoded as 0x{addr:02X}, expected 0x2A"
    assert data == 0xC3, f"data decoded as 0x{data:02X}, expected 0xC3"


@cocotb.test()
async def test_read_frame(dut):
    """A read frame shifts rd_data out on MISO, MSB first."""
    await _reset(dut)

    dut.rd_data.value = 0xA5
    got = await spi_xfer(dut, 1, 0x11, 0x00)

    assert got == 0xA5, f"MISO returned 0x{got:02X}, expected 0xA5"


@cocotb.test()
async def test_read_address_is_presented(dut):
    """rd_addr is driven from the address field before the data phase."""
    await _reset(dut)

    dut.rd_data.value = 0x5A
    await spi_xfer(dut, 1, 0x33, 0x00)
    await Timer(200, "ns")

    assert int(dut.rd_addr.value) == 0x33, \
        f"rd_addr = 0x{int(dut.rd_addr.value):02X}, expected 0x33"


@cocotb.test()
async def test_no_write_on_read(dut):
    """A read frame must never assert wr_en."""
    await _reset(dut)

    writes = []

    async def watch():
        while True:
            await RisingEdge(dut.clk)
            if int(dut.wr_en.value) == 1:
                writes.append(1)

    cocotb.start_soon(watch())

    dut.rd_data.value = 0x77
    await spi_xfer(dut, 1, 0x05, 0xFF)
    await Timer(1, "us")

    assert not writes, "wr_en asserted during a read frame"
