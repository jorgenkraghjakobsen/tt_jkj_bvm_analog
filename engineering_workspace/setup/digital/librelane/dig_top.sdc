# ============================================================
# dig_top.sdc -- timing constraints for the digital macro
#
# clk is the only real clock. SPI SCK is NOT a clock: it is
# oversampled by a 3-stage synchroniser inside spi_slave, so it is
# constrained as a slow asynchronous input instead.
#
# REV 2, 2026-11-14. Two changes, both found by actually wiring this
# file into config.json -- rev 1 was never used, because
# PNR_SDC_FILE / SIGNOFF_SDC_FILE were not set and LibreLane fell
# back to a generic single-clock SDC.
# ============================================================

# ---- clocks -------------------------------------------------
create_clock -name clk -period 20.0 [get_ports clk]

set_clock_uncertainty 0.25 [get_clocks clk]
set_clock_transition  0.15 [get_clocks clk]

# pwm0_clk and pwm1_clk are muxed externally between clk and the
# doubled clock. Constrain them for the FASTER case, 100 MHz,
# otherwise the PWM datapath is signed off at the wrong speed.
create_clock -name pwm0_clk -period 10.0 [get_ports pwm0_clk]
create_clock -name pwm1_clk -period 10.0 [get_ports pwm1_clk]

set_clock_groups -asynchronous \
    -group [get_clocks clk] \
    -group [get_clocks pwm0_clk] \
    -group [get_clocks pwm1_clk]

# ---- asynchronous / slow inputs -----------------------------
# SPI pins and the analog status flag cross into the clk domain
# through synchronisers. Mark them false paths so the tool does not
# try to close timing on an asynchronous edge.
set_false_path -from [get_ports spi_sck]
set_false_path -from [get_ports spi_cs_n]
set_false_path -from [get_ports spi_mosi]
set_false_path -from [get_ports bias_ok]
set_false_path -from [get_ports ena]
set_false_path -from [get_ports rst_n]

# ---- I/O budget ---------------------------------------------
# CLOCK PORTS MUST BE EXCLUDED HERE.
# Rev 1 applied set_input_delay and set_driving_cell to
# [all_inputs], which includes clk, pwm0_clk and pwm1_clk. Putting
# an input delay on a port relative to a clock defined on that same
# port is illegal, and OpenSTA rejected it 25 times with
#   [STA-0441] set_input_delay relative to a clock defined on the
#              same port/pin not allowed
# The constraint was silently dropped for those ports.
# OpenSTA has NO remove_from_collection -- that is a Synopsys
# PrimeTime command, and using it killed the flow at stage 12 with
#   Error: dig_top.sdc, 52 invalid command name "remove_from_collection"
# all_inputs returns port handles, not names, so list filtering does
# not help either. dig_top has nine inputs and three are clocks, so
# the six data inputs are simply named. Add to this list if a port
# is ever added to dig_top.
set data_in [get_ports {rst_n ena spi_cs_n spi_sck spi_mosi bias_ok}]

set_input_delay  -clock clk 4.0 $data_in
set_output_delay -clock clk 4.0 [all_outputs]

set_driving_cell -lib_cell sky130_fd_sc_hd__inv_2 $data_in

# ---- output load --------------------------------------------
# 0.05 pF = 50 fF on every output. This is DELIBERATELY
# conservative and it is why max cap now violates in the three
# ss_100C_1v60 corners: those appeared only once this file was
# actually used.
#
# The real loads differ by an order of magnitude and are not yet
# known, because the analog layout does not exist:
#   - phi1/phi2/cap/ota_en/i8_en drive SC switch gates. sc_ota's
#     switches are W=10 L=0.15, so a few fF each plus routing --
#     realistically under 10 fF.
#   - pwm0_out/pwm1_out and spi_miso leave the tile through the TT
#     mux, so their load is route-dominated.
#
# Do NOT relax this number to clear the warnings. Extract the real
# loads once the analog is drawn, then set them per-net here. Until
# then 50 fF is the safe over-estimate and the ss violations are a
# documented limitation, not a surprise.
set_load 0.05 [all_outputs]
