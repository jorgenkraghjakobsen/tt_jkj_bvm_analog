#!/usr/bin/env bash
# Run the OTA settling deck across process corners and temperatures.
# Usage: ./run_corners.sh [deck.spice]
set -u
DECK="${1:-tb_ota_settling.spice}"
OUT=corner_results
mkdir -p "$OUT"

for corner in tt ss ff; do
  for temp in -40 27 125; do
    tag="${corner}_${temp}C"
    echo "=== $tag ==="
    sed -e "s/sky130\.lib\.spice tt/sky130.lib.spice ${corner}/" \
        -e "1a .temp ${temp}" \
        "$DECK" > "$OUT/deck_${tag}.spice"
    ( cd "$OUT" && ngspice -b "deck_${tag}.spice" > "log_${tag}.txt" 2>&1 )
    grep -i -E 'tset|i\(vdd\)' "$OUT/log_${tag}.txt" | head -5 || echo "  (no measurement found)"
  done
done

echo
echo "Acceptance: tset < 5.12 us in all nine runs."
