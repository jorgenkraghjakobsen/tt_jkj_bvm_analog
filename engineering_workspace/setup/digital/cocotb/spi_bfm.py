"""SPI master bus-functional model for the BVM mixed-signal tile.

Frame (mode 0, CS active low, 16 SCK pulses, MSB first):
    [15]    R/W     1 = read, 0 = write
    [14:8]  address 7 bits
    [7:0]   data

The DUT oversamples SCK with the system clock through a 3-stage
synchroniser, so SCK must be far slower than clk. Default here is one
SCK period every 20 system clocks (2.5 MHz against a 50 MHz core),
which leaves ample margin for the synchroniser.

MISO is sampled immediately BEFORE each rising edge, which is the value
the slave drove on the preceding falling edge -- standard mode-0
behaviour, and robust against the synchroniser's detection latency.
"""

from cocotb.triggers import Timer

CLK_PERIOD_NS = 20          # 50 MHz core clock
SCK_DIV       = 20          # SCK period in core-clock cycles


def _half_ns(sck_div=SCK_DIV, clk_period_ns=CLK_PERIOD_NS):
    return (clk_period_ns * sck_div) // 2


async def spi_idle(dut):
    """Put the SPI pins in their idle state."""
    dut.spi_cs_n.value = 1
    dut.spi_sck.value = 0
    dut.spi_mosi.value = 0
    await Timer(_half_ns(), "ns")


async def spi_xfer(dut, rw, addr, data=0, sck_div=SCK_DIV):
    """Run one 16-bit frame. Returns the 8 bits shifted out on MISO.

    For a write (rw=0) the returned value is not meaningful.
    """
    half = _half_ns(sck_div)
    frame = ((rw & 1) << 15) | ((addr & 0x7F) << 8) | (data & 0xFF)

    dut.spi_sck.value = 0
    dut.spi_cs_n.value = 0
    await Timer(half, "ns")             # let cs_sync settle (3 clk deep)

    rx = 0
    for i in range(16):
        dut.spi_mosi.value = (frame >> (15 - i)) & 1
        await Timer(half, "ns")

        # Sample MISO just before the rising edge.
        rx = (rx << 1) | int(dut.spi_miso.value)

        dut.spi_sck.value = 1
        await Timer(half, "ns")
        dut.spi_sck.value = 0

    await Timer(half, "ns")
    dut.spi_cs_n.value = 1
    await Timer(half, "ns")

    # Only the final 8 sampled bits carry read data.
    return rx & 0xFF


async def spi_write(dut, addr, data):
    await spi_xfer(dut, 0, addr, data)


async def spi_read(dut, addr):
    return await spi_xfer(dut, 1, addr, 0x00)


# Register map (mirrors reg_bank.v localparams)
ADDR_BG_CTRL   = 0x00
ADDR_BIAS_CTRL = 0x01
ADDR_CLK_CTRL  = 0x02
ADDR_PWM0_DUTY = 0x03
ADDR_PWM0_CTRL = 0x04
ADDR_PWM1_DUTY = 0x05
ADDR_PWM1_CTRL = 0x06
ADDR_STATUS    = 0x07
ADDR_BG_SEQ    = 0x08
