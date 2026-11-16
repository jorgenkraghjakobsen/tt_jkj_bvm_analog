#!/usr/bin/env bash
# ============================================================
# Project corner runner.
#
#   setup/analog/run_corners.sh <deck.spice> [outdir]
#
# Runs the deck across tt/ss/ff and -40/27/125 C by rewriting the
# .lib line and injecting .temp, then greps the measurements out.
#
# Needs PDK_ROOT set and a .spiceinit beside the deck.
# ============================================================
set -u

DECK="${1:?usage: run_corners.sh <deck.spice> [outdir]}"
OUT="${2:-corner_results}"

[ -f "$DECK" ] || { echo "no such deck: $DECK" >&2; exit 1; }
[ -n "${PDK_ROOT:-}" ] || { echo "PDK_ROOT is not set" >&2; exit 1; }

DECK_DIR=$(cd "$(dirname "$DECK")" && pwd)
DECK_BASE=$(basename "$DECK")
mkdir -p "$DECK_DIR/$OUT"

# ngspice reads .spiceinit from the current directory
SELF_DIR=$(cd "$(dirname "$0")" && pwd)
cp -n "$SELF_DIR/.spiceinit" "$DECK_DIR/$OUT/" 2>/dev/null || true

FAIL=0
for corner in tt ss ff; do
  for temp in -40 27 125; do
    tag="${corner}_${temp}C"
    # ngspice does not expand $PDK_ROOT in .lib lines -- substitute it
    # here along with the corner and the temperature.
    sed -e "s/\(sky130\.lib\.spice\) tt/\1 ${corner}/" \
        -e "s|\$PDK_ROOT|${PDK_ROOT}|g" \
        -e "1a .temp ${temp}" \
        "$DECK_DIR/$DECK_BASE" > "$DECK_DIR/$OUT/deck_${tag}.spice"

    printf '=== %-10s ' "$tag"
    if ( cd "$DECK_DIR/$OUT" && ngspice -b "deck_${tag}.spice" \
           > "log_${tag}.txt" 2>&1 ); then
      printf 'ok\n'
    else
      printf 'NGSPICE FAILED\n'; FAIL=1
    fi
    grep -i -E '^[a-z_]+ *=' "$DECK_DIR/$OUT/log_${tag}.txt" | head -8 \
      | sed 's/^/    /' || true
  done
done

echo
echo "logs in $DECK_DIR/$OUT/"
exit "$FAIL"
