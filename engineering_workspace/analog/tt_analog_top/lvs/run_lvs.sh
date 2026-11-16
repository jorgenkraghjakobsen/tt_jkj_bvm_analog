#!/usr/bin/env bash
# ============================================================
# Tile-level LVS.
#
#   ./run_lvs.sh <block>        e.g. ./run_lvs.sh out_buf
#   ./run_lvs.sh tt_analog_top  the whole tile
#
# Expects the extracted netlist at obj/<block>_lvs.spice, produced in
# Magic with:
#     extract do local
#     extract all
#     ext2spice lvs
#     ext2spice -o <block>_lvs.spice
# ============================================================
set -u

BLOCK="${1:?usage: run_lvs.sh <block>}"
WS=$(cd "$(dirname "$0")/../../.." && pwd)

[ -n "${PDK_ROOT:-}" ] || { echo "PDK_ROOT is not set" >&2; exit 1; }

LAYOUT="$WS/obj/${BLOCK}_lvs.spice"
if [ "$BLOCK" = "tt_analog_top" ]; then
    SCHEM="$WS/analog/tt_analog_top/spice/tt_analog_top.spice"
else
    SCHEM="$WS/analog/${BLOCK}/spice/${BLOCK}.spice"
fi

for f in "$LAYOUT" "$SCHEM"; do
    [ -f "$f" ] || { echo "missing: $f" >&2; exit 1; }
done

mkdir -p "$WS/obj/lvs"
LOG="$WS/obj/lvs/${BLOCK}.log"

netgen -batch lvs \
    "$LAYOUT $BLOCK" \
    "$SCHEM $BLOCK" \
    "$PDK_ROOT/sky130A/libs.tech/netgen/sky130A_setup.tcl" \
    "$LOG"

echo
echo "--- tail of $LOG ---"
tail -20 "$LOG"
echo
if grep -q "Circuits match uniquely" "$LOG"; then
    echo "LVS PASS: $BLOCK"
else
    echo "LVS did not match. Read $LOG from the bottom."
    echo "  pin mismatch      -> a label on the wrong layer"
    echo "  device-count miss -> a missing tap or a shorted net"
    exit 1
fi
