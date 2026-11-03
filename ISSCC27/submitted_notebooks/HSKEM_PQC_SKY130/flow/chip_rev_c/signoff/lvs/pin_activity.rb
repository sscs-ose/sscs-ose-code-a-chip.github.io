# Chip v2 LVS: unchanged copy of asic/run_a3_rcx0114_lvs_run10_reference_top_pin_activity.rb.
include RBA

reference = Netlist.new
reference.read($reference_cdl.to_s, NetlistSpiceReader.new)
top = reference.circuit_by_name("TRUSTEDGE_ASIC_CORE")
raise "missing reference top" unless top

active = 0
inactive = 0
top.each_pin do |pin|
  net = top.net_for_pin(pin.id)
  raise "top pin without net #{pin.name}" unless net
  is_active = net.subcircuit_pin_count > 0 || net.terminal_count > 0
  is_active ? active += 1 : inactive += 1
  puts "pin=#{pin.name}|active=#{is_active ? 1 : 0}|subcircuit_pin_count=#{net.subcircuit_pin_count}|terminal_count=#{net.terminal_count}|pin_count=#{net.pin_count}|net=#{net.name}"
end
puts "A3_RUN10_REFERENCE_TOP_PIN_ACTIVITY=PASS|active=#{active}|inactive=#{inactive}|total=#{active + inactive}"
