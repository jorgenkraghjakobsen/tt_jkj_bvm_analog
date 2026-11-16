# ============================================================
# gen_mim_array.tcl -- build the bandgap MIM array in Magic
#
#   magic -dnull -noconsole \
#         -rcfile $PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc \
#         analog/bandgap/scripts/gen_mim_array.tcl
#
# Reads analog/bandgap/doc/mim_placement.csv (from
# mim_array.py --coords) and places one PDK-generated unit cap per
# row. The geometry is the PDK device generator's, not hand-drawn:
# capm enclosure, via and met4 coverage are all its problem.
#
# UNITS. 'cif scale out' reported 0.005 and the tech banner says
# 2 internal units = 1 lambda, so 1 um = 200 internal units. The
# script prints the generated cell's bbox so that conversion can be
# checked against reality on the first run rather than trusted.
#
# WHY m3_1 AND NOT m3_2: m3_2 is capm2 (97/44), which sits between
# met4 and met5. Met5 is reserved for the Tiny Tapeout power grid.
# ============================================================

# RUN IT ON STDIN, NOT AS A TRAILING ARGUMENT.
#   magic ... < analog/bandgap/scripts/gen_mim_array.tcl
# A .tcl passed as the last argument is taken as a CELL NAME to load,
# after which magic sits reading stdin from the terminal and appears
# to hang. No argv here for the same reason -- piped in, there is none.
set UM     200.0                                   ;# internal units/um
set CSV    "analog/bandgap/doc/mim_placement.csv"  ;# from repo root
set OUTDIR "analog/bandgap/layout"

puts "=========================================================="
puts " gen_mim_array.tcl"
puts "=========================================================="
puts " tech            : [tech name]"
puts " cif scale out   : [cif scale out]"
puts " internal/um     : $UM"
puts " csv             : $CSV"

# ---- 1. the unit capacitor, straight from the PDK generator ----
set P [sky130::sky130_fd_pr__cap_mim_m3_1_defaults]
dict set P w 5.0
dict set P l 5.0
dict set P nx 1
dict set P ny 1
puts "\n unit params     : w=[dict get $P w] l=[dict get $P l]\
 carea=[dict get $P carea] cperi=[dict get $P cperi]"

set expect_ff [expr {5.0*5.0*[dict get $P carea] + 20.0*[dict get $P cperi]}]
puts " unit C (model)  : [format %.2f $expect_ff] fF\
 (50.0 area + [format %.2f [expr {20.0*[dict get $P cperi]}]] fringe)"

cd $OUTDIR
load mimcap_unit -silent
box 0 0 0 0
if {[catch {sky130::sky130_fd_pr__cap_mim_m3_1_draw $P} err]} {
    puts "\n *** _draw failed: $err"
    puts " *** trying magic::gencell_create instead"
    if {[catch {magic::gencell_create \
            sky130::sky130_fd_pr__cap_mim_m3_1 mimcap_unit $P} err2]} {
        puts " *** gencell_create also failed: $err2"
        puts " *** STOP -- paste both messages back"
        quit -noprompt
    }
}
select top cell
puts " unit bbox (int) : [box values]"
save mimcap_unit
puts " saved           : $OUTDIR/mimcap_unit.mag"

# ---- 2. place one instance per CSV row -------------------------
load mim_array -silent

set fh [open "../../../$CSV" r]
set n 0
set groups [dict create]
while {[gets $fh line] >= 0} {
    if {[string index $line 0] eq "#"} { continue }
    if {[string match "group,*" $line]} { continue }
    if {[string trim $line] eq ""}      { continue }

    set f [split $line ","]
    set g [lindex $f 0]
    set r [lindex $f 1]
    set c [lindex $f 2]
    set x [lindex $f 5]
    set y [lindex $f 6]

    # CSV gives unit CENTRES; the cell places from its lower-left
    set llx [expr {round(($x - 2.5) * $UM)}]
    set lly [expr {round(($y - 2.5) * $UM)}]

    box position ${llx} ${lly}
    getcell mimcap_unit

    if {$r eq ""} {
        identify ring_${n}
    } else {
        identify u_${g}_r${r}c${c}
    }
    dict incr groups $g
    incr n
}
close $fh

puts "\n placed          : $n instances"
foreach g [lsort [dict keys $groups]] {
    puts [format "   %-6s %3d" $g [dict get $groups $g]]
}

select top cell
puts " array bbox (int): [box values]"
puts " array bbox (um) : [box values]  / $UM"
save mim_array
puts " saved           : $OUTDIR/mim_array.mag"
puts "\n Next: run DRC with"
puts "   magic -dnull -noconsole -rcfile \$PDK_ROOT/sky130A/libs.tech/magic/sky130A.magicrc"
puts "   then: load mim_array ; drc check ; drc why"
puts "=========================================================="
quit -noprompt
