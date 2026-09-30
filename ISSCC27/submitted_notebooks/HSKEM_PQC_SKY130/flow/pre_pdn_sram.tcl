# OpenRAM SKY130 macros expose the core supply rails with the foundry-style
# vccd1/vssd1 names.  Register them before the platform PDN script runs
# global_connect so the macro grids attach to VDD/VSS.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^vccd1$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^vssd1$} -ground
