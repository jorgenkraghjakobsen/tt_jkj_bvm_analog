#!/usr/bin/env python3
"""Interdigitated NMOS input pair for the bandgap OTA.

Eight unit_n10_l4 in a common-centroid A B B A A B B A row, odd
positions mirrored about x.

No parent-level met1 ROUTING: unit_n10_l4's gate rail spans
x -396..+396 at y 1032..1078 and again at -1078..-1032, coming within
10 units (0.05 um) of the drain/source strips at x +/-(406..452).
met1 therefore cannot leave the cell vertically; every net escapes on
met2 or above.  met1 appears only as 24 local 90x90 widenings that
merge with their own terminal, because a 0.15 um via1 cannot meet its
0.055 um enclosure on a 46-unit strip.

  net     terminals                escape                   bus
  ntail   8 sources                via1+via2, met3 down     met3 y -1450..-1350
  vinn    4 A gates (bottom rail)  via1, met2               met2 y -1150..-1050
  n1a     4 A drains               via1, met2 up            met2 y  1250.. 1350
  vinp    4 B gates (top rail)     via1+via2, met3          met3 y  1050.. 1150
  n1      4 B drains               via1+via2+via3, met4 up  met4 y  1500.. 1600

Three nets go up and two go down, so met4 is unavoidable for a
five-net single-row array with met1 blocked.  Using each gate's
*unused* rail (A gates on the bottom, B gates on the top) holds it
to three.  NOTE for top level: this block uses met4 internally, so it
must not be placed under the ua[2..7] pin locations.

Result: DRC 0, .subckt ota_pair ntail n1a n1 vinn vinp, 43.24 x 15.25 um.

1 internal unit = 0.005 um; file carries `magscale 1 2`.
"""

import collections, itertools, sys

CHILD = "unit_n10_l4"
PITCH = 1100
PAT   = ["A", "B", "B", "A", "A", "B", "B", "A"]
BB_HW, BB_HH = 458, 1088
TERM_DX, TERM_HW, GATE_HW = 429, 23, 396
PAD1, PAD3 = 45, 60
# magic paints a contact as cut + enclosure, so the PAINTED area must be
# >= cut + 2*enclosure (magic insets the real GDS cut itself):
#   via1 >= 0.26 um (via.1a  + 2*via.4a)  = 52 units
#   via2 >= 0.28 um (via2.1a + 2*via2.4)  = 56 units
#   via3 >= 0.32 um (via3.1  + 2*via3.4)  = 64 units
V1, V2, V3 = 30, 30, 35
YV = 600
B_M2_VINN  = (-1150, -1050)
B_M3_NTAIL = (-1450, -1350)
B_M2_N1A   = ( 1250,  1350)
B_M3_VINP  = ( 1050,  1150)
B_M4_N1    = ( 1500,  1600)
GW_LO, GW_HI = 1032, 1150
GVC = 1100

cx       = lambda k: PITCH * k
mirrored = lambda k: k % 2 == 1

def term_x(k, which):
    off = -TERM_DX if which == "D" else TERM_DX
    return cx(k) + (-off if mirrored(k) else off)

L = collections.defaultdict(list)
def rect(lay, x1, y1, x2, y2):
    assert x2 > x1 and y2 > y1, (lay, x1, y1, x2, y2)
    L[lay].append((x1, y1, x2, y2))
def pad(lay, xc, yc, hw, hh):   rect(lay, xc-hw, yc-hh, xc+hw, yc+hh)
def vstub(lay, xc, y1, y2):     rect(lay, xc-PAD1, y1, xc+PAD1, y2)
def hbus(lay, x1, x2, b):       rect(lay, x1, b[0], x2, b[1])

src   = [term_x(k, "S") for k in range(len(PAT))]
drn_A = [term_x(k, "D") for k, g in enumerate(PAT) if g == "A"]
drn_B = [term_x(k, "D") for k, g in enumerate(PAT) if g == "B"]
gat_A = [cx(k) for k, g in enumerate(PAT) if g == "A"]
gat_B = [cx(k) for k, g in enumerate(PAT) if g == "B"]
cent  = lambda xs: sum(xs) / len(xs)

cen = {"A drains": cent(drn_A), "B drains": cent(drn_B),
       "A gates":  cent(gat_A), "B gates":  cent(gat_B),
       "A srcs":   cent([term_x(k,"S") for k,g in enumerate(PAT) if g=="A"]),
       "B srcs":   cent([term_x(k,"S") for k,g in enumerate(PAT) if g=="B"])}
assert abs(cen["A drains"] - cen["B drains"]) < 1e-9, cen
assert abs(cen["A gates"]  - cen["B gates"])  < 1e-9, cen
assert abs(cen["A srcs"]   - cen["B srcs"])   < 1e-9, cen

for x in src:                                     # ntail
    pad("metal1", x, -YV, PAD1, PAD1)
    pad("via1",   x, -YV, V1,   V1)
    pad("metal2", x, -YV, PAD1, PAD1)
    pad("via2",   x, -YV, V2,   V2)
    vstub("metal3", x, B_M3_NTAIL[0], -YV + PAD1)
hbus("metal3", min(src)-PAD1, max(src)+PAD1, B_M3_NTAIL)

for x in drn_A:                                   # n1a
    pad("metal1", x, YV, PAD1, PAD1)
    pad("via1",   x, YV, V1,   V1)
    vstub("metal2", x, YV-PAD1, B_M2_N1A[1])
hbus("metal2", min(drn_A)-PAD1, max(drn_A)+PAD1, B_M2_N1A)

for x in drn_B:                                   # n1
    pad("metal1", x, YV, PAD1, PAD1)
    pad("via1",   x, YV, V1,   V1)
    pad("metal2", x, YV, PAD1, PAD1)
    pad("via2",   x, YV, V2,   V2)
    pad("metal3", x, YV, PAD3, PAD3)              # 120x120: met3 min area
    pad("via3",   x, YV, V3,   V3)
    vstub("metal4", x, YV-PAD1, B_M4_N1[1])
hbus("metal4", min(drn_B)-PAD1, max(drn_B)+PAD1, B_M4_N1)

for x in gat_A:                                   # vinn, bottom rail
    rect("metal1", x-PAD1, -GW_HI, x+PAD1, -GW_LO)
    pad("via1",    x, -GVC, V1, V1)
hbus("metal2", min(gat_A)-PAD1, max(gat_A)+PAD1, B_M2_VINN)

for x in gat_B:                                   # vinp, top rail
    rect("metal1", x-PAD1, GW_LO, x+PAD1, GW_HI)
    pad("via1",    x, GVC, V1, V1)
    rect("metal2", x-PAD1, B_M3_VINP[0], x+PAD1, B_M3_VINP[1])
    pad("via2",    x, GVC, V2, V2)
hbus("metal3", min(gat_B)-PAD3, max(gat_B)+PAD3, B_M3_VINP)

ports = [("ntail","metal3",(cent(src),   sum(B_M3_NTAIL)//2)),
         ("n1a",  "metal2",(cent(drn_A), sum(B_M2_N1A)  //2)),
         ("n1",   "metal4",(cent(drn_B), sum(B_M4_N1)   //2)),
         ("vinn", "metal2",(cent(gat_A), sum(B_M2_VINN) //2)),
         ("vinp", "metal3",(cent(gat_B), sum(B_M3_VINP) //2))]

# --- checks: no parent met1 near a foreign gate rail or terminal strip ---
for (x1, y1, x2, y2) in L["metal1"]:
    for k in range(len(PAT)):
        gl, gr = cx(k)-GATE_HW, cx(k)+GATE_HW
        for (ry1, ry2) in ((-1078,-1032), (1032,1078)):
            if y2 <= ry1 or y1 >= ry2: continue
            dx = max(gl-x2, x1-gr, 0)
            if dx < 28 and abs((x1+x2)/2 - cx(k)) > 1e-9:
                raise AssertionError(f"met1 {(x1,y1,x2,y2)} {dx} from rail {k}")
    hits = [(k,w) for k in range(len(PAT)) for w in ("D","S")
            if x1 < term_x(k,w)+TERM_HW and x2 > term_x(k,w)-TERM_HW
            and y1 < 1000 and y2 > -1000]
    assert len(hits) <= 1, f"met1 {(x1,y1,x2,y2)} bridges {hits}"

MINW = {"metal1":28,"metal2":28,"metal3":60,"metal4":60,
        "via1":52,"via2":56,"via3":64}
for _lay, _rs in L.items():
    for _r in _rs:
        _w = min(_r[2]-_r[0], _r[3]-_r[1])
        assert _w >= MINW[_lay], f"{_lay} width {_w} < {MINW[_lay]} at {_r}"
MIN = {"metal1":28,"metal2":28,"metal3":60,"metal4":60,
       "via1":34,"via2":40,"via3":40}
chk = {k: list(v) for k, v in L.items()}
for k in range(len(PAT)):                         # add child met1 footprint
    for (x1,y1,x2,y2) in ((-452,-1000,-406,1000),(406,-1000,452,1000),
                          (-396,1032,396,1078),(-396,-1078,396,-1032)):
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

out = ["magic", "tech sky130A", "magscale 1 2", "timestamp 0"]
for k, grp in enumerate(PAT):
    a, c = (-1 if mirrored(k) else 1), cx(k)
    out += [f"use {CHILD} u_{grp}_k{k}", "timestamp 0",
            f"transform {a} 0 {c} 0 1 0",
            f"box {c-BB_HW} {-BB_HH} {c+BB_HW} {BB_HH}"]
for lay in ("metal1","via1","metal2","via2","metal3","via3","metal4"):
    if L[lay]:
        out.append(f"<< {lay} >>")
        out += [f"rect {r[0]} {r[1]} {r[2]} {r[3]}" for r in L[lay]]
out.append("<< labels >>")
for _i, (nm, lay, (px, py)) in enumerate(ports, 1):
    px = int(round(px))
    out.append(f"rlabel {lay} {px} {py} {px} {py} 0 {nm}")
    out.append(f"port {_i} nsew")
out.append("<< end >>")

path = sys.argv[1] if len(sys.argv) > 1 else "ota_pair.mag"
open(path, "w").write("\n".join(out) + "\n")

print(f"wrote {path}  ({len(out)} lines)")
print(f"  instances {len(PAT)}  pattern {' '.join(PAT)}  pitch {PITCH}")
print("  centroids:", "  ".join(f"{k}={v:.1f}" for k, v in cen.items()))
print(f"  ntail {src}")
print(f"  n1a   {drn_A}\n  n1    {drn_B}")
print(f"  vinn  {gat_A}\n  vinp  {gat_B}")
for lay in ("metal1","via1","metal2","via2","metal3","via3","metal4"):
    if L[lay]: print(f"  {lay:<8} {len(L[lay]):3d} rects")
allr = [r for v in L.values() for r in v]
print(f"  routing bbox x {min(r[0] for r in allr)}..{max(r[2] for r in allr)}"
      f"  y {min(r[1] for r in allr)}..{max(r[3] for r in allr)}")
print("  all geometry + width + spacing checks passed")
