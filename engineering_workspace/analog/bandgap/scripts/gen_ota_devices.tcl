# ============================================================
# gen_ota_devices.tcl -- build the OTA's device cells
#
#   magic -dnull -noconsole -rcfile $PDK_ROOT/.../sky130A.magicrc \
#         < analog/bandgap/scripts/gen_ota_devices.tcl
#
# PIPE IT ON STDIN. A .tcl passed as a trailing argument is taken as
# a cell name to load, and magic then hangs reading the terminal.
#
# Generates one cell per distinct device, saves it, and reports the
# bounding box. The bbox is what sets placement pitch, exactly as
# FIXED_BBOX did for mimcap_unit.
#
# SETTLED 2026-11-14 -- THE TWO CONVENTIONS DIFFER:
#
#   SPICE  W is the TOTAL device width; nf only splits it into
#          fingers. Measured: W=40 nf=1 draws 503.5 uA, W=40 nf=4
#          draws 504.5 uA. Ratio 1.0019 -- the 0.19 % is diffusion
#          area changing with finger count, nothing more.
#   MAGIC  w is the width of EACH FINGER. A first pass at w=40 nf=4
#          extracted as FOUR devices of w=40, i.e. 160 um total.
#
# So every multi-finger device must be generated with
#       w_magic = W_spice / nf
# Rev 1 of this script did not, which would have put a 160 um input
# pair in the layout against a 40 um schematic -- 4x the design gm.
# LVS would have caught it, but only after the block was placed and
# routed.
#
# mkdev below takes the SPICE total and divides. Pass W as it appears
# in sc_ota.spice and the arithmetic stays in one place.
# ============================================================

proc mkdev {name gen wtot l nf guard} {
    # wtot is the SPICE total width; magic wants it per finger
    set w [expr {double($wtot) / $nf}]
    set P [${gen}_defaults]
    dict set P w     $w
    dict set P l     $l
    dict set P nf    $nf
    dict set P guard $guard
    load $name -silent
    box 0 0 0 0
    if {[catch {${gen}_draw $P} err]} {
        puts "  $name : DRAW FAILED -- $err"
        return
    }
    select top cell
    set b [box values]
    set x0 [lindex $b 0]; set y0 [lindex $b 1]
    set x1 [lindex $b 2]; set y1 [lindex $b 3]
    puts [format "  %-16s Wtot=%-4s w/f=%-5s l=%-5s nf=%s g=%s bbox %s (%.2f x %.2f um)" \
          $name $wtot $w $l $nf $guard $b \
          [expr {($x1-$x0)/200.0}] [expr {($y1-$y0)/200.0}]]
    save $name
}

set N sky130::sky130_fd_pr__nfet_01v8
set P sky130::sky130_fd_pr__pfet_01v8

puts "=========================================================="
puts " OTA device cells   (200 internal units = 1 um)"
puts "=========================================================="

# ---- SINGLE-FINGER UNITS for the two matched pairs ----------
# An nf=4 device is four fingers of ONE transistor. Two of those
# side by side is a plain differential pair, NOT common-centroid.
# Interdigitation has to happen finger by finger, so the pairs are
# built from single-finger units placed in a pattern -- the same
# approach as the MIM array.
#
#   input pair  XM1/XM2, W=40 nf=4 each -> 8 units of w=10 l=4
#               pattern A B B A A B B A
#               A at 1,4,5,8 and B at 2,3,6,7, both centroids 4.5
#   mirror load XM3/XM4, W=20 nf=2 each -> 4 units of w=10 l=1
#               pattern A B B A, both centroids 2.5
#
# guard 0 on every unit: one shared ring goes round each group.
# A per-unit ring would wall the fingers apart and defeat the point.
mkdev unit_n10_l4    $N 10   4    1 0
mkdev unit_p10_l1    $P 10   1    1 0

# the nf=4/nf=2 forms are kept for reference and area comparison;
# they are NOT what gets placed for the matched pairs.
mkdev dev_n40_l4_f4  $N 40   4    4 0
mkdev dev_p20_l1_f2  $P 20   1    2 0

# standalone devices keep their own guard ring
mkdev dev_n16_l4     $N 16   4    1 1
mkdev dev_p80_l2_f4  $P 80   2    4 1
mkdev dev_n80_l4_f2  $N 80   4    2 1
mkdev dev_n10_l015   $N 10   0.15 1 1

puts ""
puts " extracting to check w/nf semantics..."
foreach c {unit_n10_l4 unit_p10_l1 dev_n40_l4_f4 dev_p20_l1_f2 \
           dev_n16_l4 dev_p80_l2_f4 dev_n80_l4_f2 dev_n10_l015} {
    load $c
    extract do local
    extract all
}
ext2spice lvs
foreach c {unit_n10_l4 unit_p10_l1 dev_n40_l4_f4 dev_p20_l1_f2 \
           dev_n16_l4 dev_p80_l2_f4 dev_n80_l4_f2 dev_n10_l015} {
    load $c
    ext2spice
}
puts "=========================================================="
quit -noprompt
