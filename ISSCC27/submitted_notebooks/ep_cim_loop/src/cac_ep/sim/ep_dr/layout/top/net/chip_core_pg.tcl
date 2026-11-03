# chip_core r3 — mk_top.py 2026-10-28 07:35, col_blk = digital/col_blk/out/col_blk, arr = layout/top/strap/arr_w3s_128x64.cdl
connect_global_net VDD -type pg_pin -pin_base_name VDD -all
connect_global_net VDD -type pg_pin -pin_base_name vdd -all
connect_global_net VDD -type pg_pin -pin_base_name VPWR -all
connect_global_net VDD -type pg_pin -pin_base_name VPB -all
connect_global_net VSS -type pg_pin -pin_base_name VSS -all
connect_global_net VSS -type pg_pin -pin_base_name vss -all
connect_global_net VSS -type pg_pin -pin_base_name VGND -all
connect_global_net VSS -type pg_pin -pin_base_name VNB -all
connect_global_net VSS -type tie_lo -all   ;# 1'b0: arr_f.wl_106…wl_127, arr_n.wl_106…wl_127, colb_f.lo, colb_n.lo
