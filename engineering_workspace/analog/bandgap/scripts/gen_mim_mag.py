#!/usr/bin/env python3
"""Write the bandgap MIM array as a Magic .mag file.

    python3 analog/bandgap/scripts/gen_mim_mag.py

WHY NOT A MAGIC TCL SCRIPT
A first attempt drove magic with getcell/identify in -dnull mode and
placed nothing: with no window there is no box context, and magic
reported "the box is in cell mimcap_unit, not in the edit cell
mim_array" a hundred times while the array came out as 0 0 1 1.
The .mag format is plain text and fully determined, so writing it
directly removes magic's interactive semantics from the problem.
Magic only has to READ the result.

GEOMETRY FACTS, all read out of the generated mimcap_unit.mag rather
than assumed:
    magscale 1 2                       must match, or coordinates
                                       are reinterpreted
    200 internal units = 1 um          capm spans 1000 units = 5.0 um
    FIXED_BBOX -716 -540 364 540       the abutment box
    capm x -676..324                   centre at -176 units = -0.88 um,
                                       NOT the cell origin
    ports: C1 top plate (mimcapcontact, x -176)
           C2 bottom plate (via3, x 664) -- both reach met4
"""
import os, sys

UM        = 200          # internal units per micron
MAGSCALE  = "1 2"
CHILD     = "mimcap_unit"
CAPM_DX   = -176         # capm centre in child coords, internal units
BBOX      = (-716, -540, 364, 540)      # FIXED_BBOX of the child

CSV = "analog/bandgap/doc/mim_placement.csv"
OUT = "analog/bandgap/layout/mim_array.mag"

def main():
    if not os.path.exists(CSV):
        sys.exit(f"missing {CSV} -- run: mim_array.py --coords > {CSV}")

    rows = []
    for line in open(CSV):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("group,"):
            continue
        g, r, c, i, j, x, y = line.split(",")
        rows.append((g, r, c, float(x), float(y)))

    body, n = [], 0
    xs, ys = [], []
    for g, r, c, x_um, y_um in rows:
        # land the CAPM CENTRE on (x_um, y_um): the cell origin must go
        # to x_um - capm_offset, because capm sits left of the origin.
        dx = round(x_um * UM) - CAPM_DX
        dy = round(y_um * UM)
        if dx != int(dx) or dy != int(dy):
            sys.exit(f"non-integer placement at {x_um},{y_um}")
        name = f"ring_{n}" if r == "" else f"u_{g}_r{r}c{c}"
        bx = (BBOX[0] + dx, BBOX[1] + dy, BBOX[2] + dx, BBOX[3] + dy)
        xs += [bx[0], bx[2]]
        ys += [bx[1], bx[3]]
        body.append(f"use {CHILD}  {name}\n"
                    f"timestamp 0\n"
                    f"transform 1 0 {dx} 0 1 {dy}\n"
                    f"box {bx[0]} {bx[1]} {bx[2]} {bx[3]}")
        n += 1

    # ---- C1 vertical straps -----------------------------------
    # EVERY non-dummy cell shares one top-plate net: C_A, C_B, C_F and
    # all four trim groups tie their C1 to the OTA summing node. Only
    # the BOTTOM plates differ by group, so C1 is a single net over 55
    # cells, not seven nets.
    #
    # Top plates take the summing node and bottom plates the driven
    # switches, never the reverse: met3 carries the larger parasitic
    # to substrate and that belongs on the low-impedance side.
    #
    # Cell (i,j) C1 met4 in array coords:
    #     x [1700i+389, 1700i+1311]   y [1340j+209, 1340j+1131]
    # Vertically adjacent C1s are 418 units (2.09 um) apart with the
    # SAME x extent, so a strap of identical width joins them without
    # changing any horizontal gap -- which is why this cannot break
    # the spacing that already passed DRC.
    #
    # Horizontally, cell i's C2 contact sits at x [1700i+1642,
    # 1700i+1738], squarely between the two C1s, so columns cannot be
    # joined directly. They need a spine in a row channel. NOT YET
    # DRAWN -- the columns are currently 10 isolated combs.
    core, allc = {}, {}
    for g, r, c, x_um, y_um in rows:
        if r == "":
            continue
        core[(int(c) + 1, 8 - int(r))] = g        # ring coords (i,j)
    # Every cell, with ring and dummy folded into one VSS net. The
    # ring is a closed loop so it is 4-connected on its own, and eight
    # of the nine dummies sit against it -- only the interior dummy at
    # (2,4) needs a route of its own.
    for i in range(10):
        for j in range(10):
            if i in (0, 9) or j in (0, 9):
                allc[(i, j)] = "VSS"
    for (i, j), g in core.items():
        allc[(i, j)] = "VSS" if g == "d" else g

    straps = []
    for (i, j), g in sorted(core.items()):
        if g == "d":
            continue
        above = core.get((i, j + 1))
        if above is None or above == "d":
            continue
        x0, x1 = 1700 * i + 389, 1700 * i + 1311
        y0, y1 = 1340 * j + 1131, 1340 * (j + 1) + 209
        straps.append(f"rect {x0} {y0} {x1} {y1}")

    # ---- C1 horizontal spines ---------------------------------
    # The 46 straps give 9 isolated combs. Spines join them, each
    # placed in a channel where every column it spans HAS a strap, so
    # overlapping met4 on the same net does the joining with no stubs.
    #
    # Each spine must also thread between two rows of C2 contacts.
    # C2 met4 spans y [1340j+142, 1340j+1198], leaving a 284-unit
    # (1.42 um) clear band. met4 spacing is 0.3 um = 60 units; CLEAR
    # = 82 gives 0.41 um each side.
    #
    # TWO are needed, not one. Column i=2 has a dummy at j=4 which
    # splits it into an upper comb (j 5..8) and a lower comb (j 1..3).
    # The j5/j6 spine reaches only the upper one -- extraction caught
    # this: 52 caps merged and a 3-cap comb left orphaned.
    #   spine A  j5/j6, columns 1..8  -- the only channel where all
    #                                   eight columns have a strap
    #   spine B  j2/j3, columns 2..7  -- i=1 and i=8 have a dummy at
    #                                   j=2, so they are excluded;
    #                                   i=2 is the orphan and i=3..7
    #                                   are already on the main net
    CLEAR = 82
    spines = [(5, 6, 1, 8), (2, 3, 2, 7)]
    spine_info = []
    for (j_lo, j_hi, i_from, i_to) in spines:
        for col in range(i_from, i_to + 1):
            for jj in (j_lo, j_hi):
                g = core.get((col, jj))
                if g is None or g == "d":
                    sys.exit(f"spine j={j_lo}/{j_hi}: column {col} has "
                             f"no strap at j={jj} (cell is {g})")
        sy0 = 1340 * j_lo + 1198 + CLEAR
        sy1 = 1340 * j_hi + 142  - CLEAR
        sx0 = 1700 * i_from + 389
        sx1 = 1700 * i_to + 1311
        straps.append(f"rect {sx0} {sy0} {sx1} {sy1}")
        spine_info.append((j_lo, j_hi, i_from, i_to, sy0, sy1))

    # ---- C2 escapes to met2 -----------------------------------
    # Each cell drops its bottom plate to met2 through a via2, and C2
    # then routes on met2, which is completely empty in this array --
    # the MIM cap uses met3, capm and met4 only.
    #
    # The via2 CANNOT go under the capm: capm.8/via2.4 requires 0.1 um
    # between them, and a via2 under the plate measures zero. Probed
    # and confirmed. met3 runs to x=632 while capm stops at x=324, so
    # x 400..500 is over met3, 0.38 um clear of capm and 0.66 um clear
    # of the via3 at 632. Probe result: DRC 0, and extraction renamed
    # the C2 node to the met2 label -- one node through the via.
    #
    # met2 has no spacing relationship to the met3 bottom plates it
    # runs beneath, so wires cross freely under other cells.
    V2 = []     # via2 cuts
    M2 = []     # met2 pads and straps
    for (i, j), g in sorted(allc.items()):
        ox, oy = 1700 * i + 1026, 1340 * j + 670
        V2.append(f"rect {ox+400} {oy-40} {ox+500} {oy+40}")
        M2.append(f"rect {ox+350} {oy-90} {ox+550} {oy+90}")

    # vertical straps between vertically adjacent cells of the SAME
    # net -- the C2 analogue of the C1 straps. Conflict-free: same
    # column, same net, adjacent rows.
    c2_straps = 0
    for (i, j), g in sorted(allc.items()):
        above = allc.get((i, j + 1))
        if above is None or above != g:
            continue
        ox = 1700 * i + 1026
        M2.append(f"rect {ox+350} {1340*j+670+90} {ox+550} {1340*(j+1)+670-90}")
        c2_straps += 1

    # ---- C2 horizontal straps on met1 -------------------------
    # met1 is as empty as met2. A via1 at every cell takes the C2 net
    # up to met1 (probed: met1-via1-met2-via2-met3 is one node, DRC 0),
    # and horizontal straps there join horizontally adjacent same-net
    # cells. They cannot collide: a strap spans only the gap between
    # two NEIGHBOURS, so nothing of another net lies in between, and
    # the vertical straps are on met2 a layer away.
    #
    # Together the two directions give plain 4-connectivity on the
    # grid, which collapses B from 14 combs to ONE -- its periphery
    # ring is continuous all the way round.
    V1, M1 = [], []
    for (i, j), g in sorted(allc.items()):
        ox, oy = 1700 * i + 1026, 1340 * j + 670
        V1.append(f"rect {ox+400} {oy-40} {ox+500} {oy+40}")
        M1.append(f"rect {ox+350} {oy-90} {ox+550} {oy+90}")

    h_straps = 0
    for (i, j), g in sorted(allc.items()):
        right = allc.get((i + 1, j))
        if right is None or right != g:
            continue
        oy = 1340 * j + 670
        M1.append(f"rect {1700*i+1576} {oy-90} {1700*(i+1)+1376} {oy+90}")
        h_straps += 1

    # ---- final joins for the four split nets ------------------
    # met1 straps sit at pad-y, so every ROW gap is free on met1.
    # met2 straps sit at pad-x, so every COLUMN gap is free on met2.
    # That leaves a clean Manhattan grid: met1 highways running
    # horizontally through row gaps, met2 vertically through column
    # gaps, and the two never meet.
    #
    #   T8  met1, row gap above j=6   -- columns i=3 and i=6
    #   T2  met1, row gap j4/j5       -- its two cells straddle it
    #   F   met2, column gap i=4/i=5  -- both halves include i=4
    #   T4  met2, same gap, x track 200 units clear of F's
    PAD_X0, PAD_X1 = 1376, 1576       # pad x within a column
    def padx(i):  return (1700*i + PAD_X0, 1700*i + PAD_X1)
    def pady(j):  return (1340*j + 580,    1340*j + 760)

    # --- T8: met1 horizontal at y 9200..9320 (row gap j6/j7) ---
    ya, yb = 9200, 9320
    for i in (3, 6):
        x0, x1 = padx(i)
        M1.append(f"rect {x0} {pady(6)[1]} {x1} {yb}")
    M1.append(f"rect {padx(3)[0]} {ya} {padx(6)[1]} {yb}")

    # --- T2: met1 horizontal at y 6600..6720 (row gap j4/j5) ---
    ya, yb = 6600, 6720
    x0, x1 = padx(2)
    M1.append(f"rect {x0} {ya} {x1} {pady(5)[0]}")      # down from j=5
    x0, x1 = padx(7)
    M1.append(f"rect {x0} {pady(4)[1]} {x1} {yb}")      # up from j=4
    M1.append(f"rect {padx(2)[0]} {ya} {padx(7)[1]} {yb}")

    # --- F: met2 vertical at x 8500..8620 (column gap i4/i5) ---
    xa, xb = 8500, 8620
    for j in (3, 6):
        y0, y1 = pady(j)
        M2.append(f"rect {padx(4)[1]} {y0} {xb} {y1}")
    M2.append(f"rect {xa} {pady(3)[0]} {xb} {pady(6)[1]}")

    # --- T4: met2 vertical at x 8700..8820, 80 units clear of F --
    xa, xb = 8700, 8820
    for j in (2, 7):
        y0, y1 = pady(j)
        M2.append(f"rect {padx(4)[1]} {y0} {xb} {y1}")
    M2.append(f"rect {xa} {pady(2)[0]} {xb} {pady(7)[1]}")

    # --- VSS cells: short C1 to C2 so the dummy caps vanish -----
    # The cell already brings C2 up to met4 at x 616..712 through its
    # via3. A met4 strap from there across to the C1 region (which
    # ends at x 285) shorts the two plates of that unit together, so
    # the dummy contributes no capacitance and nothing floats. It
    # cannot reach the SUM net: there is no path out of the cell.
    for (i, j), g in sorted(allc.items()):
        if g != "VSS":
            continue
        ox, oy = 1700 * i + 1026, 1340 * j + 670
        straps.append(f"rect {ox+285} {oy-100} {ox+650} {oy+100}")

    # --- interior dummy (2,4): met2 down the i1/i2 column gap ---
    # the stub has to REACH the vertical track at x 3400..3520, not
    # stop 1056 units short of it -- which is what rev 1 did, leaving
    # this dummy as its own one-cell node.
    M2.append(f"rect 3400 {1340*4+580} {1700*2+1376} {1340*4+760}")
    M2.append(f"rect {1700*1+1576+124} {1340*0+670} "
              f"{1700*1+1576+244} {1340*4+760}")
    M2.append(f"rect {1700*1+1376} {1340*0+580} "
              f"{1700*1+1576+244} {1340*0+760}")

    # ---- port labels ------------------------------------------
    # Without these the nets are correct but anonymous, and LVS has
    # nothing to match against the schematic. Each label sits on the
    # met1 pad of a representative cell of its net; SUM goes on the
    # met4 spine. Same rlabel/port form the PDK uses in mimcap_unit.
    #
    # Net roles in the SC bandgap:
    #   SUM     all 55 top plates -> OTA summing node
    #   VBE     C_A bottom  -> V_BE sampling switches
    #   DVBE    C_B bottom  -> delta-V_BE sampling switches
    #   OTAOUT  C_F bottom  -> OTA output (the feedback cap)
    #   TRIM8/4/2/1         -> trim switches, added to C_B by code
    #   VSS     dummies and guard ring, plates shorted together
    def pad_centre(i, j):
        return (1700 * i + 1476, 1340 * j + 670)
    ports = [("SUM",    "metal4", (2500, 8040)),
             ("VBE",    "metal1", pad_centre(4, 5)),
             ("DVBE",   "metal1", pad_centre(2, 8)),
             ("OTAOUT", "metal1", pad_centre(4, 6)),
             ("TRIM8",  "metal1", pad_centre(3, 5)),
             ("TRIM4",  "metal1", pad_centre(4, 7)),
             ("TRIM2",  "metal1", pad_centre(2, 5)),
             ("TRIM1",  "metal1", pad_centre(7, 5)),
             ("VSS",    "metal1", pad_centre(0, 0))]
    # guard: every label must land on a cell of the net it names
    expect = {"VBE": "A", "DVBE": "B", "OTAOUT": "F", "TRIM8": "T8",
              "TRIM4": "T4", "TRIM2": "T2", "TRIM1": "T1", "VSS": "VSS"}
    for nm, lay, (lx, ly) in ports:
        if nm not in expect:
            continue
        i, j = (lx - 1476) // 1700, (ly - 670) // 1340
        got = allc.get((i, j))
        if got != expect[nm]:
            sys.exit(f"label {nm} at cell ({i},{j}) which is {got}, "
                     f"expected {expect[nm]}")
    labels = []
    for pn, (nm, lay, (lx, ly)) in enumerate(ports, start=1):
        labels.append(f"rlabel {lay} {lx} {ly} {lx} {ly} 0 {nm}")
        labels.append(f"port {pn} nsew")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write("magic\ntech sky130A\n")
        f.write(f"magscale {MAGSCALE}\n")
        f.write("timestamp 0\n")
        if straps:
            f.write("<< metal4 >>\n")
            f.write("\n".join(straps) + "\n")
        if M2:
            f.write("<< metal2 >>\n")
            f.write("\n".join(M2) + "\n")
        if V2:
            f.write("<< via2 >>\n")
            f.write("\n".join(V2) + "\n")
        if M1:
            f.write("<< metal1 >>\n")
            f.write("\n".join(M1) + "\n")
        if V1:
            f.write("<< via1 >>\n")
            f.write("\n".join(V1) + "\n")
        if labels:
            f.write("<< labels >>\n")
            f.write("\n".join(labels) + "\n")
        f.write("\n".join(body))
        f.write("\n<< end >>\n")

    print(f"wrote {OUT}")
    print(f"  instances      {n}")
    print(f"  bbox (int)     {min(xs)} {min(ys)} {max(xs)} {max(ys)}")
    print(f"  bbox (um)      {(max(xs)-min(xs))/UM:.2f}"
          f" x {(max(ys)-min(ys))/UM:.2f}")
    print(f"  area (um^2)    {(max(xs)-min(xs))*(max(ys)-min(ys))/UM/UM:.0f}")
    from collections import Counter
    cnt = Counter(g for g, *_ in rows)
    print("  groups         " + "  ".join(f"{k}:{v}" for k, v in sorted(cnt.items())))
    print(f"  C1 straps      {len(straps)-len(spine_info)} vertical"
          f" + {len(spine_info)} spines (met4)")
    for (jl, jh, i0, i1, y0, y1) in spine_info:
        print(f"    j{jl}/j{jh} cols {i0}-{i1}  y {y0}..{y1}"
              f"  ({(y1-y0)/UM:.2f} um tall, clears C2 by {CLEAR/UM:.2f})")
    nsum = sum(1 for v in core.values() if v != "d")
    print(f"  C1 net covers  {nsum} cells, joined into ONE net")
    print(f"  C2 escapes     {len(V2)} via2 + pads (met2)")
    print(f"  C2 straps      {c2_straps} vertical, same-net")
    import collections
    grp = collections.defaultdict(list)
    for (i, j), g in core.items():
        if g != "d":
            grp[g].append((i, j))
    print(f"  C2 straps      {h_straps} horizontal, same-net (met1)")
    # connected components under 4-connectivity
    print("  C2 components per net:")
    seen, total = set(), 0
    for g in sorted(grp):
        comps = 0
        for cell in grp[g]:
            if cell in seen:
                continue
            comps += 1
            stack = [cell]
            seen.add(cell)
            while stack:
                (a, b) = stack.pop()
                for nb in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
                    if nb in grp[g] and nb not in seen:
                        seen.add(nb); stack.append(nb)
        total += comps
        print(f"    {g:>3}  {len(grp[g]):>2} cells -> {comps} component(s)")
    print(f"  core components total: {total} BEFORE the 4 final joins")
    print(f"  ports          {len(ports)}: "
          + " ".join(n for n, _, _ in ports))
    print("  final joins    T8,T2 on met1 (row gaps);"
          " F,T4 on met2 (column gap i4/i5)")

if __name__ == "__main__":
    main()
