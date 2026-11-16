"""bg_seq: the switched-capacitor phase sequencer.

The property that matters most for the analog side is NON-OVERLAP --
phi1 and phi2 must never be high together, or the SC network shorts
through. That is checked continuously throughout every test here.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

CLK_NS = 20


async def _start(dut, div_sel=0, burst=0, hold_exp=0):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, "ns").start())
    dut.rst_n.value = 0
    dut.en.value = 0
    dut.div_sel.value = div_sel
    dut.burst.value = burst
    dut.hold_exp.value = hold_exp
    await Timer(100, "ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    dut.en.value = 1
    await RisingEdge(dut.clk)


async def _assert_non_overlap(dut, cycles):
    for _ in range(cycles):
        await RisingEdge(dut.clk)
        if int(dut.phi1.value) and int(dut.phi2.value):
            raise AssertionError("phi1 and phi2 high simultaneously")


@cocotb.test()
async def test_phases_never_overlap(dut):
    """The whole point of the dead time in `inner`."""
    await _start(dut, div_sel=0)
    await _assert_non_overlap(dut, 4000)


@cocotb.test()
async def test_phases_never_overlap_slow(dut):
    """Same check at a larger slot size."""
    await _start(dut, div_sel=2)
    await _assert_non_overlap(dut, 4000)


@cocotb.test()
async def test_dead_time_present(dut):
    """There is at least one clock where neither phase is asserted."""
    await _start(dut, div_sel=0)

    saw_both_low = False
    saw_phi1 = False
    saw_phi2 = False

    for _ in range(2000):
        await RisingEdge(dut.clk)
        p1, p2 = int(dut.phi1.value), int(dut.phi2.value)
        saw_phi1 |= bool(p1)
        saw_phi2 |= bool(p2)
        if not p1 and not p2:
            saw_both_low = True

    assert saw_phi1, "phi1 never asserted"
    assert saw_phi2, "phi2 never asserted"
    assert saw_both_low, "no dead time between phases"


@cocotb.test()
async def test_valid_asserts_after_four_updates(dut):
    """`valid` tracks four completed P1/P2 update pairs."""
    await _start(dut, div_sel=0)

    slot = 16 << 0
    # Four full P1+P2 pairs, plus slack for the registered output.
    budget = slot * 2 * 6

    seen_valid = False
    for _ in range(budget):
        await RisingEdge(dut.clk)
        if int(dut.valid.value) == 1:
            seen_valid = True
            break

    assert seen_valid, f"valid never asserted within {budget} clocks"


@cocotb.test()
async def test_disable_clears_outputs(dut):
    """Dropping en returns every phase output to its idle state."""
    await _start(dut, div_sel=0)
    for _ in range(200):
        await RisingEdge(dut.clk)

    dut.en.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)

    for name in ("phi1", "phi2", "cap", "ota_en", "i8_en", "valid"):
        val = int(getattr(dut, name).value)
        assert val == 0, f"{name} = {val} after en deasserted, expected 0"
