# ============================================================
# Shared cocotb settings for every digital block.
#
# A block's tb/Makefile sets WS, VERILOG_SOURCES, TOPLEVEL and MODULE,
# then includes this file. This keeps the simulator choice, the
# language dialect and the PYTHONPATH for the shared BFM in one place.
#
#   make                 run the block's tests
#   make WAVES=1         also write <TOPLEVEL>.vcd
#   make SIM=verilator   if you have it; icarus is the default
# ============================================================

ifndef WS
  $(error WS is not set. The block Makefile must define it.)
endif
ifndef TOPLEVEL
  $(error TOPLEVEL is not set.)
endif

SIM           ?= icarus
TOPLEVEL_LANG ?= verilog

# Icarus needs 2012 acceptance for these sources.
COMPILE_ARGS += -g2012

# spi_bfm.py and tb_util.py live here, not in the block.
export PYTHONPATH := $(WS)/setup/digital/cocotb:$(PYTHONPATH)

ifeq ($(WAVES),1)
    VERILOG_SOURCES += $(WS)/setup/digital/cocotb/dump_$(TOPLEVEL).v
    COMPILE_ARGS    += -s dump_$(TOPLEVEL)
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
