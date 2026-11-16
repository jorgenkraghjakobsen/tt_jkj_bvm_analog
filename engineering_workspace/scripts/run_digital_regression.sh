#!/usr/bin/env bash
# ============================================================
# Run every digital block's cocotb regression, in dependency order.
#
#   scripts/run_digital_regression.sh
#   scripts/run_digital_regression.sh WAVES=1
# ============================================================
set -u

WS=$(cd "$(dirname "$0")/.." && pwd)
EXTRA="$*"
FAIL=0

SPECS=(
  "digital/spi_slave/tb|spi_slave|"
  "digital/pwm/tb|pwm|"
  "digital/dig_top/tb|bg_seq phases|TEST=test_bg_seq"
  "digital/dig_top/tb|bg_seq Step 6 boundary rules|TEST=test_bg_seq_rules"
  "digital/dig_top/tb|dig_top integration + bring-up|TEST=test_dig_top"
)

for spec in "${SPECS[@]}"; do
    IFS='|' read -r dir label extra <<< "$spec"
    printf '\n\033[1;34m===== %s =====\033[0m\n' "$label"
    ( cd "$WS/$dir" && make -s clean >/dev/null 2>&1 ) || true
    if ( cd "$WS/$dir" && make $extra $EXTRA ); then
        printf '\033[0;32mPASS\033[0m  %s\n' "$label"
    else
        printf '\033[0;31mFAIL\033[0m  %s\n' "$label"
        FAIL=1
    fi
done

for d in digital/spi_slave/tb digital/pwm/tb digital/dig_top/tb; do
    ( cd "$WS/$d" && make -s clean >/dev/null 2>&1 ) || true
done

echo
if [ "$FAIL" -eq 0 ]; then
    printf '\033[0;32mAll digital blocks passed.\033[0m\n'
else
    printf '\033[0;31mAt least one block failed.\033[0m\n'
fi
exit "$FAIL"
