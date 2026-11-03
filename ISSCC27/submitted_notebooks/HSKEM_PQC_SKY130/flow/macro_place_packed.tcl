# Fixed placement of the packed NTT's 24x128 macro (ORFS hook MACRO_PLACEMENT_TCL). The macro has
# address pins on its bottom and top edges and its clock and enables on its left edge; about 40 um of
# room on each of those sides leaves space for strong drivers just outside the placement halo
# (flow/post_grt_macro_pins.tcl), the remedy found for the 16x256 macro (notebook, Appendix B.4).
# SPDX-License-Identifier: Apache-2.0
place_macro -macro_name u_sram.u_macro -location {60 50} -orientation R0
set cac_m [[ord::get_db_block] findInst u_sram.u_macro]
$cac_m setPlacementStatus FIRM
