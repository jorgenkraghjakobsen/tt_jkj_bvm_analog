# cocotb regression for spi_slave
#   make            run
#   make WAVES=1    also write spi_slave.vcd

WS := $(abspath $(CURDIR)/../../..)

VERILOG_SOURCES = $(WS)/digital/spi_slave/rtl/spi_slave.v
TOPLEVEL        = spi_slave
MODULE          = test_spi_slave

include $(WS)/setup/digital/cocotb/common.mk
