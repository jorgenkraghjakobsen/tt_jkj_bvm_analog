"""Shared helpers for the digital testbenches."""

from cocotb.triggers import RisingEdge


async def measure_duty(clk, sig, n_cycles):
    """Count cycles where `sig` is high, sampled on `clk` rising edges.

    Returns (high_count, n_cycles). Because the PWM counter free-runs,
    counting over exactly one full period gives the correct ratio
    regardless of where sampling starts.
    """
    high = 0
    for _ in range(n_cycles):
        await RisingEdge(clk)
        if int(sig.value) == 1:
            high += 1
    return high, n_cycles
