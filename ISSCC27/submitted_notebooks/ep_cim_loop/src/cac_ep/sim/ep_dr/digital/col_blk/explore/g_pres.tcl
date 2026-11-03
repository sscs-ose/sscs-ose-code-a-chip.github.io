set P /home/grads/s/seokjindaveoh/work/ep_dr/digital/pdk
set_db init_lib_search_path $P
read_libs sky130_fd_sc_hvl__ff_085C_5v50.lib
read_hdl {../rtl/coll.v ../rtl/col_ctrl.v}
set_db auto_ungroup none
elaborate col_ctrl
set h [lindex [get_db hinsts *u_coll*] 63]
puts "HINST $h"
foreach v {map_size_ok size_ok true delete_ok size_delete_ok} {
  if {[catch {set_db $h .preserve $v} m]} { puts "PRES $v FAIL: $m" } else { puts "PRES $v OK -> [get_db $h .preserve]" }
}
catch {help -attribute preserve} m; puts "HELP $m"
exit
