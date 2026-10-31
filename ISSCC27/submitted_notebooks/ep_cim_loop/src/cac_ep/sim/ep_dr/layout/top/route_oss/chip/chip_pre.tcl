catch { connect_global_net VSS -type tie_lo -all }
if {[catch {create_pg_pin -name VDD -net VDD -geom met4 868.690 1131.140 876.690 1133.140} m]} { puts "TOPR: PGPIN VDD FAIL $m" } else { puts "TOPR: PGPIN VDD" }
if {[catch {create_pg_pin -name VSS -net VSS -geom met4 958.690 1131.140 966.690 1133.140} m]} { puts "TOPR: PGPIN VSS FAIL $m" } else { puts "TOPR: PGPIN VSS" }
