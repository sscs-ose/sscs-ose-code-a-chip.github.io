foreach c {place_inst create_place_blockage create_place_halo cut_rows delete_rows delete_obj create_route_rule set_route_attributes edit_pin create_pin add_stripes create_shape route_special create_route_blockage set_db_net} {
  puts "######## $c"
  if {[catch {help -detail $c} m]} { puts "NOHELP $c: $m" }
}
foreach a {route_rule skip_routing dont_touch use_rule is_dont_route} {
  puts "######## net attr $a"
  if {[catch {help -detail -attribute net:$a} m]} { puts "NOATTR $a: $m" }
}
puts "######## apropos row"
catch {help *row*} m; puts $m
exit
