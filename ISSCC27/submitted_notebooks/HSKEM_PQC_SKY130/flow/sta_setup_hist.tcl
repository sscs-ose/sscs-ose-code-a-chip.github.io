# Setup-violating endpoints of the routed chip, one worst path per endpoint (summary format), for a histogram by block.
# env: LIB SDC SPEF ODB EXTRA_LIBS
# SPDX-License-Identifier: Apache-2.0
read_liberty $::env(LIB)
foreach lib $::env(EXTRA_LIBS) { read_liberty $lib }
read_db $::env(ODB)
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
puts "SECTION SUMMARY"
report_checks -path_delay max -group_path_count 800 -endpoint_path_count 1 -unique_paths_to_endpoint -slack_max 0 -format summary
puts "SECTION END"
exit
