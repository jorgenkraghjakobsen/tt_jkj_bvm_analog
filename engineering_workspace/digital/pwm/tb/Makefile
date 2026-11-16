# cocotb regression for pwm
#   make            run
#   make WAVES=1    also write pwm.vcd

WS := $(abspath $(CURDIR)/../../..)

VERILOG_SOURCES = $(WS)/digital/pwm/rtl/pwm.v
TOPLEVEL        = pwm
MODULE          = test_pwm

include $(WS)/setup/digital/cocotb/common.mk
