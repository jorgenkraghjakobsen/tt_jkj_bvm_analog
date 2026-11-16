"""bg_seq: the four rules the bandgap guide (Step 6) puts on the RTL.

  1. phi1 and phi2 are never high together
  2. cap falls BEFORE phi2 falls      <- rev1 of bg_seq.v fails this
  3. i8_en spans the whole phi1 slot, so the emitter current only
     changes inside the dead time
  4. ota_en is high for the slot before phi1 resumes after a hold

Rule 2 is the one with silicon consequences: if cap is still closed when
the OTA's feedback opens, C_H samples the disconnection transient rather
than VREF.
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


@cocotb.test()
async def test_rule1_non_overlap(dut):
    """phi1 and phi2 must never be high on the same cycle."""
    await _start(dut, div_sel=0)
    for _ in range(4000):
        await RisingEdge(dut.clk)
        assert not (int(dut.phi1.value) and int(dut.phi2.value)), \
            "phi1 and phi2 overlapped"


@cocotb.test()
async def test_rule2_cap_falls_before_phi2(dut):
    """cap must reach 0 at least one clock before phi2 does.

    Fails against bg_seq rev1, where cap sat in the final phi2 cycle.
    """
    await _start(dut, div_sel=0)

    prev_cap = 0
    prev_phi2 = 0
    cap_fall = None
    cycle = 0
    checked = 0

    for _ in range(6000):
        await RisingEdge(dut.clk)
        await Timer(1, "ns")
        cycle += 1
        cap = int(dut.cap.value)
        phi2 = int(dut.phi2.value)

        if prev_cap == 1 and cap == 0:
            cap_fall = cycle
        if prev_phi2 == 1 and phi2 == 0:
            assert cap_fall is not None, \
                "phi2 fell without cap ever having pulsed"
            gap = cycle - cap_fall
            assert gap >= 1, (
                f"cap fell on the same edge as phi2 (gap={gap}). "
                "C_H will sample the OTA disconnection transient."
            )
            checked += 1
            cap_fall = None

        prev_cap, prev_phi2 = cap, phi2

    assert checked >= 2, f"only saw {checked} phi2 falling edges"


@cocotb.test()
async def test_rule3_i8_spans_phi1(dut):
    """Whenever phi1 is high, i8_en must already be high."""
    await _start(dut, div_sel=0)
    for _ in range(4000):
        await RisingEdge(dut.clk)
        await Timer(1, "ns")
        if int(dut.phi1.value) == 1:
            assert int(dut.i8_en.value) == 1, \
                "phi1 high while i8_en low: emitter current switching " \
                "with sampling switches closed"


@cocotb.test()
async def test_rule4_ota_wakes_before_phi1(dut):
    """Coming out of a hold, ota_en leads phi1."""
    await _start(dut, div_sel=0, burst=1, hold_exp=2)

    prev_phi1 = 0
    saw = 0
    for _ in range(20000):
        await RisingEdge(dut.clk)
        await Timer(1, "ns")
        phi1 = int(dut.phi1.value)
        if phi1 == 1 and prev_phi1 == 0:
            assert int(dut.ota_en.value) == 1, \
                "phi1 rose with the OTA still disabled"
            saw += 1
            if saw >= 3:
                return
        prev_phi1 = phi1

    assert saw > 0, "never saw a phi1 rising edge in burst mode"
