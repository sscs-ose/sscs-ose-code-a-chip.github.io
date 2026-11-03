# Reference audit for chip v2 LVS (from asic/run_a3_rcx0114_lvs_run8_reference.rb): the SRAM masters are
# blanked (independent transistor-level LVS covers them), unused top circuits are purged, and the counts must
# agree with the filter stats (top instances) and the SRAM list given on the command line.
# -rd cdl= -rd stats= -rd masters=a,b,.. -rd expected_top=<retained_top_instances>
include RBA

masters = $masters.to_s.split(",")
expected_top = $expected_top.to_i
top_name = "TRUSTEDGE_ASIC_CORE"
raise "missing masters" if masters.empty?
raise "missing expected_top" unless expected_top > 0

netlist = Netlist.new
netlist.read($cdl, NetlistSpiceReader.new)
masters.each do |name|
  circuit = netlist.circuit_by_name(name.upcase)
  raise "missing reference SRAM #{name}" unless circuit
  circuit.blank
end
top = netlist.circuit_by_name(top_name)
raise "missing reference top" unless top
netlist.top_circuits.to_a.each { |c| netlist.purge_circuit(c) unless c == top }
netlist.purge

circuits = netlist.each_circuit.to_a
std = circuits.select { |c| c.name.start_with?("SKY130_FD_SC_HD__") }
sram = circuits.select { |c| masters.map(&:upcase).include?(c.name) }
other = circuits - std - sram - [top]
instances = top.each_subcircuit.to_a.size
raise "reference SRAM count #{sram.size}/#{masters.size}" unless sram.size == masters.size
raise "reference top instance count #{instances}/#{expected_top}" unless instances == expected_top
raise "unexpected reference circuits #{other.map(&:name).join(',')}" unless other.empty?
sram_instances = top.each_subcircuit.count { |s| masters.map(&:upcase).include?(s.circuit_ref.name) }

File.open($stats, "w") do |f|
  f.puts "CHIPV2_LVS_REFERENCE=PASS"
  f.puts "circuits=#{circuits.size}"
  f.puts "standard_cells=#{std.size}"
  f.puts "sram_masters=#{sram.size}"
  f.puts "sram_instances=#{sram_instances}"
  f.puts "top_instances=#{instances}"
end
puts "CHIPV2_LVS_REFERENCE=PASS|circuits=#{circuits.size}|stdcells=#{std.size}|sram=#{sram.size}|sram_instances=#{sram_instances}|top_instances=#{instances}"
