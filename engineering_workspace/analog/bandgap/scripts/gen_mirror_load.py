#!/usr/bin/env python3
"""PMOS mirror load for the bandgap OTA.

Four unit_p10_l1 in a common-centroid A B B A row at pitch 388 (wells
abut and merge: nwell.2a is `touching_ok`), inside an nwell_ring that
satisfies nwell.4 ("all nwells must contain metal-connected N+ taps").

Like the nfet, unit_p10_l1's gate rail claims met1 across both ends
(x -96..96 at y +/-(1041..1087)), coming within 10 units of the
terminal strips at x +/-(106..152).  So again: no parent met1 routing,
only local 90x90 widenings for via enclosure.

Only FOUR nets here -- the gates are common -- and the crowded
neighbours are same-net (source beside source, the two B drains beside
each other), so those merge into plates instead of needing spaced
stubs.  That is what makes a 388 pitch routable at all.

  net   terminals            escape                  bus
  vdd   4 sources + tap ring via1+via2, met3 down     met3 plate y -1560..-555
  pg    4 gates (bot rail)   via1, met2               met2 bus   y -1160..-1060
  n1a   2 A drains           via1, met2 up            met2 bus   y  1250..1350
  n1    2 B drains           via1+via2, met3 up       met3 plate y   555..1450

Magic scale notes, both learned the hard way:
  * .mag files are INTERNAL units, 1 unit = 0.005 um.
  * magic's `box` command takes LAMBDA = 2 internal units, so any box
    argument is half the number you see in the file.
  * magic paints a contact as cut + enclosure, so a painted via must be
    >= cut + 2*enclosure (via1 52, via2 56, via3 64).
"""

import collections, itertools, sys

CHILD, RING = "unit_p10_l1", "nwell_ring"
PITCH = 388
PAT   = ["A", "B", "B", "A"]
BB_HW, BB_HH = 194, 1100
RING_BB = (-501, -1553, 1665, 1553)

TERM_DX, TERM_HW, GATE_HW = 129, 23, 96
RAIL_LO, RAIL_HI = 1041, 1087          # gate rail band, both signs
PAD1, V1, V2 = 45, 30, 30
YV   = 600                              # drain/source via y
GVC  = -1100                            # gate via centre (bottom rail)
GW   = (-1160, -1041)                   # gate met1 widening

B_M2_PG  = (-1160, -1060)
B_M3_VDD = (-1545,  -555)
B_M2_N1A = ( 1250,  1350)
B_M3_N1  = (  555,  1450)

RING_YC   = -1500                       # bottom ring centre line
RING_LI   = (-1517, -1483)              # ring contact band (34 tall)
TAPX      = [200, 582, 964]

cx       = lambda k: PITCH * k
mirrored = lambda k: k % 2 == 1

def term_x(k, which):
    off = -TERM_DX if which == "D" else TERM_DX
    return cx(k) + (-off if mirrored(k) else off)

L = collections.defaultdict(list)
def rect(lay, x1, y1, x2, y2):
    assert x2 > x1 and y2 > y1, (lay, x1, y1, x2, y2)
    L[lay].append((x1, y1, x2, y2))
def pad(lay, xc, yc, hw, hh): rect(lay, xc-hw, yc-hh, xc+hw, yc+hh)

src   = [term_x(k, "S") for k in range(len(PAT))]
drn_A = [term_x(k, "D") for k, g in enumerate(PAT) if g == "A"]
drn_B = [term_x(k, "D") for k, g in enumerate(PAT) if g == "B"]
gat   = [cx(k) for k in range(len(PAT))]
cent  = lambda xs: sum(xs) / len(xs)

cen = {"A drains": cent(drn_A), "B drains": cent(drn_B), "gates": cent(gat),
       "A srcs": cent([term_x(k,"S") for k,g in enumerate(PAT) if g=="A"]),
       "B srcs": cent([term_x(k,"S") for k,g in enumerate(PAT) if g=="B"])}
for a, b in itertools.combinations(cen.values(), 2):
    assert abs(a - b) < 1e-9, cen

# ---- vdd: sources down to a met3 plate -------------------------------
for x in src:
    pad("metal1", x, -YV, PAD1, PAD1)
    pad("via1",   x, -YV, V1,   V1)
    pad("metal2", x, -YV, PAD1, PAD1)
    pad("via2",   x, -YV, V2,   V2)
# ---- vdd: well-tap stacks onto the ring's bottom segment -------------
for x in TAPX:
    rect("locali", x-PAD1, RING_LI[0], x+PAD1, RING_LI[1])
    rect("viali",  x-PAD1, RING_LI[0], x+PAD1, RING_LI[1])
    pad("metal1",  x, RING_YC, PAD1, PAD1)
    pad("via1",    x, RING_YC, V1,   V1)
    pad("metal2",  x, RING_YC, PAD1, PAD1)
    pad("via2",    x, RING_YC, V2,   V2)
rect("metal3", min(src)-PAD1, B_M3_VDD[0], max(src)+PAD1, B_M3_VDD[1])

# ---- pg: gates on the bottom rail ------------------------------------
for x in gat:
    rect("metal1", x-PAD1, GW[0], x+PAD1, GW[1])
    pad("via1",    x, GVC, V1, V1)
rect("metal2", min(gat)-PAD1, B_M2_PG[0], max(gat)+PAD1, B_M2_PG[1])

# ---- n1a: A drains up on met2 ----------------------------------------
for x in drn_A:
    pad("metal1", x, YV, PAD1, PAD1)
    pad("via1",   x, YV, V1,   V1)
    rect("metal2", x-PAD1, YV-PAD1, x+PAD1, B_M2_N1A[1])
rect("metal2", min(drn_A)-PAD1, B_M2_N1A[0], max(drn_A)+PAD1, B_M2_N1A[1])

# ---- n1: B drains up on met3 (one plate, same net, 130 apart) --------
for x in drn_B:
    pad("metal1", x, YV, PAD1, PAD1)
    pad("via1",   x, YV, V1,   V1)
    pad("metal2", x, YV, PAD1, PAD1)
    pad("via2",   x, YV, V2,   V2)
rect("metal3", min(drn_B)-PAD1, B_M3_N1[0], max(drn_B)+PAD1, B_M3_N1[1])

ports = [("vdd", "metal3", (cent(src),   -1000)),
         ("pg",  "metal2", (cent(gat),   sum(B_M2_PG)//2)),
         ("n1a", "metal2", (cent(drn_A), sum(B_M2_N1A)//2)),
         ("n1",  "metal3", (cent(drn_B), 1400))]

# ---- checks -----------------------------------------------------------
MINW = {"metal1":28,"metal2":28,"metal3":60,"metal4":60,
        "via1":52,"via2":56,"via3":64,"viali":34,"locali":34}
for lay, rs in L.items():
    for r in rs:
        w = min(r[2]-r[0], r[3]-r[1])
        assert w >= MINW[lay], f"{lay} width {w} < {MINW[lay]} at {r}"

for (x1, y1, x2, y2) in L["metal1"]:
    for k in range(len(PAT)):
        gl, gr = cx(k)-GATE_HW, cx(k)+GATE_HW
        for s in (1, -1):
            ry1, ry2 = (RAIL_LO, RAIL_HI) if s > 0 else (-RAIL_HI, -RAIL_LO)
            if y2 <= ry1 or y1 >= ry2: continue
            dx = max(gl-x2, x1-gr, 0)
            if dx < 28 and abs((x1+x2)/2 - cx(k)) > 1e-9:
                raise AssertionError(f"met1 {(x1,y1,x2,y2)} {dx} from rail {k}")
    hits = [(k,w) for k in range(len(PAT)) for w in ("D","S")
            if x1 < term_x(k,w)+TERM_HW and x2 > term_x(k,w)-TERM_HW
            and y1 < 1000 and y2 > -1000]
    assert len(hits) <= 1, f"met1 {(x1,y1,x2,y2)} bridges {hits}"

MIN = {"metal1":28,"metal2":28,"metal3":60,"metal4":60,
       "via1":34,"via2":40,"via3":40,"viali":34,"locali":34}
chk = {k: list(v) for k, v in L.items()}
for k in range(len(PAT)):
    for (x1,y1,x2,y2) in ((-152,-1000,-106,1000), (106,-1000,152,1000),
                          (-96,RAIL_LO,96,RAIL_HI), (-96,-RAIL_HI,96,-RAIL_LO)):
        chk["metal1"].append((x1+PITCH*k, y1, x2+PITCH*k, y2))
viol = 0
for lay, rs in chk.items():
    for a, b in itertools.combinations(rs, 2):
        dx = max(b[0]-a[2], a[0]-b[2], 0); dy = max(b[1]-a[3], a[1]-b[3], 0)
        if dx == 0 and dy == 0: continue
        g = (dx*dx + dy*dy) ** 0.5
        if g < MIN[lay]:
            print(f"  SPACING {lay}: {g:.1f} < {MIN[lay]}  {a} {b}"); viol += 1
assert viol == 0, f"{viol} spacing violations"

# ---- write ------------------------------------------------------------
out = ["magic", "tech sky130A", "magscale 1 2", "timestamp 0"]
for k, grp in enumerate(PAT):
    a, c = (-1 if mirrored(k) else 1), cx(k)
    out += [f"use {CHILD} u_{grp}_k{k}", "timestamp 0",
            f"transform {a} 0 {c} 0 1 0",
            f"box {c-BB_HW} {-BB_HH} {c+BB_HW} {BB_HH}"]
out += [f"use {RING} u_ring", "timestamp 0", "transform 1 0 0 0 1 0",
        f"box {RING_BB[0]} {RING_BB[1]} {RING_BB[2]} {RING_BB[3]}"]
for lay in ("locali","viali","metal1","via1","metal2","via2","metal3"):
    if L[lay]:
        out.append(f"<< {lay} >>")
        out += [f"rect {r[0]} {r[1]} {r[2]} {r[3]}" for r in L[lay]]
out.append("<< labels >>")
for i, (nm, lay, (px, py)) in enumerate(ports, 1):
    out += [f"rlabel {lay} {int(round(px))} {py} {int(round(px))} {py} 0 {nm}",
            f"port {i} nsew"]
out.append("<< end >>")

path = sys.argv[1] if len(sys.argv) > 1 else "mirror_load.mag"
open(path, "w").write("\n".join(out) + "\n")

print(f"wrote {path}  ({len(out)} lines)")
print(f"  instances {len(PAT)} x {CHILD} + 1 x {RING}  pitch {PITCH}")
print("  centroids:", "  ".join(f"{k}={v:.1f}" for k, v in cen.items()))
print(f"  vdd srcs {src}   taps {TAPX}")
print(f"  pg  gates {gat}")
print(f"  n1a {drn_A}\n  n1  {drn_B}")
for lay in ("locali","viali","metal1","via1","metal2","via2","metal3"):
    if L[lay]: print(f"  {lay:<8} {len(L[lay]):3d} rects")
allr = [r for v in L.values() for r in v]
print(f"  routing bbox x {min(r[0] for r in allr)}..{max(r[2] for r in allr)}"
      f"  y {min(r[1] for r in allr)}..{max(r[3] for r in allr)}")
print(f"  ring bbox    x {RING_BB[0]}..{RING_BB[2]}  y {RING_BB[1]}..{RING_BB[3]}")
print("  all geometry + width + spacing checks passed")
