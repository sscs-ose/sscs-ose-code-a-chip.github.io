# Copyright 2025 LibreLane Contributors
# Adapted from OpenLane, Copyright 2020-2022 Efabless Corporation
# Licensed under the Apache License, Version 2.0.
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Versioned HuLLCirq modification: complete children-first, per-definition
# extraction, with a separate one-SD style only for qualified decap geometry.
# No geometry writes, abstract/ignore additions, warning suppression or feedback
# deletion. Original raw ext2spice output is retained before an explicit include.
set f [open $::env(STEP_DIR)/cif_scale.txt "w"]
puts $f [expr {((round([magic::cif scale output] * 10000)) / 10000.0) * 1}]
close $f
source $::env(SCRIPTS_DIR)/magic/common/read.tcl
drc off
crashbackups disable
locking disable
set hullcirq_root [file normalize [file join $::env(STEP_DIR) ../../..]]
set hullcirq_helper [file join $hullcirq_root lvs_moscap_v5.py]
# Load the exact source-tech copy plus a separate extraction style BEFORE GDS.
tech load [file join $hullcirq_root derived-sky130A-moscap-v5.tech] -noprompt
source [file join $hullcirq_root extraction-cell-plan.tcl]
# Magic's database can already contain its empty initial window definition.
# Keep observations before/after GDS and port annotation. Never drop an
# unexpected cell by name or ignore a cell containing real paint or labels.
proc hullcirq_record_inventory {hullcirq_phase} {
    global hullcirq_root hullcirq_helper hullcirq_expected_cells
    set hullcirq_events {}
    foreach hullcirq_name [lsort -unique [cellname list allcells]] {
        set hullcirq_flags [lsort -unique [cellname list flags $hullcirq_name]]
        set hullcirq_children [lsort -unique [cellname list children $hullcirq_name]]
        set hullcirq_paint -1
        set hullcirq_labels -1
        set hullcirq_instances -1
        if {[lsearch -exact $hullcirq_expected_cells $hullcirq_name] < 0} {
            load $hullcirq_name
            select top cell
            set hullcirq_bbox [select bbox]
            if {[llength $hullcirq_bbox] != 4} {
                error "Cannot prove a non-source native definition is empty"
            }
            snap internal
            select do labels
            lassign $hullcirq_bbox hullcirq_x1 hullcirq_y1 hullcirq_x2 hullcirq_y2
            box values [expr {$hullcirq_x1-1}] [expr {$hullcirq_y1-1}] [expr {$hullcirq_x2+1}] [expr {$hullcirq_y2+1}]
            select area *
            set hullcirq_contents [what -list]
            if {[llength $hullcirq_contents] != 3} {
                error "Cannot inspect complete native paint, labels and instances"
            }
            set hullcirq_paint [llength [lindex $hullcirq_contents 0]]
            set hullcirq_labels [llength [lindex $hullcirq_contents 1]]
            set hullcirq_instances [llength [lindex $hullcirq_contents 2]]
            select clear
        }
        lappend hullcirq_events $hullcirq_name [llength $hullcirq_flags] {*}$hullcirq_flags [llength $hullcirq_children] {*}$hullcirq_children $hullcirq_paint $hullcirq_labels $hullcirq_instances
    }
    exec python3 $hullcirq_helper inventory $hullcirq_root $hullcirq_phase {*}$hullcirq_events
}
if {!$::env(MAGIC_EXT_USE_GDS)} {
    error "Qualified MOSCAP extraction requires the unchanged source GDS"
}
hullcirq_record_inventory pre_gds
gds read $::env(CURRENT_GDS)
hullcirq_record_inventory post_gds
read_pdk_spice
hullcirq_record_inventory post_annotation
if {[info exists ::env(MAGIC_EXT_ABSTRACT_CELLS)] && $::env(MAGIC_EXT_ABSTRACT_CELLS) ne ""} {
    error "Qualified extraction does not add cell abstractions"
}
if {[info exists ::env(MAGIC_EXT_ABSTRACT_CELLS_RX)] && $::env(MAGIC_EXT_ABSTRACT_CELLS_RX) ne ""} {
    error "Qualified extraction does not add cell abstractions"
}
load $::env(DESIGN_NAME) -dereference
set backup $::env(PWD)
set extdir $::env(STEP_DIR)/extraction
set netlist $::env(STEP_DIR)/$::env(DESIGN_NAME).spice
file mkdir $extdir
cd $extdir
extract do local
extract no capacitance
extract no coupling
extract no resistance
extract no adjust
if {$::env(MAGIC_EXT_UNIQUE) != "none"} {
    extract unique $::env(MAGIC_EXT_UNIQUE)
}
set hullcirq_execution {}
set hullcirq_last_feedback 0
foreach hullcirq_row $hullcirq_cell_plan {
    lassign $hullcirq_row hullcirq_cell hullcirq_style
    load $hullcirq_cell -dereference
    set hullcirq_before [feedback count]
    if {$hullcirq_before != $hullcirq_last_feedback} {
        error "Feedback changed outside the recorded extraction operation"
    }
    extract style $hullcirq_style
    if {[feedback count] != $hullcirq_before} {
        error "Extraction style change discarded feedback"
    }
    # `extract cell <file>` extracts the selected cell, not merely the cell
    # loaded into the window. Select after style reload and bind its identity.
    select top cell
    set hullcirq_selected [cellname list self]
    if {$hullcirq_selected ne $hullcirq_cell} {
        error "The selected extraction definition differs from the planned source cell"
    }
    extract cell $hullcirq_cell
    if {![file isfile [file join $extdir $hullcirq_cell.ext]]} {
        error "A discovered cell did not produce its own fresh extraction file"
    }
    set hullcirq_after [feedback count]
    if {$hullcirq_after < $hullcirq_before} {
        error "Extraction discarded prior feedback"
    }
    lappend hullcirq_execution $hullcirq_cell $hullcirq_style $hullcirq_selected $hullcirq_before $hullcirq_after
    set hullcirq_last_feedback $hullcirq_after
}
exec python3 $hullcirq_helper record $hullcirq_root {*}$hullcirq_execution
load $::env(DESIGN_NAME) -dereference
extract style ngspice()
ext2spice lvs
if {$::env(MAGIC_EXT_SHORT_RESISTOR)} {
    ext2spice short resistor
}
ext2spice -o [file join $hullcirq_root extraction-raw.spice] $::env(DESIGN_NAME).ext
exec python3 $hullcirq_helper finalize $hullcirq_root
cd $backup
feedback save $::env(STEP_DIR)/feedback.txt
