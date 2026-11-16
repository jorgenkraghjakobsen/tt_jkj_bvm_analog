# ============================================================
# bvm_analog_tapeout -- top-level build
#
#   make help        everything you can run
#   make status      component status and build order
# ============================================================

WS       := $(CURDIR)
PDK_ROOT ?= $(HOME)/.ciel/ciel/sky130/versions/792ef67037d74c8c51811eab3ce23cf793491296
VENV     ?= $(HOME)/eda-venv

# Put the venv on PATH for every target and every sub-make.
# VENV was declared above and used NOWHERE, so cocotb-config was
# found only when the venv happened to be active in the shell. After
# a 'wsl --shutdown' it was not, and common.mk's
#     include $(shell cocotb-config --makefiles)/Makefile.sim
# expanded to the literal path "/Makefile.sim". Every block then
# reported FAIL without running a single test -- which reads exactly
# like 26 broken tests and is not.
export PATH := $(VENV)/bin:$(PATH)

.PHONY: help status check graph \
        sim-digital bringup sim-spi sim-pwm sim-bgseq sim-bgrules sim-refstart sim-refres area harden harden-local \
        bg-analysis bg-array bg-pnp bg-pnp-corners bg-ideal bg-ota bg-settling bg-corners \
        sim-outbuf sim-bias sim-dac sim-doubler sim-ref \
        lvs-top clean

help:
	@echo ""
	@echo "Workspace"
	@echo "  make status        component table + build order"
	@echo "  make graph         dependency graph"
	@echo "  make check         fail if any depend.config is inconsistent"
	@echo ""
	@echo "Digital"
	@echo "  make sim-digital   every block, in dependency order"
	@echo "  make bringup       dig_top -- the duty-follows-register test"
	@echo "  make sim-spi / sim-pwm / sim-bgseq / sim-bgrules"
	@echo "  make sim-refres    cold start / PSRR / tempco of resistor_ref"
	@echo "  make sim-refstart  cold-start test for the fallback reference"
	@echo "  make area          dig_top cell area via yosys (no download)"
	@echo "  make harden        LibreLane (docker) -> GDS/LEF for dig_top"
	@echo "  make harden-local  same, for a nix/AppImage install"
	@echo ""
	@echo "Bandgap"
	@echo "  make bg-analysis   trim/TC, OTA requirement, area, current"
	@echo "  make bg-array      MIM common-centroid placement + check"
	@echo "  make bg-pnp        characterise the sky130 PNP (tt)"
	@echo "  make bg-pnp-corners  the same at tt / ss / ff"
	@echo "  make bg-ideal      ideal SC core (acceptance: within 1 mV)"
	@echo "  make bg-ota        OTA gain / GBW / phase margin at beta=1"
	@echo "  make bg-corners    OTA settling across PVT"
	@echo ""
	@echo "Other analog"
	@echo "  make sim-outbuf / sim-bias / sim-dac / sim-doubler / sim-ref"
	@echo ""
	@echo "Integration"
	@echo "  make lvs-top       tile-level LVS (needs obj/ extraction)"
	@echo ""
	@echo "  PDK_ROOT = $(PDK_ROOT)"
	@echo ""

# ---------------- workspace ----------------
status:
	@python3 scripts/workspace.py

graph:
	@python3 scripts/workspace.py --graph

check:
	@python3 scripts/workspace.py --check

# ---------------- digital ----------------
sim-digital:
	@scripts/run_digital_regression.sh

bringup:
	$(MAKE) -C digital/dig_top/tb TEST=test_dig_top

sim-spi:
	$(MAKE) -C digital/spi_slave/tb

sim-pwm:
	$(MAKE) -C digital/pwm/tb

sim-bgseq:
	$(MAKE) -C digital/dig_top/tb TEST=test_bg_seq

sim-bgrules:
	$(MAKE) -C digital/dig_top/tb TEST=test_bg_seq_rules

# Area estimate with yosys alone -- no LibreLane, no Docker.
# This is the number that decides 1x2 vs 2x2.
area:
	@PDK_ROOT=$(PDK_ROOT) setup/digital/synth_area.sh

# LibreLane via Docker. Run from the workspace ROOT, not from the
# config's directory: the container mounts the current directory, and
# the config's dir:: paths reach up into digital/, which would be
# outside the mount if we cd'd in first.
#
# PDK_ROOT points at the existing ciel install so LibreLane does not
# download a second multi-GB copy of sky130.
harden:
	PDK_ROOT=$(PDK_ROOT) PDK=sky130A \
	    librelane --dockerized setup/digital/librelane/config.json

harden-local:
	PDK_ROOT=$(PDK_ROOT) PDK=sky130A \
	    librelane setup/digital/librelane/config.json

# ---------------- analog helpers ----------------
# ngspice reads .spiceinit from the current directory.
define RUN_NGSPICE
	PDK_ROOT=$(PDK_ROOT) setup/analog/run_ngspice.sh $(1)/$(2)
endef

# ---------------- bandgap ----------------
bg-analysis:
	@python3 analog/bandgap/scripts/trim_analysis.py

bg-array:
	@python3 analog/bandgap/scripts/mim_array.py

bg-pnp:
	$(call RUN_NGSPICE,analog/bandgap/spice,tb_pnp_char.spice)

bg-ideal:
	$(call RUN_NGSPICE,analog/bandgap/spice,tb_sc_ideal.spice)

bg-ota:
	$(call RUN_NGSPICE,analog/bandgap/spice,tb_sc_ota.spice)

bg-settling:
	$(call RUN_NGSPICE,analog/bandgap/spice,tb_ota_settling.spice)

bg-pnp-corners:
	@for c in tt ss ff; do \
	  sed "s/sky130\.lib\.spice tt/sky130.lib.spice $$c/" \
	      analog/bandgap/spice/tb_pnp_char.spice \
	      > analog/bandgap/spice/.tb_pnp_$$c.spice; \
	  echo "===== $$c ====="; \
	  PDK_ROOT=$(PDK_ROOT) setup/analog/run_ngspice.sh \
	      analog/bandgap/spice/.tb_pnp_$$c.spice -b 2>&1 \
	    | grep -E 'vbe2_27|dvbe8_dt|ddvbe_dt|ratio_8i|code_8i' || true; \
	  rm -f analog/bandgap/spice/.tb_pnp_$$c.spice; \
	done

bg-corners:
	cp setup/analog/.spiceinit analog/bandgap/spice/ 2>/dev/null || true
	PDK_ROOT=$(PDK_ROOT) setup/analog/run_corners.sh \
	    analog/bandgap/spice/tb_ota_settling.spice

# ---------------- other analog ----------------
sim-outbuf:
	$(call RUN_NGSPICE,analog/out_buf/spice,tb_out_buf.spice)

# Cold-start test for the fallback reference. A .op cannot catch an
# inverted start-up branch; only a VDD ramp can.
# Characterise the resistor fallback: cold start, PSRR, tempco.
sim-refres:
	$(call RUN_NGSPICE,analog/bandgap/fallback/spice,tb_resistor_ref.spice)

sim-refstart:
	$(call RUN_NGSPICE,analog/bandgap/fallback/spice,tb_simple_ref_startup.spice)

sim-bias:
	$(call RUN_NGSPICE,analog/bias_gen/spice,tb_bias_gen.spice)

sim-dac:
	$(call RUN_NGSPICE,analog/pwm_dac/spice,tb_pwm_dac.spice)

sim-doubler:
	$(call RUN_NGSPICE,analog/clk_doubler/spice,tb_clk_doubler.spice)

sim-ref:
	$(call RUN_NGSPICE,analog/bandgap/fallback/spice,tb_simple_ref.spice)

# ---------------- integration ----------------
lvs-top:
	PDK_ROOT=$(PDK_ROOT) analog/tt_analog_top/lvs/run_lvs.sh tt_analog_top

clean:
	-$(MAKE) -C digital/spi_slave/tb clean 2>/dev/null
	-$(MAKE) -C digital/pwm/tb clean 2>/dev/null
	-$(MAKE) -C digital/dig_top/tb clean 2>/dev/null
	rm -rf obj/* analog/*/spice/corner_results
	find . -name '*.vcd' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
