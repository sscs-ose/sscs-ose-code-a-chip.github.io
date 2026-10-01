# Magic DRC on a final (post-PnR) GDS - run inside the LibreLane 3.0.14 image.
#
# Parameters come from ENVIRONMENT VARIABLES (not argv, because Magic puts its
# own CLI flags and the script path into $argv):
#   DRC_DESIGN   design tag, e.g. best_uniform (cell = fir_<design>)
#   DRC_GDS      path to the final GDS
#   DRC_OUT      output prefix for <out>_drc_count.txt / _drc_markers.txt
#
# Local invocation from the repo root:
#   export PDK_HASH=<hash>
#   docker run --rm -v "$PWD":/work -w /work -v "$HOME/.ciel":/root/.ciel \
#     -e PDK_ROOT=/root/.ciel/ciel/sky130/versions/$PDK_HASH \
#     -e DRC_DESIGN=best_uniform \
#     -e DRC_GDS=runs/best_uniform/final/gds/fir_best_uniform.gds \
#     -e DRC_OUT=/work/runs/drc_signoff/best_uniform \
#     ghcr.io/librelane/librelane:3.0.14 \
#     magic -noconsole -dnull \
#     -rcfile /root/.ciel/ciel/sky130/versions/$PDK_HASH/sky130A/libs.tech/magic/sky130A.magicrc \
#     synth/magic_drc.tcl
set design $env(DRC_DESIGN)
set gds $env(DRC_GDS)
set outp $env(DRC_OUT)

gds read $gds
load fir_$design -dereference
select top cell

# --- validation: refuse to report on an unloaded/empty cell -----------------
set bbox [property FIXED_BBOX]
puts "FIXED_BBOX $bbox"
if {[llength $bbox] != 4} {
    puts "FATAL: cell fir_$design has no FIXED_BBOX - GDS not loaded correctly"
    quit -noprompt
}

# --- DRC ---------------------------------------------------------------------
drc euclidean on
drc style drc(full)
drc check
drc catchup

set count 0
set fh [open ${outp}_drc_count.txt w]
foreach {ctype cvalue} [drc list count] {
    puts $fh "$ctype: $cvalue"
    set count [expr {$count + $cvalue}]
}
close $fh

set fm [open ${outp}_drc_markers.txt w]
foreach line [drc list why] {
    puts $fm $line
}
close $fm

puts "TOTAL_DRC_ERRORS $count"
quit -noprompt
