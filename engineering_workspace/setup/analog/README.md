# setup/analog

Shared analog setup: xschem configuration, the corner runner and the
layout tool entry points.

| file | what |
|---|---|
| `xschemrc` | sources the PDK xschemrc, then adds every project block to `XSCHEM_LIBRARY_PATH` so blocks can instance each other |
| `.spiceinit` | `ngbehavior=hsa` and `ng_nomodcheck`; sky130 models will not parse without it |
| `run_corners.sh` | runs any deck across tt/ss/ff and −40/27/125 °C |

## Layout tools

Magic must be started with the PDK rc file or it opens with the wrong
technology and every DRC result is meaningless:

```bash
magic -rcfile $PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc -d XR
```

`-d XR` forces the X11 renderer. Magic's OpenGL backend is unreliable
under WSLg and typically gives a black canvas.

KLayout:

```bash
klayout -e -nn $PDK_ROOT/sky130A/libs.tech/klayout/tech/sky130A.lyt
```

## LVS

```bash
netgen -batch lvs "<block>_lvs.spice <block>" \
                  "<block>.spice <block>" \
                  $PDK_ROOT/sky130A/libs.tech/netgen/sky130A_setup.tcl \
                  lvs.log
```

Read `lvs.log` from the bottom. "Circuits match uniquely" is the goal.
Pin mismatches are usually a label on the wrong layer; device-count
mismatches are usually a missing tap or a shorted net.

## PDK_ROOT

Everything here needs it set:

```bash
export PDK_ROOT=$HOME/.ciel/ciel/sky130/versions/<hash>
```
