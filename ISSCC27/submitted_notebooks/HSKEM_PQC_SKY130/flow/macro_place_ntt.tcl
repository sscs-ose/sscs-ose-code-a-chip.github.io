# Fixed placement of the NTT coefficient macro for the OpenRAM-macro points (ORFS hook
# MACRO_PLACEMENT_TCL). The macro has address pins on both its top and its bottom edge; the
# automatic placer puts it against the bottom of the die, which leaves no room to place drivers
# next to the bottom pins. Raising it by about 30 um keeps the same orientation and gives both pin
# rows space for a driver just outside the placement halo (flow/post_grt_macro_pins.tcl).
# SPDX-License-Identifier: Apache-2.0
place_macro -macro_name u_coeff_ram.u_macro -location {11.975 43.52} -orientation R180
set cac_m [[ord::get_db_block] findInst u_coeff_ram.u_macro]
$cac_m setPlacementStatus FIRM
