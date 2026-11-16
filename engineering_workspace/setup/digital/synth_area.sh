#!/usr/bin/env bash
# ============================================================
# Estimate dig_top's cell area with yosys alone.
#
# No LibreLane, no Docker, no download -- this uses the yosys that
# came with OpenROAD-flow-scripts and the liberty file from the PDK
# you already have.
#
# It does NOT give you a GDS. It gives you the one number that
# decides 1x2 vs 2x2, which is what the floorplan is blocked on.
#
#   source ~/OpenROAD-flow-scripts/env.sh
#   export PDK_ROOT=...
#   setup/digital/synth_area.sh
# ============================================================
set -u

WS=$(cd "$(dirname "$0")/../.." && pwd)

command -v yosys >/dev/null || {
    echo "yosys not on PATH. Run: source ~/OpenROAD-flow-scripts/env.sh" >&2
    exit 1; }
[ -n "${PDK_ROOT:-}" ] || { echo "PDK_ROOT is not set" >&2; exit 1; }

LIB="$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
if [ ! -f "$LIB" ]; then
    echo "liberty file not found:" >&2
    echo "  $LIB" >&2
    echo "look for one with:" >&2
    echo "  find \$PDK_ROOT -name 'sky130_fd_sc_hd__tt*.lib' | head" >&2
    exit 1
fi

OUT="$WS/obj/synth_area"
mkdir -p "$OUT"

cat > "$OUT/synth_area.ys" << YOSYS
read_verilog $WS/digital/spi_slave/rtl/spi_slave.v
read_verilog $WS/digital/reg_bank/rtl/reg_bank.v
read_verilog $WS/digital/pwm/rtl/pwm.v
read_verilog $WS/digital/dig_top/rtl/bg_seq.v
read_verilog $WS/digital/dig_top/rtl/dig_top.v

hierarchy -check -top dig_top
synth -top dig_top -flatten
dfflibmap -liberty $LIB
abc -liberty $LIB
setundef -zero
splitnets
opt_clean -purge
stat -liberty $LIB
YOSYS

echo "running yosys..."
yosys -l "$OUT/synth.log" "$OUT/synth_area.ys" > /dev/null 2>&1 || {
    echo "yosys failed -- see $OUT/synth.log" >&2
    tail -20 "$OUT/synth.log" >&2
    exit 1; }

echo
sed -n '/=== dig_top ===/,/^$/p' "$OUT/synth.log" | tail -40

AREA=$(grep -oP 'Chip area for module .*: \K[0-9.]+' "$OUT/synth.log" | tail -1)
CELLS=$(grep -oP 'Number of cells: *\K[0-9]+' "$OUT/synth.log" | tail -1)

echo
echo "============================================================"
if [ -z "${AREA:-}" ]; then
    echo "  could not parse the area -- read $OUT/synth.log"
    exit 1
fi
printf "  cells          %s\n" "${CELLS:-?}"
printf "  CELL AREA      %s um^2\n" "$AREA"
echo "============================================================"

python3 - "$AREA" << 'PY'
import sys
cell = float(sys.argv[1])
tile = 160*225
analog = 11200          # bandgap 7200 + DAC caps/res 3000 + buffers/bias 1000
print()
print("  WHAT THIS MEANS FOR THE TILE")
print(f"    1x2 tile                 {tile:>8.0f} um^2")
print(f"    analog blocks (estimate) {analog:>8.0f} um^2")
print()
for util in (0.45, 0.55, 0.65):
    die = cell/util
    tot = die + analog
    pct = tot/tile*100
    verdict = "FITS" if pct < 70 else ("TIGHT" if pct < 85 else "DOES NOT FIT")
    print(f"    at {util*100:.0f}% utilisation: die {die:>7.0f}"
          f"  + analog = {tot:>7.0f} um^2 = {pct:>3.0f}% of 1x2   {verdict}")
print()
print("    Utilisation of 45-55% is realistic for a small macro with")
print("    this much I/O. Above ~70% of the tile, go 2x2.")
PY
