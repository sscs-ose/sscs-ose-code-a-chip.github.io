# Chip v2 LVS copy of asic/run_a3_rcx0114_lvs_run10_gds_label_probe_l2n.rb; the active pin count is an argument
# (-rd expected_active=, from pin_activity.rb) instead of the old 341.
include RBA

l2n_path = $l2n.to_s
gds_path = $gds.to_s
reference_path = $reference_cdl.to_s
raise "missing L2N" unless File.size?(l2n_path)
raise "missing GDS" unless File.size?(gds_path)
raise "missing reference CDL" unless File.size?(reference_path)

lvs = LayoutVsSchematic.new
lvs.read_l2n(l2n_path)

gds = Layout.new
gds.read(gds_path)
gds_top = gds.cell("trustedge_asic_core")
raise "missing GDS top" unless gds_top

reference = Netlist.new
reference.read(reference_path, NetlistSpiceReader.new)
reference_top = reference.circuit_by_name("TRUSTEDGE_ASIC_CORE")
raise "missing reference top" unless reference_top
reference_pins = reference_top.each_pin.map { |pin| pin.name.to_s }
reference_fold = reference_pins.map(&:upcase).to_h { |name| [name, name] }
reference_active = {}
reference_top.each_pin do |pin|
  net = reference_top.net_for_pin(pin.id)
  raise "reference top pin without net #{pin.name}" unless net
  reference_active[pin.name.to_s.upcase] = net.subcircuit_pin_count > 0 || net.terminal_count > 0
end

drawing_regions = {}
lvs.layer_indexes.each do |index|
  info = lvs.layer_info(index)
  next unless info && info.datatype == 20
  drawing_regions[info.layer] = lvs.layer_by_index(index)
end

labels = {}
gds.layer_indexes.each do |index|
  info = gds.get_info(index)
  next unless info.datatype == 5 && drawing_regions.key?(info.layer)
  gds_top.shapes(index).each do |shape|
    next unless shape.is_text?
    value = shape.text.string.to_s
    folded = value.upcase
    next unless reference_fold.key?(folded)
    raise "duplicate GDS top label #{value}" if labels.key?(folded)
    labels[folded] = [value, info.layer, shape.text.trans.disp]
  end
end
raise "GDS/reference label count mismatch #{labels.size}/#{reference_pins.size}" unless labels.size == reference_pins.size

results = []
misses = []
ambiguous = []
die = gds_top.bbox
labels.sort.each do |folded, (label, layer, point)|
  next unless reference_active.fetch(folded)
  dx = point.x < die.left + 2_000 ? 1 : (point.x > die.right - 2_000 ? -1 : 0)
  dy = point.y < die.bottom + 2_000 ? 1 : (point.y > die.top - 2_000 ? -1 : 0)
  candidates = []
  [0, 1, 100].each do |step|
    probe_point = Point.new(point.x + dx * step, point.y + dy * step)
    net = lvs.probe_net(drawing_regions.fetch(layer), probe_point)
    candidates << [net.name.to_s, probe_point.x, probe_point.y] if net
  end
  unique = candidates.map(&:first).uniq
  if unique.size == 1
    chosen = candidates.first
    results << [reference_fold.fetch(folded), label, layer, point.x, point.y, chosen[0], chosen[1], chosen[2]]
  elsif unique.size > 1
    ambiguous << [label, layer, point.x, point.y, candidates.map { |row| row.join('@') }.uniq.join(',')]
  else
    misses << [label, layer, point.x, point.y]
  end
end

puts "A3_RUN10_GDS_LABEL_PROBE_L2N"
puts "reference_top_pin_count=#{reference_pins.size}"
puts "reference_active_pin_count=#{reference_active.count { |_name, active| active }}"
puts "reference_inactive_pin_count=#{reference_active.count { |_name, active| !active }}"
puts "probed_count=#{results.size}"
puts "miss_count=#{misses.size}"
puts "ambiguous_count=#{ambiguous.size}"
puts "unique_probed_net_count=#{results.map { |row| row[5] }.uniq.size}"
results.each do |reference_name, label, layer, x, y, net_name, probe_x, probe_y|
  puts "map=#{reference_name}|label=#{label}|layer=#{layer}|x=#{x}|y=#{y}|probe_x=#{probe_x}|probe_y=#{probe_y}|l2n_net=#{net_name}"
end
misses.each do |label, layer, x, y|
  puts "miss=#{label}|layer=#{layer}|x=#{x}|y=#{y}"
end
ambiguous.each do |label, layer, x, y, candidates|
  puts "ambiguous=#{label}|layer=#{layer}|x=#{x}|y=#{y}|candidates=#{candidates}"
end
raise "one or more GDS labels did not probe to an extracted net" unless misses.empty?
raise "one or more GDS labels probe ambiguously" unless ambiguous.empty?
expected_active = $expected_active.to_i
raise "missing expected_active" unless expected_active > 0
raise "unexpected active top pin count #{results.size}/#{expected_active}" unless results.size == expected_active
raise "two top labels probe to the same extracted net" unless results.map { |row| row[5] }.uniq.size == results.size
puts "A3_RUN10_GDS_LABEL_PROBE_L2N=PASS"
