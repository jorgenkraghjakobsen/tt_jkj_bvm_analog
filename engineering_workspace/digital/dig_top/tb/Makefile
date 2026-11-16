# cocotb regression for dig_top and its sequencer
#
#   make                        dig_top integration + bring-up test
#   make TEST=test_bg_seq       bg_seq phases
#   make TEST=test_bg_seq_rules bg_seq Step 6 boundary rules
#   make WAVES=1                also write a .vcd

WS := $(abspath $(CURDIR)/../../..)

TEST ?= test_dig_top

ifeq ($(TEST),test_dig_top)
    TOPLEVEL        = dig_top
    VERILOG_SOURCES = \
        $(WS)/digital/spi_slave/rtl/spi_slave.v \
        $(WS)/digital/reg_bank/rtl/reg_bank.v \
        $(WS)/digital/pwm/rtl/pwm.v \
        $(WS)/digital/dig_top/rtl/bg_seq.v \
        $(WS)/digital/dig_top/rtl/dig_top.v
else
    TOPLEVEL        = bg_seq
    VERILOG_SOURCES = $(WS)/digital/dig_top/rtl/bg_seq.v
endif

MODULE = $(TEST)

include $(WS)/setup/digital/cocotb/common.mk
