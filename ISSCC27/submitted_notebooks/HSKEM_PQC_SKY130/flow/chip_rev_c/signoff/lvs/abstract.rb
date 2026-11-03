# Chip v2 LVS (from asic/run_a3_rcx0114_lvs_run8_abstract.rb): every SRAM master in the GDS is replaced by its
# LEF pin frame (pins, labels, outline), whose pin set must equal the reference port list; unreachable cells
# (e.g. the unused 16x256 master merged by the flow) are deleted. Old fixed counts are now arguments
# (-rd sram_instances=) or recorded; cells other than the top, standard cells and SRAMs must be ORFS vias.
include RBA

input_gds = $input_gds
output_gds = $output_gds
manifest = $manifest
spec = $macro_spec
reference_cdl = $reference_cdl
raise "missing input_gds" if input_gds.to_s.empty?
raise "missing output_gds" if output_gds.to_s.empty?
raise "missing macro_spec" if spec.to_s.empty?
raise "missing reference_cdl" if reference_cdl.to_s.empty?

groups = []
File.readlines(reference_cdl, chomp: true).each do |line|
  if line.lstrip.start_with?("+") && !groups.empty?
    groups[-1] << " " << line.lstrip[1..].strip
  else
    groups << line.strip
  end
end
subckt_ports = {}
groups.each do |line|
  tokens = line.split
  next unless tokens.size >= 2 && tokens[0].casecmp?(".subckt")
  subckt_ports[tokens[1].downcase] = tokens[2..]
end

metal_gds = {
  "met1" => 68,
  "met2" => 69,
  "met3" => 70,
  "met4" => 71,
  "met5" => 72,
}

macros = spec.split(";").map do |entry|
  name, lef = entry.split("=", 2)
  raise "bad macro_spec entry: #{entry}" if name.to_s.empty? || lef.to_s.empty?
  [name, lef]
end

layout = Layout.new
layout.read(input_gds)
top = layout.cell("trustedge_asic_core")
raise "missing trustedge_asic_core top" unless top

top_counts_before = Hash.new(0)
top.each_inst { |inst| top_counts_before[layout.cell(inst.cell_index).name] += 1 }
expected_sram_instances = $sram_instances.to_i
raise "missing sram_instances" unless expected_sram_instances > 0
raise "unexpected SRAM instance total" unless macros.sum { |name, _| top_counts_before[name] } == expected_sram_instances

audit = []
macros.each do |name, lef_path|
  target = layout.cell(name)
  raise "missing GDS SRAM master #{name}" unless target

  lef_layout = Layout.new
  lef_layout.read(lef_path)
  source = lef_layout.cell(name)
  raise "missing LEF macro #{name}" unless source

  labels = []
  pin_shapes = 0
  outline_shapes = 0
  target.clear

  lef_layout.layer_indices.each do |li|
    info = lef_layout.get_info(li)
    layer_name = info.name.to_s
    if layer_name == "OUTLINE"
      dst = layout.layer(235, 4)
      source.shapes(li).each do |shape|
        target.shapes(dst).insert(shape)
        outline_shapes += 1
      end
      next
    end

    match = /\A(met[1-5])\.(PIN|LABEL)\z/.match(layer_name)
    next unless match
    metal = match[1]
    purpose = match[2]
    gds_layer = metal_gds.fetch(metal)
    dst = layout.layer(gds_layer, purpose == "PIN" ? 20 : 5)
    source.shapes(li).each do |shape|
      if purpose == "PIN"
        raise "non-polygon pin shape #{name}:#{layer_name}" unless shape.is_box? || shape.is_polygon? || shape.is_path?
        target.shapes(dst).insert(shape)
        pin_shapes += 1
      else
        raise "non-text label #{name}:#{layer_name}" unless shape.is_text?
        target.shapes(dst).insert(shape.text)
        labels << shape.text.string
      end
    end
  end

  unique_labels = labels.uniq
  raise "duplicate non-supply label #{name}" unless labels.group_by(&:itself).all? { |pin, xs| xs.size == 1 || %w[vccd1 vssd1].include?(pin.downcase) }
  raise "empty pin frame #{name}" if pin_shapes == 0 || unique_labels.empty? || outline_shapes != 1
  raise "missing supply label #{name}" unless unique_labels.map(&:downcase).include?("vccd1") && unique_labels.map(&:downcase).include?("vssd1")
  reference_ports = subckt_ports[name.downcase]
  raise "missing reference port list #{name}" unless reference_ports
  label_set = unique_labels.map(&:downcase).sort
  port_set = reference_ports.map(&:downcase).sort
  raise "pin set mismatch #{name} labels_only=#{(label_set - port_set).join(',')} reference_only=#{(port_set - label_set).join(',')}" unless label_set == port_set

  audit << [name, lef_path, top_counts_before[name], unique_labels.size, labels.size, pin_shapes]
end

macros.each do |name, _|
  layout.prune_subcells(layout.cell(name).cell_index, -1)
end

top_counts_after = Hash.new(0)
top.each_inst { |inst| top_counts_after[layout.cell(inst.cell_index).name] += 1 }
macros.each do |name, _|
  raise "placement count changed #{name}" unless top_counts_after[name] == top_counts_before[name]
end

seen = {}
queue = [top]
until queue.empty?
  cell = queue.shift
  next if seen[cell.cell_index]
  seen[cell.cell_index] = true
  next if macros.any? { |name, _| name == cell.name }
  cell.each_inst { |inst| queue << layout.cell(inst.cell_index) }
end
names = seen.keys.map { |i| layout.cell(i).name }
std = names.select { |n| n.start_with?("sky130_fd_sc_hd__") }
sram = names.select { |n| macros.any? { |name, _| name == n } }
other = names.reject { |n| n == top.name || std.include?(n) || sram.include?(n) }.sort
expected_other = other
expected_total = names.size
puts "CHIPV2_ABSTRACT_REACHABILITY|total=#{names.size}|stdcells=#{std.size}|sram=#{sram.size}|other=#{other.size}|other_names=#{other.join(',')}"
raise "non-via helper cells reachable: #{other.reject { |n| n.start_with?('VIA_') }.join(',')}" unless other.all? { |n| n.start_with?("VIA_") }
raise "SRAM master mismatch #{sram.size}/#{macros.size}" unless sram.size == macros.size

unreachable = layout.each_cell.map(&:cell_index).reject { |i| seen[i] }
layout.delete_cells(unreachable) unless unreachable.empty?

layout.write(output_gds)

reopen = Layout.new
reopen.read(output_gds)
reopen_top = reopen.cell("trustedge_asic_core")
raise "reopen top mismatch" unless reopen_top
raise "reopen has multiple top cells" unless reopen.top_cells.size == 1 && reopen.top_cells[0].name == "trustedge_asic_core"
raise "reopen cell count mismatch #{reopen.cells}" unless reopen.cells == expected_total

File.open(manifest, "w") do |f|
  f.puts "CHIPV2_LVS_ABSTRACT=PASS"
  f.puts "top=trustedge_asic_core"
  f.puts "reachable_total=#{expected_total}"
  f.puts "reachable_standard_cells=#{std.size}"
  f.puts "reachable_sram_masters=#{sram.size}"
  f.puts "reachable_via_helpers=#{expected_other.size}"
  f.puts "top_sram_instances=#{expected_sram_instances}"
  f.puts "deleted_unreachable_cells=#{unreachable.size}"
  f.puts "via_helper_allowlist=#{other.join(',')}"
  audit.each_with_index do |row, index|
    name, lef, instances, unique_pins, labels, shapes = row
    f.puts "macro_#{index}_name=#{name}"
    f.puts "macro_#{index}_lef=#{lef}"
    f.puts "macro_#{index}_instances=#{instances}"
    f.puts "macro_#{index}_unique_pin_labels=#{unique_pins}"
    f.puts "macro_#{index}_label_shapes=#{labels}"
    f.puts "macro_#{index}_pin_shapes=#{shapes}"
  end
end

puts "CHIPV2_LVS_ABSTRACT=PASS|reachable=#{expected_total}|stdcells=#{std.size}|sram_masters=#{sram.size}|via_helpers=#{expected_other.size}|sram_instances=#{expected_sram_instances}|deleted_unreachable=#{unreachable.size}"
