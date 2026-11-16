# layout/

The `.mag` files are NOT stored here. They are produced by the
generators in `../scripts/`, and the authoritative copies live in the
working WSL2 tree where magic runs.

Regenerate from this directory's parent (`analog/bandgap`):

    python3 scripts/gen_mim_mag.py    layout/mim_array.mag
    python3 scripts/gen_ota_pair.py   layout/ota_pair.mag
    python3 scripts/gen_mirror_load.py layout/mirror_load.mag

`gen_ota_devices.tcl` produces the device and unit cells; pipe it into
magic on stdin (magic treats a trailing .tcl argument as a cell name to
load and hangs).

`nwell_ring.mag` comes from the PDK generator, not from a script:

    magic -dnull -noconsole <<'EOF'
    load unit_p10_l1          # switches tech to sky130A -- REQUIRED
    load nwell_ring
    box -224 -750 806 750     # LAMBDA, = internal -448..1612 x +/-1500
    sky130::nwell_draw
    save nwell_ring
    quit
    EOF
