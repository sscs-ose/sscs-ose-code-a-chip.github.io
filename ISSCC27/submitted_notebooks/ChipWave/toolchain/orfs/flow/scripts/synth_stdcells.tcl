# Read standard cells and macros as blackbox inputs
read_liberty -overwrite -setattr liberty_cell -lib {*}$::env(LIB_FILES)
read_liberty -overwrite -setattr liberty_cell \
  -unit_delay -wb -ignore_miss_func -ignore_buses {*}$::env(LIB_FILES)
if { [info exists ::env(UNSET_ABC9_BOX_CELLS)] } {
  setattr -mod -unset abc9_box {*}$::env(UNSET_ABC9_BOX_CELLS)
}
