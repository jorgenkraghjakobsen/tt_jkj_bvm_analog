import math

k_q = 8.617333262e-5          # Boltzmann / charge, V/K
T0   = 300.15                 # 27 C
VG0  = 1.17

# ------------------------------------------------------------------
# MEASURED from tb_pnp_char.spice, sky130 tt, 2026-11-13.
# These replace the textbook placeholders (VBE0 = 0.650, ETA = 4.0).
#
#   VBE at 8I (4.0 uA)    715.97 mV   <- what C_A samples in option D
#   VBE at 1I (0.5 uA)    661.43 mV
#   dVBE                   54.54 mV
#   dVBE/dT at 8I         -1.7953 mV/K
#   dVBE/dT at 1I         -1.9783 mV/K
#   ddVBE/dT              +0.1830 mV/K
#
# ETA is back-solved so the model reproduces the measured 8I slope.
# ------------------------------------------------------------------
VBE_8I  = 0.7159708
DVBE_27 = 0.05454046
S_VBE8  = -1.79530e-3
S_DVBE  =  0.18300e-3

ETA = 1 + (-(VG0 - VBE_8I)/T0 - S_VBE8)/k_q      # ~4.28

# C_B base. Was 36, which suited a design sampling VBE at 1I
# (ratio 10.81 -> code 7.2). Option D samples at 8I, ratio 9.81, so
# base 36 put the optimum at code 3.2 and the reset value at
# 155 ppm/C. Base 31 recentres the optimum on code 8.
CB_BASE = 32

def VT(T): return k_q * T

def vbe(T, vbe0=VBE_8I, alpha=1.0):
    """VBE(T) anchored on the measured 8I operating point."""
    return VG0 - (T/T0)*(VG0 - vbe0) - (ETA - alpha)*VT(T)*math.log(T/T0)

def dvbe(T, N=8):
    """Measured dVBE, PTAT and very linear over this range."""
    return DVBE_27 + S_DVBE*(T - T0)

def vref(T, CA, CB, CF, vbe0=VBE_8I):
    return (CA*vbe(T, vbe0) + CB*dvbe(T)) / CF

print("="*64)
print(f"1. TRIM / TEMPERATURE COEFFICIENT   (C_A = C_F = 4u, C_B = {CB_BASE} + code)")
print("="*64)
CA = CF = 4.0
Tlo, Thi = 273.15, 358.15      # 0 - 85 C

best = None
rows = []
for code in range(16):
    CB = float(CB_BASE) + code
    Ts = [Tlo + i*(Thi-Tlo)/200 for i in range(201)]
    vs = [vref(T, CA, CB, CF) for T in Ts]
    vmin, vmax = min(vs), max(vs)
    v27 = vref(T0, CA, CB, CF)
    tc = (vmax - vmin)/v27/(Thi-Tlo)*1e6     # box method, ppm/C
    rows.append((code, CB, v27, tc))
    if best is None or tc < best[3]:
        best = (code, CB, v27, tc)

print(f"{'code':>4} {'C_B(u)':>7} {'VREF@27C':>10} {'TC ppm/C':>10}")
for code, CB, v27, tc in rows:
    mark = "  <- best" if code == best[0] else ("  <- default" if code == 8 else "")
    print(f"{code:>4} {CB:>7.0f} {v27:>9.4f}V {tc:>9.1f}{mark}")

print(f"\n  slope change per code ~ {abs(rows[9][3]-rows[8][3]):.0f} ppm/C")
print(f"  dVBE/dT  at 27 C = {(vbe(T0+0.5)-vbe(T0-0.5))*1e3:+.2f} mV/K")
print(f"  dDVBE/dT at 27 C = {(dvbe(T0+0.5)-dvbe(T0-0.5))*1e3:+.3f} mV/K  (N=8)")
print(f"  ideal C_B/C_A    = {-(vbe(T0+0.5)-vbe(T0-0.5))/(dvbe(T0+0.5)-dvbe(T0-0.5)):.2f}"
      f"  -> code {-(vbe(T0+0.5)-vbe(T0-0.5))/(dvbe(T0+0.5)-dvbe(T0-0.5))*CA - CB_BASE:.1f}")
print(f"  DVBE at 27 C     = {dvbe(T0)*1e3:.1f} mV")

print()
print("="*64)
print("2. OTA REQUIREMENT  (this is the number that matters)")
print("="*64)
Cu   = 50e-15
CAf, CFf = 4*Cu, 4*Cu
CBf  = (CB_BASE + 8)*Cu     # reset code 8
Cp   = 150e-15
beta = CFf/(CAf + CBf + CFf + Cp)
print(f"  C_A = C_F = {CAf*1e15:.0f} fF   C_B = {CBf*1e15:.0f} fF   Cp = {Cp*1e15:.0f} fF")
print(f"  feedback factor beta = {beta:.4f}  (1/{1/beta:.1f})")

eps_v = 0.5e-3
vout  = 1.2416
eps   = eps_v/vout
A_req = 1/(beta*eps)
print(f"  settling error budget {eps_v*1e3:.1f} mV on {vout:.4f} V -> eps = {eps:.2e}")
print(f"  required DC gain     = {A_req:.0f}  = {20*math.log10(A_req):.1f} dB")

slot   = 5.12e-6
settle = slot/2
Ntau   = math.log(1/eps)
GBW    = Ntau/(2*math.pi*settle*beta)
print(f"  slot {slot*1e6:.2f} us, settle window {settle*1e6:.2f} us, N_tau = {Ntau:.1f}")
print(f"  required GBW = {GBW/1e6:.2f} MHz")

CL_eff = 1.5e-12
Cc     = 0.5*CL_eff
gm1    = GBW*2*math.pi*Cc
print(f"  Cc ~ {Cc*1e15:.0f} fF -> gm1 = {gm1*1e6:.1f} uS")
for gmid in (10, 15, 20):
    print(f"    gm/ID = {gmid:>2}  ->  ID = {gm1/gmid*1e6:.2f} uA   OTA total ~ {4*gm1/gmid*1e6:.2f} uA")

print()
print("  --- what the Rev19 OTA actually delivers ---")
print("  Rev19 is L=0.5 um everywhere on a 2 uA tail.")
for gmro in (30, 50, 100):
    A2 = gmro**2
    print(f"    gm*ro = {gmro:>3} per stage -> two-stage gain {20*math.log10(A2):>5.1f} dB"
          f"   static error {1/(A2*beta)*vout*1e3:>7.2f} mV")
print(f"  Budget is {eps_v*1e3:.1f} mV. Measure the real gain with .ac before redesigning.")

print()
print("="*64)
print("3. AREA  (does this fit a 1x2 tile?)")
print("="*64)
tile_1x2 = 160*225
mim_pitch = 6.2
mim = (10*mim_pitch)**2
bg_block = 80*90
print(f"  1x2 tile            {tile_1x2:>8.0f} um^2  (160 x 225)")
print(f"  MIM array 10x10     {mim:>8.0f} um^2  ({10*mim_pitch:.0f} x {10*mim_pitch:.0f})")
print(f"  bandgap block       {bg_block:>8.0f} um^2  (80 x 90 budget) = {bg_block/tile_1x2*100:.0f}% of tile")
for dig in (10000, 15000, 20000):
    rest = 1000 + 2000 + 400 + 600     # DAC caps, DAC resistors, 2x out_buf, bias_gen+doubler
    tot  = bg_block + dig + rest
    verdict = "FITS (tight)" if tot < 0.7*tile_1x2 else "DOES NOT FIT"
    print(f"  + dig_top {dig:>6} um^2 + ~{rest} other -> {tot:>6.0f} um^2"
          f" = {tot/tile_1x2*100:>3.0f}% of 1x2   {verdict}")

print()
print("="*64)
print("4. CURRENT BUDGET  (option D, I = 0.5 uA)")
print("="*64)
I = 0.5e-6
print(f"  mirror units 9 x I          = {9*I*1e6:.1f} uA   (burst budget is 4 uA)")
print(f"  -> the 8 extra units MUST be gated by ota_en, or burst mode is over budget")
ota_on = 10e-6; core = 3e-6
print(f"  continuous: core {core*1e6:.0f} + OTA {ota_on*1e6:.0f} = {(core+ota_on)*1e6:.0f} uA  (spec <= 15 uA)")
tau_e = (VT(T0)/I)*CBf
print(f"  emitter settling tau = (VT/I)*C_B = {tau_e*1e9:.0f} ns -> 7tau = {7*tau_e*1e6:.2f} us"
      f" of a {slot*1e6:.2f} us slot")
