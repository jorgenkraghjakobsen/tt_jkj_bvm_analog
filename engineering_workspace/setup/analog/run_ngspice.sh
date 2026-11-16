#!/usr/bin/env bash
# ============================================================
# setup/analog/run_ngspice.sh <deck.spice> [ngspice args...]
#
# ngspice does NOT expand environment variables inside .lib or
# .include lines -- it passes "$PDK_ROOT" through as a literal path and
# fails. The decks keep $PDK_ROOT as a readable placeholder; this script
# substitutes the real value into a temporary copy placed BESIDE the
# deck, so every relative .include still resolves, runs ngspice there,
# and cleans up.
#
#   export PDK_ROOT=$HOME/.ciel/ciel/sky130/versions/<hash>
#   setup/analog/run_ngspice.sh analog/bandgap/spice/tb_sc_ideal.spice
# ============================================================
set -u

DECK="${1:?usage: run_ngspice.sh <deck.spice> [ngspice args...]}"
shift || true

if [ -z "${PDK_ROOT:-}" ]; then
    echo "PDK_ROOT is not set." >&2
    echo "  export PDK_ROOT=\$HOME/.ciel/ciel/sky130/versions/<hash>" >&2
    exit 1
fi

LIB="$PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice"
if [ ! -f "$LIB" ]; then
    echo "PDK model library not found:" >&2
    echo "  $LIB" >&2
    echo "PDK_ROOT must be the directory that CONTAINS sky130A." >&2
    echo "Find it with:  find ~/.ciel -maxdepth 5 -type d -name sky130A" >&2
    exit 1
fi

[ -f "$DECK" ] || { echo "no such deck: $DECK" >&2; exit 1; }

DIR=$(cd "$(dirname "$DECK")" && pwd)
BASE=$(basename "$DECK")
TMP=".run_${BASE}"

SELF=$(cd "$(dirname "$0")" && pwd)
cp -n "$SELF/.spiceinit" "$DIR/" 2>/dev/null || true

sed "s|\$PDK_ROOT|$PDK_ROOT|g" "$DIR/$BASE" > "$DIR/$TMP"
trap 'rm -f "$DIR/$TMP"' EXIT

( cd "$DIR" && ngspice "$@" "$TMP" )
