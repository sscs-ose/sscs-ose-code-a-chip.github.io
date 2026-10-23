include RBA

require "digest"

L2N_PATH = $l2n.to_s
GDS_PATH = $gds.to_s
LAYOUT_CDL = $layout_cdl.to_s
REFERENCE_CDL = $reference_cdl.to_s
OUTPUT_CDL = $output_cdl.to_s
OUTPUT_MANIFEST = $output_manifest.to_s

# Chip v2 LVS copy of asic/run_a3_rcx0114_lvs_run15_repair_sram_pin_objects.rb. Hierarchical extraction
# omits a master pin when no parent wire leaves the instance there (one-ended SRAM outputs, Y of load-only
# standard cells). The old script pinned the old chip's masters and counts; here the SRAM list and instance
# count are arguments (-rd srams=a,b,.. -rd sram_instances=N) and the standard-cell masters are found by
# comparing the extracted and reference pin lists: a master may miss only Y, every reference occurrence of
# that Y must be one-ended, and every other difference stops the run. All per-object guards are unchanged.
SRAMS = $srams.to_s.split(",").map(&:downcase).freeze
EXPECTED_SRAM_INSTANCES = $sram_instances.to_i
raise "missing srams / sram_instances" if SRAMS.empty? || EXPECTED_SRAM_INSTANCES <= 0

def sha256(path)
  Digest::SHA256.file(path).hexdigest
end

def parse_instance_keys(path)
  result = {}
  pending = nil
  statement = nil
  File.foreach(path) do |line|
    if statement
      if line.lstrip.start_with?("+")
        statement << " " << line.lstrip[1..].strip
        next
      end
      words = statement.split
      model = words[-1].downcase
      if TARGET_CELLS.include?(model)
        raise "target statement without placement" unless pending
        name = words[0]
        raise "unexpected target instance name #{name}" unless name.match?(/^X\$\d+$/)
        key = [model, pending]
        raise "duplicate target placement key #{key.inspect}" if result.key?(key)
        result[key] = name[2..].to_i
      end
      statement = nil
      pending = nil
    end

    if (match = line.match(/^\* cell instance \S+ (\S+) \*1 ([^,]+),([^\s]+)\s*$/i))
      orient, x, y = match.captures
      x_dbu = (Float(x) * 1000).round
      y_dbu = (Float(y) * 1000).round
      pending = "#{orient.downcase} #{x_dbu},#{y_dbu}"
    elsif line.lstrip.match?(/^X/i)
      statement = line.strip
    end
  end
  if statement
    words = statement.split
    model = words[-1].downcase
    result[[model, pending]] = words[0][2..].to_i if TARGET_CELLS.include?(model)
  end
  unless result.size == EXPECTED_TARGET_INSTANCES
    raise "expected #{EXPECTED_TARGET_INSTANCES} target placement keys, got #{result.size}"
  end
  result
end

def reference_contract(path)
  netlist = Netlist.new
  netlist.read(path, NetlistSpiceReader.new)
  result = {}
  TARGET_CELLS.each do |name|
    circuit = netlist.circuit_by_name(name.upcase)
    raise "missing reference target cell #{name}" unless circuit
    ports = circuit.each_pin.map { |pin| pin.name.to_s }
    raise "duplicate reference target pin #{name}" unless ports.uniq.size == ports.size
    result[name] = ports
  end
  [netlist, result]
end

def physical_dangling_probe(lvs, regions, gds, top, child, inst, port)
  labels = []
  gds.layer_indexes.each do |index|
    info = gds.get_info(index)
    next unless info.datatype == 5 && regions.key?(info.layer)
    child.shapes(index).each do |shape|
      next unless shape.is_text? && shape.text.string.to_s.casecmp?(port)
      labels << [info.layer, shape.text.trans.disp]
    end
  end
  raise "missing GDS label #{child.name}.#{port}" if labels.empty?

  observations = []
  bbox = child.bbox
  labels.each do |layer, local|
    dx = local.x < bbox.left + 2_000 ? 1 : (local.x > bbox.right - 2_000 ? -1 : 0)
    dy = local.y < bbox.bottom + 2_000 ? 1 : (local.y > bbox.top - 2_000 ? -1 : 0)
    out_dx = -dx
    out_dy = -dy
    [[0, 0], [out_dx, out_dy], [out_dx * 10, out_dy * 10],
     [out_dx * 50, out_dy * 50], [out_dx * 100, out_dy * 100],
     [out_dx * 250, out_dy * 250], [out_dx * 500, out_dy * 500]].uniq.each do |ox, oy|
      point = inst.cplx_trans * Point.new(local.x + ox, local.y + oy)
      path = []
      net = lvs.probe_net(regions.fetch(layer), point, path, top)
      next unless net
      observations << [net, point, path]
    end
  end
  raise "no physical dangling probe #{child.name}.#{port}" if observations.empty?
  expected_qname = "#{child.name}:#{port}"
  matching = observations.select { |net, _point, _path| net.qname.to_s.casecmp?(expected_qname) }
  observed = observations.map { |net, _point, _path| net.qname.to_s }.uniq.sort
  if matching.empty?
    raise "physical dangling net absent #{child.name}.#{port}: observed=#{observed.join(',')}"
  end
  matching.each do |_net, _point, path|
    unless path.any? { |sub| sub.circuit_ref.name.to_s.casecmp?(child.name) }
      raise "probe hierarchy missing target instance #{child.name}.#{port}: observed=#{observed.join(',')}"
    end
  end
  net, point, path = matching.first
  [net, point, path]
end

def physical_net(lvs, regions, gds, top, child, inst, port, expected_parent = nil)
  labels = []
  gds.layer_indexes.each do |index|
    info = gds.get_info(index)
    next unless info.datatype == 5 && regions.key?(info.layer)
    child.shapes(index).each do |shape|
      next unless shape.is_text? && shape.text.string.to_s.casecmp?(port)
      labels << [info.layer, shape.text.trans.disp]
    end
  end
  raise "missing GDS label #{child.name}.#{port}" if labels.empty?
  observations = []
  bbox = child.bbox
  labels.each do |layer, local|
    dx = local.x < bbox.left + 2_000 ? 1 : (local.x > bbox.right - 2_000 ? -1 : 0)
    dy = local.y < bbox.bottom + 2_000 ? 1 : (local.y > bbox.top - 2_000 ? -1 : 0)
    # The extracted child circuit lacks a pin for the affected output bits.
    # An inward probe therefore returns the child-local net.  Walk out through
    # the macro boundary and accept only clusters represented in the top
    # circuit, which recovers the actual routed parent net without naming it.
    out_dx = -dx
    out_dy = -dy
    offsets = [[0, 0]]
    [1, 10, 50, 100, 250, 500, 1_000, 2_000, 5_000, 10_000].each do |distance|
      offsets << [out_dx * distance, out_dy * distance]
    end
    offsets.uniq.each_with_index do |(ox, oy), rank|
      point = inst.cplx_trans * Point.new(local.x + ox, local.y + oy)
      net = lvs.probe_net(regions.fetch(layer), point)
      if net
        if $debug.to_s == "1" && !expected_parent && child.name.downcase == "sky130_sram_1rw_24x256" && port.casecmp?("dout0[24]")
          puts "DEBUG_PROBE|rank=#{rank}|offset=#{ox},#{oy}|name=#{net.name}|qname=#{net.qname}|expanded=#{net.expanded_name}|cluster=#{net.cluster_id}|object=#{net.object_id}|point=#{point.x},#{point.y}"
        end
        parent = top.net_by_cluster_id(net.cluster_id)
        observations << [rank, parent, point] if parent
      end
    end
  end
  if expected_parent
    match = observations.find { |_rank, parent, _point| parent.cluster_id == expected_parent.cluster_id }
    raise "physical parent cluster not found #{child.name}.#{port}" unless match
    return [match[1], match[2]]
  end
  raise "DEBUG_STOP" if $debug.to_s == "1" && child.name.downcase == "sky130_sram_1rw_24x256" && port.casecmp?("dout0[24]")
  nearest_by_cluster = {}
  observations.each do |rank, parent, point|
    current = nearest_by_cluster[parent.cluster_id]
    nearest_by_cluster[parent.cluster_id] = [rank, parent, point] if !current || rank < current[0]
  end
  raise "unmapped routed parent net #{child.name}.#{port}" if nearest_by_cluster.empty?
  nearest_rank = nearest_by_cluster.values.map(&:first).min
  nearest = nearest_by_cluster.values.select { |rank, _parent, _point| rank == nearest_rank }
  raise "ambiguous routed parent net #{child.name}.#{port}" unless nearest.size == 1
  [nearest[0][1], nearest[0][2]]
end

[L2N_PATH, GDS_PATH, LAYOUT_CDL, REFERENCE_CDL].each do |path|
  raise "missing input #{path}" unless File.size?(path)
end
raise "output path missing" if OUTPUT_CDL.empty? || OUTPUT_MANIFEST.empty?

lvs = LayoutVsSchematic.new
lvs.read_l2n(L2N_PATH)
layout = lvs.netlist
top = layout.circuit_by_name("trustedge_asic_core")
raise "missing extracted top" unless top

# standard-cell masters whose extracted pin list misses reference pins
std_reference = Netlist.new
std_reference.read(REFERENCE_CDL, NetlistSpiceReader.new)
std_missing = {}
layout.each_circuit do |circuit|
  name = circuit.name.to_s.downcase
  next unless name.start_with?("sky130_fd_sc_hd__")
  # physical-only masters: the logical contract drops them (same list as its awk filter) and the
  # reference has CONB merged into the supplies, so their pin lists are not compared
  next if name.start_with?("sky130_fd_sc_hd__fill_") ||
          %w[sky130_fd_sc_hd__tapvpwrvgnd_1 sky130_fd_sc_hd__diode_2 sky130_fd_sc_hd__conb_1].include?(name)
  ref = std_reference.circuit_by_name(name.upcase)
  next unless ref
  have = circuit.each_pin.map { |pin| pin.name.to_s.upcase }
  missing = ref.each_pin.map { |pin| pin.name.to_s.upcase } - have
  std_missing[name] = missing unless missing.empty?
end
unexpected = std_missing.reject { |_name, missing| missing == ["Y"] }
raise "extracted standard cells miss pins other than Y: #{unexpected.inspect}" unless unexpected.empty?
STD_DANGLING_OUTPUT_COUNTS = std_missing.keys.sort.to_h do |name|
  [name, std_reference.circuit_by_name(name.upcase).each_ref.to_a.size]
end.freeze
std_reference = nil
TARGET_CELLS = (SRAMS + STD_DANGLING_OUTPUT_COUNTS.keys).freeze
EXPECTED_TARGET_INSTANCES = EXPECTED_SRAM_INSTANCES + STD_DANGLING_OUTPUT_COUNTS.values.sum
puts "CHIPV2_STD_MISSING_Y=#{STD_DANGLING_OUTPUT_COUNTS.inspect}"

placement_to_id = parse_instance_keys(LAYOUT_CDL)
reference, ref_ports = reference_contract(REFERENCE_CDL)

gds = Layout.new
gds.read(GDS_PATH)
gds_top = gds.cell("trustedge_asic_core")
raise "missing GDS top" unless gds_top

regions = {}
lvs.layer_indexes.each do |index|
  info = lvs.layer_info(index)
  regions[info.layer] = lvs.layer_by_index(index) if info && info.datatype == 20
end

new_pins = {}
SRAMS.each do |name|
  circuit = layout.circuit_by_name(name)
  raise "missing extracted SRAM #{name}" unless circuit
  existing = circuit.each_pin.map { |pin| pin.name.to_s.upcase }.reject(&:empty?)
  missing = ref_ports.fetch(name).reject { |port| existing.include?(port.upcase) }
  # (old chip: every SRAM master missed some pins; a master may now miss none)
  new_pins[name] = {}
  missing.each do |port|
    pin = circuit.create_pin(port)
    local_net = circuit.create_net("__physical_#{port}")
    circuit.connect_pin(pin.id, local_net)
    new_pins[name][port.upcase] = pin
  end
end

# Every pin absent from the extracted SRAM header must be a true one-ended
# reference connection.  This proves that a unique anonymous parent net is the
# correct topology; it prevents inventing or shorting a routed signal by name.
reference_dangling_guards = 0
SRAMS.each do |name|
  circuit = reference.circuit_by_name(name.upcase)
  missing_names = new_pins.fetch(name).keys
  refs = circuit.each_ref.to_a
  raise "reference SRAM has no instances #{name}" if refs.empty?
  refs.each do |sub|
    missing_names.each do |port|
      pin = circuit.each_pin.find { |candidate| candidate.name.to_s.casecmp?(port) }
      raise "reference missing guarded pin #{name}.#{port}" unless pin
      net = sub.net_for_pin(pin.id)
      unless net && net.subcircuit_pin_count == 1 && net.terminal_count == 0 && net.pin_count == 0
        raise "reference pin is not one-ended #{name}.#{port} net=#{net&.qname}"
      end
      reference_dangling_guards += 1
    end
  end
end
puts "CHIPV2_SRAM_ONE_ENDED_GUARDS=#{reference_dangling_guards}"

# The eight standard-cell masters below are used exclusively as deliberate
# load cells whose Y pin is one-ended in the reference.  Their GDS contains the
# physical Y shape/net, but hierarchical extraction omits the master pin when
# no parent wire leaves the instance.  Guard every occurrence before restoring
# the missing physical pin/net object.
standard_reference_dangling_guards = 0
STD_DANGLING_OUTPUT_COUNTS.each do |name, expected_count|
  circuit = reference.circuit_by_name(name.upcase)
  raise "missing reference standard cell #{name}" unless circuit
  pin = circuit.each_pin.find { |candidate| candidate.name.to_s.casecmp?("Y") }
  raise "reference standard cell missing Y #{name}" unless pin
  refs = circuit.each_ref.to_a
  raise "reference standard-cell count mismatch #{name}=#{refs.size}" unless refs.size == expected_count
  refs.each do |sub|
    net = sub.net_for_pin(pin.id)
    unless net && net.subcircuit_pin_count == 1 && net.terminal_count == 0 && net.pin_count == 0
      raise "reference standard-cell Y is not one-ended #{name} net=#{net&.qname}"
    end
    standard_reference_dangling_guards += 1
  end
end
expected_standard_dangling = STD_DANGLING_OUTPUT_COUNTS.values.sum
unless standard_reference_dangling_guards == expected_standard_dangling
  raise "standard dangling guard mismatch #{standard_reference_dangling_guards}"
end

# (2026-10-16, t3e) a top output tied by a conb_1 HI/LO straight to the port shares the supply net in the extraction
# (KLayout names it "VDD,<port>" / "VDD|<port>"); the reference ties the same ports (CHIPV2_LVS_TIED_PORTS, derived
# from the reference conb instances whose HI/LO net is a top pin). supply_name returns "VDD" / "VSS" for a supply net
# whose other names are only such ports, and the plain upcased name otherwise (any other merge still fails the guards).
TIED_PORTS = (ENV["CHIPV2_LVS_TIED_PORTS"] || "").split.map(&:upcase)
def supply_name(net)
  return "" unless net
  parts = net.name.to_s.upcase.split(/[|,]/)
  base = parts & %w[VDD VSS]
  return base[0] if base.size == 1 && (parts - base).all? { |p| TIED_PORTS.include?(p) }
  net.name.to_s.upcase
end

instance_count = 0
existing_object_checks = 0
missing_connections = 0
supply_guards = 0
connected_objects = []

gds_top.each_inst do |inst|
  child = gds.cell(inst.cell_index)
  name = child.name.downcase
  next unless SRAMS.include?(name)
  key = [name, inst.trans.to_s.downcase]
  id = placement_to_id[key]
  raise "unmatched GDS SRAM placement #{key.inspect}" unless id
  sub = top.subcircuit_by_id(id)
  raise "missing extracted SRAM subcircuit id=#{id}" unless sub
  raise "SRAM child mismatch id=#{id}" unless sub.circuit_ref.name.downcase == name
  circuit = sub.circuit_ref
  instance_count += 1

  ref_ports.fetch(name).each do |port|
    if port.casecmp?("vccd1") || port.casecmp?("vssd1")
      pin = circuit.each_pin.find { |candidate| candidate.name.to_s.casecmp?(port) }
      raise "missing extracted supply pin #{name}.#{port}" unless pin
      expected = port.casecmp?("vccd1") ? "VDD" : "VSS"
      actual = sub.net_for_pin(pin.id)
      raise "supply guard failed #{id}.#{port} net=#{actual&.name}" unless supply_name(actual) == expected
      supply_guards += 1
      next
    end

    pin = circuit.each_pin.find { |candidate| candidate.name.to_s.casecmp?(port) }
    if !new_pins.fetch(name).key?(port.upcase)
      raise "existing extracted pin disappeared #{name}.#{port}" unless pin
      parent = sub.net_for_pin(pin.id)
      net, point = physical_net(lvs, regions, gds, top, child, inst, port, parent)
      existing_object_checks += 1
    else
      pin = new_pins.fetch(name).fetch(port.upcase)
      local_net, point, path = physical_dangling_probe(lvs, regions, gds, top, child, inst, port)
      net = top.create_net("__run15_dangling_#{id}_#{port.gsub(/[^A-Za-z0-9_]/, '_')}")
      sub.connect_pin(pin.id, net)
      connected = sub.net_for_pin(pin.id)
      unless connected && connected.name.to_s == net.name.to_s && connected.circuit.name == top.name
        raise "missing pin connect failed id=#{id} pin=#{port} expected=#{net.qname}/#{net.object_id} actual=#{connected&.qname}/#{connected&.object_id}"
      end
      connected_objects << [id, name, port, net.name.to_s, net.object_id,
                            local_net.qname.to_s, path.map(&:id).join(","), point.x, point.y]
      missing_connections += 1
    end
  end
end

raise "SRAM instance count mismatch #{instance_count}" unless instance_count == EXPECTED_SRAM_INSTANCES
signal_ports = 0
gds_top.each_inst do |inst|
  n = gds.cell(inst.cell_index).name.downcase
  next unless SRAMS.include?(n)
  signal_ports += ref_ports.fetch(n).count { |p| !p.casecmp?("vccd1") && !p.casecmp?("vssd1") }
end
raise "SRAM pin accounting #{existing_object_checks}+#{missing_connections} != #{signal_ports}" unless existing_object_checks + missing_connections == signal_ports
raise "missing physical connections mismatch #{missing_connections}" unless missing_connections == reference_dangling_guards
raise "supply guards mismatch #{supply_guards}" unless supply_guards == 2 * EXPECTED_SRAM_INSTANCES
physical_groups = connected_objects.group_by { |row| row[4] }
duplicates = physical_groups.select { |_key, rows| rows.size > 1 }
unless duplicates.empty?
  detail = duplicates.map { |key, rows| "#{key.inspect}=#{rows.map { |row| [row[0], row[2]] }.inspect}" }.join(";")
  raise "physical missing net objects are not unique: #{detail}"
end

standard_probe_rows = []
standard_local_nets = {}
standard_instance_counts = Hash.new(0)
gds_top.each_inst do |inst|
  child = gds.cell(inst.cell_index)
  name = child.name.downcase
  next unless STD_DANGLING_OUTPUT_COUNTS.key?(name)
  key = [name, inst.trans.to_s.downcase]
  id = placement_to_id[key]
  raise "unmatched GDS standard-cell placement #{key.inspect}" unless id
  sub = top.subcircuit_by_id(id)
  raise "missing extracted standard-cell subcircuit id=#{id}" unless sub
  raise "standard-cell child mismatch id=#{id}" unless sub.circuit_ref.name.downcase == name
  circuit = sub.circuit_ref
  if circuit.each_pin.any? { |candidate| candidate.name.to_s.casecmp?("Y") }
    raise "standard-cell Y unexpectedly present #{name}"
  end
  local_net, point, path = physical_dangling_probe(lvs, regions, gds, top, child, inst, "Y")
  unless local_net.circuit.name.to_s.casecmp?(circuit.name.to_s)
    raise "standard-cell local Y circuit mismatch #{name}:#{local_net.qname}"
  end
  previous = standard_local_nets[name]
  if previous && !previous.qname.to_s.casecmp?(local_net.qname.to_s)
    raise "standard-cell Y local net mismatch #{name}:#{previous.qname}/#{local_net.qname}"
  end
  standard_local_nets[name] ||= local_net
  standard_probe_rows << [id, name, sub, local_net, point, path]
  standard_instance_counts[name] += 1
end

unless standard_instance_counts == STD_DANGLING_OUTPUT_COUNTS
  raise "standard-cell physical instance count mismatch #{standard_instance_counts.inspect}"
end

standard_pins = {}
STD_DANGLING_OUTPUT_COUNTS.each_key do |name|
  circuit = layout.circuit_by_name(name)
  raise "missing extracted standard cell #{name}" unless circuit
  pin = circuit.create_pin("Y")
  circuit.connect_pin(pin.id, standard_local_nets.fetch(name))
  connected = circuit.net_for_pin(pin.id)
  unless connected && connected.qname.to_s.casecmp?(standard_local_nets.fetch(name).qname.to_s)
    raise "standard-cell local Y pin connection failed #{name}"
  end
  standard_pins[name] = pin
end

standard_connected_objects = []
standard_probe_rows.each do |id, name, sub, local_net, point, path|
  pin = standard_pins.fetch(name)
  parent = top.create_net("__run15_std_dangling_#{id}_Y")
  sub.connect_pin(pin.id, parent)
  connected = sub.net_for_pin(pin.id)
  unless connected && connected.name.to_s == parent.name.to_s && connected.circuit.name == top.name
    raise "standard-cell parent Y connection failed #{id}/#{name}"
  end
  standard_connected_objects << [id, name, parent.name.to_s, parent.object_id,
                                 local_net.qname.to_s, local_net.object_id,
                                 path.map(&:id).join(","), point.x, point.y]
end

expected_standard_connections = STD_DANGLING_OUTPUT_COUNTS.values.sum
unless standard_connected_objects.size == expected_standard_connections
  raise "standard-cell dangling connection mismatch #{standard_connected_objects.size}"
end
standard_groups = standard_connected_objects.group_by { |row| row[2] }
standard_duplicates = standard_groups.select { |_key, rows| rows.size > 1 }
raise "standard-cell parent Y nets are not unique" unless standard_duplicates.empty?

removed_unnamed = 0
SRAMS.each do |name|
  circuit = layout.circuit_by_name(name)
  named = circuit.each_pin.to_a.reject { |pin| pin.name.to_s.empty? }
  unnamed = circuit.each_pin.to_a.select { |pin| pin.name.to_s.empty? }
  refs = circuit.each_ref.to_a
  unnamed.each do |pin|
    refs.each do |sub|
      net = sub.net_for_pin(pin.id)
      net_name = supply_name(net)
      named_nets = named.map { |named_pin| sub.net_for_pin(named_pin.id) }.compact
      unless %w[VDD VSS].include?(net_name) && named_nets.any? { |candidate| supply_name(candidate) == net_name }
        raise "unnamed pin is not redundant #{name} pin=#{pin.id}"
      end
    end
  end
  unnamed.sort_by { |pin| -pin.id }.each do |pin|
    refs.each { |sub| sub.disconnect_pin(pin.id) }
    circuit.disconnect_pin(pin.id)
    circuit.remove_pin(pin.id)
    removed_unnamed += 1
  end
end
puts "CHIPV2_REDUNDANT_UNNAMED_SUPPLY_PINS=#{removed_unnamed}"

layout.write(OUTPUT_CDL, NetlistSpiceWriter.new)
raise "empty output CDL" unless File.size?(OUTPUT_CDL)

lines = [
  "A3_RUN15_NET_OBJECT_REPAIR=PASS",
  "A3_RUN15_SRAM_NET_OBJECT_REPAIR=PASS",
  "physical_flow_launch=0",
  "l2n_modified_in_memory_only=1",
  "golden_reference_modified=0",
  "sram_master_count=#{SRAMS.size}",
  "sram_instance_count=#{instance_count}",
  "existing_physical_net_object_checks=#{existing_object_checks}",
  "missing_pin_physical_net_connections=#{missing_connections}",
  "reference_one_ended_dangling_guards=#{reference_dangling_guards}",
  "standard_cell_master_count=#{STD_DANGLING_OUTPUT_COUNTS.size}",
  "standard_cell_instance_count=#{standard_connected_objects.size}",
  "standard_cell_reference_one_ended_Y_guards=#{standard_reference_dangling_guards}",
  "standard_cell_physical_Y_net_connections=#{standard_connected_objects.size}",
  "supply_guards=#{supply_guards}",
  "removed_redundant_unnamed_supply_pins=#{removed_unnamed}",
  "l2n_sha256=#{sha256(L2N_PATH)}",
  "gds_sha256=#{sha256(GDS_PATH)}",
  "layout_contract_sha256=#{sha256(LAYOUT_CDL)}",
  "reference_sha256=#{sha256(REFERENCE_CDL)}",
  "output_cdl_sha256=#{sha256(OUTPUT_CDL)}"
]
connected_objects.sort.each do |id, name, port, net_name, object_id, local_qname, path_ids, x, y|
  lines << "instance=#{id}|cell=#{name}|pin=#{port}|anonymous_parent_net=#{net_name}|object_id=#{object_id}|physical_local_qname=#{local_qname}|probe_path_ids=#{path_ids}|probe_x=#{x}|probe_y=#{y}|guard=PASS"
end
STD_DANGLING_OUTPUT_COUNTS.sort.each do |name, count|
  lines << "standard_cell=#{name}|instances=#{count}|missing_pin=Y|reference_one_ended=PASS|physical_probe=PASS"
end
standard_connected_objects.sort.each do |id, name, net_name, object_id, local_qname, local_object_id, path_ids, x, y|
  lines << "standard_instance=#{id}|cell=#{name}|pin=Y|anonymous_parent_net=#{net_name}|object_id=#{object_id}|physical_local_qname=#{local_qname}|physical_local_object_id=#{local_object_id}|probe_path_ids=#{path_ids}|probe_x=#{x}|probe_y=#{y}|guard=PASS"
end
File.write(OUTPUT_MANIFEST, lines.join("\n") + "\n")
puts lines.join("\n")
