# Hold slack of the routed chip when the external launch delay of the inputs (minimum input delay) is changed.
# env: LIB SDC SPEF ODB EXTRA_LIBS MIN_IN (ns; only labels the run: the SDC given already carries the minimum input delay, see scripts/sta_io_hold.sh)
# SPDX-License-Identifier: Apache-2.0
read_liberty $::env(LIB)
foreach lib $::env(EXTRA_LIBS) { read_liberty $lib }
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
puts "RESULT min_input_delay $::env(MIN_IN)"
puts "RESULT hold_wns [sta::format_time [sta::worst_slack_cmd min] 3]"
puts "RESULT hold_violating_endpoints [sta::endpoint_violation_count min]"
puts "RESULT setup_wns [sta::format_time [sta::worst_slack_cmd max] 3]"
exit
