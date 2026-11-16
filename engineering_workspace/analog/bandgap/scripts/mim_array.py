"""Generate and check a common-centroid MIM placement for the SC bandgap.

8x8 core inside a 10x10 dummy ring.
  C_A       4 units
  C_F       4 units
  C_B base 32 units
  trim      8 + 4 + 2 + 1 = 15 units
  internal dummies 9
  total    64 core + 36 ring = 100

Rule: every group is placed in centrosymmetric pairs (r,c) <-> (7-r,7-c),
which puts its centre of gravity exactly at the array centre. Only groups
with an odd count can't be: here that is trim-1 (one unit) and one dummy.
That residue is reported rather than hidden.
"""
import sys

N = 8
CENTRE = (N - 1) / 2.0

# C_B base is 32, not 36: see BANDGAP_NOTES.md section 7.
# 32 is EVEN, so C_B gets an exact common-centroid placement.
GROUPS = [("A", 4), ("F", 4), ("T8", 8), ("T4", 4), ("T2", 2), ("T1", 1),
          ("B", 32), ("d", 9)]


def pair_of(r, c):
    return (N - 1 - r, N - 1 - c)


def build():
    grid = [[None] * N for _ in range(N)]

    # Ring order: walk cells by distance from centre so the small, most
    # critical groups (A, F) land close in, and B fills the outside.
    cells = sorted(((r, c) for r in range(N) for c in range(N)),
                   key=lambda p: ((p[0] - CENTRE) ** 2 + (p[1] - CENTRE) ** 2,
                                  p[0], p[1]))

    for name, count in GROUPS:
        placed = 0
        # centrosymmetric pairs first
        for (r, c) in cells:
            if count - placed < 2:
                break
            if grid[r][c] is not None:
                continue
            pr, pc = pair_of(r, c)
            if grid[pr][pc] is not None:
                continue
            grid[r][c] = name
            grid[pr][pc] = name
            placed += 2
        # an odd leftover goes as close to the centre as possible, which
        # is where its unavoidable centroid offset costs least
        if placed < count:
            for (r, c) in cells:
                if grid[r][c] is None:
                    grid[r][c] = name
                    placed += 1
                    break

    # anything still empty becomes an internal dummy
    for r in range(N):
        for c in range(N):
            if grid[r][c] is None:
                grid[r][c] = "d"
    return grid


def centroid(grid, name):
    pts = [(r, c) for r in range(N) for c in range(N) if grid[r][c] == name]
    if not pts:
        return None, 0
    rr = sum(p[0] for p in pts) / len(pts)
    cc = sum(p[1] for p in pts) / len(pts)
    return (rr - CENTRE, cc - CENTRE), len(pts)


def gradient_error(grid, name, gx, gy):
    """Fractional capacitance error from a linear gradient across the array."""
    pts = [(r, c) for r in range(N) for c in range(N) if grid[r][c] == name]
    if not pts:
        return 0.0
    tot = 0.0
    for (r, c) in pts:
        fx = (c - CENTRE) / (N - 1)
        fy = (r - CENTRE) / (N - 1)
        tot += 1.0 + gx * fx + gy * fy
    return tot / len(pts) - 1.0


grid = build()

if "--coords" not in sys.argv:
  print("=" * 62)
  print("MIM ARRAY -- generated common-centroid placement")
  print("=" * 62)
  print("\n      " + " ".join(f"{c:>3}" for c in range(N)))
  print("     +" + "----" * N)
  for r in range(N):
    print(f" {r:>2}  |" + " ".join(f"{(grid[r][c] or '.'):>3}" for c in range(N)))

  print("\n  (a full dummy ring surrounds this 8x8 core -> 10x10 = 100 units)")

  print("\n" + "-" * 62)
  print(f"{'group':>6} {'units':>6} {'centroid offset (pitch)':>26}")
  print("-" * 62)
  ok = True
  for name, want in GROUPS:
    off, n = centroid(grid, name)
    status = ""
    if off is None:
        continue
    if abs(off[0]) < 1e-9 and abs(off[1]) < 1e-9:
        status = "exact"
    else:
        status = f"OFFSET  <- odd count ({n} units)"
        if n % 2 == 0:
            ok = False
    if n != want:
        print(f"    note: {name} placed {n}, nominal {want}")
    print(f"{name:>6} {n:>6}      dr={off[0]:+.4f}  dc={off[1]:+.4f}   {status}")

  total = sum(1 for r in range(N) for c in range(N) if grid[r][c])
  print("-" * 62)
  print(f"  core cells used: {total}/64   ring dummies: 36   total: {total + 36}")

  print("\n" + "=" * 62)
  print("GRADIENT SENSITIVITY  (guide's defaults: 0.50 %/array x, 0.30 %/array y)")
  print("=" * 62)
  gx, gy = 0.005, 0.003
  eA = gradient_error(grid, "A", gx, gy)
  eF = gradient_error(grid, "F", gx, gy)

  # C_B at code 8 = base + T8
  ptsB = [(r, c) for r in range(N) for c in range(N) if grid[r][c] in ("B", "T8")]
  tot = 0.0
  for (r, c) in ptsB:
    tot += 1.0 + gx * (c - CENTRE) / (N - 1) + gy * (r - CENTRE) / (N - 1)
  eB = tot / len(ptsB) - 1.0

  print(f"  C_A error {eA*1e6:+8.1f} ppm")
  print(f"  C_F error {eF*1e6:+8.1f} ppm")
  print(f"  C_B error {eB*1e6:+8.1f} ppm   (base + trim8, {len(ptsB)} units, code 8)")

  VREF = 1.2477      # measured device, base 31, code 8
  dv = VREF * (eB - eF)
  print(f"\n  VREF shift from the gradient ~ {dv*1e3:+.3f} mV")
  print("  (compare: naive row-by-row placement gives tens of mV here)")

  print("\n" + "=" * 62)
  print("RANDOM MISMATCH  (A_C = 1.0 %*um assumed -- sky130 publishes none)")
  print("=" * 62)
  import math
  AC, Cu_side = 0.01, 5.0
  sigma_u = AC / Cu_side
  print(f"  unit {Cu_side} x {Cu_side} um -> sigma(C)/C per unit = {sigma_u*100:.3f} %")
  for name, n in (("C_A", 4), ("C_F", 4), ("C_B", 40)):
    print(f"  {name:>4} ({n:>2} units) sigma = {sigma_u/math.sqrt(n)*100:.3f} %")
  sA = sigma_u / math.sqrt(4)
  sF = sigma_u / math.sqrt(4)
  sB = sigma_u / math.sqrt(40)
  VBE, DVBE = 0.7160, 0.05454   # measured
  CA = CF = 4.0; CB = 40.0
  dA = CA * VBE / CF * sA
  dB = CB * DVBE / CF * sB
  dF = VREF * sF
  s_vref = math.sqrt(dA**2 + dB**2 + dF**2)
  print(f"\n  sigma(VREF) = {s_vref*1e3:.2f} mV   (guide's painter reports ~1.11 mV)")

# ============================================================
# COORDINATE EMITTER  --  run with:  mim_array.py --coords
#
# The grid above is the electrical design. This turns it into
# geometry, so the placement is never transcribed by hand -- which
# is the step where a common-centroid array normally dies.
#
# Unit: 5.0 x 5.0 um of capm. At sky130's 2 fF/um^2 that is 50 fF,
# which is the Cu the whole SC design was dimensioned around
# (C_A = C_F = 4 units = 200 fF, C_B = 40 units at code 8 =
# 2000 fF, giving the beta = 0.078 used in tb_ota_settling).
#
# Pitch: 6.2 um, so 1.2 um between adjacent unit edges.
# Array: 10 x 10 at 6.2 um = 62.0 x 62.0 um, which is 3844 um^2 of
# the bandgap's 80 x 90 budget.
#
# Row r = 0 is the TOP row as printed, so y decreases with r and
# the emitted layout matches the grid you just read.
#
# MUST use cap_mim_m3_1 (capm, between met3 and met4). cap_mim_m4_1
# sits between met4 and met5, and met5 is reserved for the Tiny
# Tapeout power grid.
# ============================================================
# PITCH, from the PDK cell's REAL extent -- not from "5 um unit plus
# a gap", which was the first guess and was wrong.
# mimcap_unit.mag (generated by sky130_fd_pr__cap_mim_m3_1 at w=l=5)
# draws, in internal units at 200/um:
#     capm      x -676..324   y -500..500     = 5.0 x 5.0 um
#     metal3    x -716..716   y -540..540     = 7.16 x 5.4 um
#     via3/met4 x  616..712                   <- the C2 bottom-plate
#                                                contact, deliberately
#                                                OUTSIDE FIXED_BBOX
#                                                (-716 -540 364 540)
# So the cell is 7.16 x 5.4 um of drawn metal, and a 6.2 um square
# pitch would have overlapped neighbours by nearly a micron.
# met3 min spacing in sky130 is 0.3 um; these leave 0.34 and 0.40.
# REV 2, 2026-11-14, after magic DRC on the generated array. 7.5 x 5.8
# failed three rules; drc why named them and the binding one was NOT
# the obvious one:
#   capm.2a   capm <-> capm             >= 0.84 um
#   met3.3d   wide met3 <-> met3        >= 0.40 um
#   capm.11   capm <-> UNRELATED met3   >= 1.34 um   <-- binding
# capm.11 binds because met3 runs to +716 while the neighbour's capm
# starts at -676+P, so the governing gap is P - 1392 units:
#   x: P >= 1392 + 268 = 1660 units = 8.30 um
#   y: Q >= 1040 + 268 = 1308 units = 6.54 um
# 8.5 / 6.7 leaves 0.20 um and 0.16 um over the limit.
PITCH_X  = 8.5
PITCH_Y  = 6.7
# capm is NOT centred on the cell origin: it spans -676..324, so its
# centre is at x = -176 internal units = -0.88 um. Placement must use
# the capm centre, since that is what common-centroid matching is
# about -- a constant offset is harmless, an unaccounted one is not.
CAPM_DX_UM = -0.88
UNIT     = 5.0
RING     = 1          # one dummy cell deep, all round
FULL     = N + 2 * RING          # 10
CU_FF    = 50.0

def unit_centre(i, j):
    """capm centre of ring-coordinate cell (i,j), i across, j up."""
    return (PITCH_X * i + PITCH_X / 2.0, PITCH_Y * j + PITCH_Y / 2.0)

def emit_coords(grid):
    span_x = PITCH_X * FULL
    span_y = PITCH_Y * FULL
    rows = []
    # core: grid row r is the TOP row at r=0, so j counts down from N
    for r in range(N):
        for c in range(N):
            i, j = c + RING, (N - 1 - r) + RING
            x, y = unit_centre(i, j)
            rows.append((grid[r][c], r, c, i, j, x, y))
    # dummy ring
    for i in range(FULL):
        for j in range(FULL):
            if i in (0, FULL - 1) or j in (0, FULL - 1):
                x, y = unit_centre(i, j)
                rows.append(("ring", -1, -1, i, j, x, y))

    print("# MIM array placement, generated by mim_array.py --coords")
    print(f"# unit {UNIT} x {UNIT} um = {CU_FF:.0f} fF area"
          f" (+3.8 fF fringe: PDK cperi = 0.19 fF/um)")
    print(f"# pitch {PITCH_X} x {PITCH_Y} um, from the PDK cell extent")
    print(f"# array {FULL} x {FULL} = {span_x:.1f} x {span_y:.1f} um"
          f" = {span_x*span_y:.0f} um^2")
    print(f"# capm centre offset in cell coords: {CAPM_DX_UM} um in x")
    print("# x,y are UNIT CENTRES in um, relative to array lower-left (0,0).")
    print("# x,y are the CAPM CENTRE. To place mimcap_unit there,")
    print(f"# translate the cell by (x - ({CAPM_DX_UM}), y).")
    print("#")
    print("group,row,col,i,j,x_um,y_um")
    for g, r, c, i, j, x, y in rows:
        rr = "" if r < 0 else r
        cc = "" if c < 0 else c
        print(f"{g},{rr},{cc},{i},{j},{x:.3f},{y:.3f}")

    print("#")
    print("# --- totals ---")
    from collections import Counter
    cnt = Counter(g for g, *_ in rows)
    for g in sorted(cnt):
        print(f"# {g:>5}  {cnt[g]:>3} units  {cnt[g]*CU_FF:>7.0f} fF")
    code8 = cnt.get("B", 0) + cnt.get("T8", 0)
    print(f"# C_B at code 8 = B + T8 = {code8} units"
          f" = {code8*CU_FF:.0f} fF")
    print(f"# beta = C_F/(C_A+C_B+C_F+Cp), Cp = 150 fF ->"
          f" {cnt['F']*CU_FF/(cnt['A']*CU_FF + code8*CU_FF + cnt['F']*CU_FF + 150):.4f}")

if "--coords" in sys.argv:
    emit_coords(grid)
    sys.exit(0)

sys.exit(0 if ok else 1)
