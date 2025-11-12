yosys -import

if {[info exist ::env(CACHED_NETLIST)]} {
  exec cp $::env(CACHED_NETLIST) $::env(RESULTS_DIR)/1_1_yosys.v
  if {[info exist ::env(CACHED_REPORTS)]} {
    exec cp {*}$::env(CACHED_REPORTS) $::env(REPORTS_DIR)/.
  }
  exit
}

# Setup verilog include directories
set vIdirsArgs ""
if {[info exist ::env(VERILOG_INCLUDE_DIRS)]} {
  foreach dir $::env(VERILOG_INCLUDE_DIRS) {
    lappend vIdirsArgs "-I$dir"
  }
  set vIdirsArgs [join $vIdirsArgs]
}

# Read verilog files
if {$::env(USE_YOSYS_SV_PLUGIN)} {
  puts "Using the Synlig Yosys plugin for reading Verilog/SystemVerilog."
  foreach file $::env(VERILOG_FILES) {
    if {[file extension $file] == ".sv"} {
      read_systemverilog -defer {*}$vIdirsArgs $file
    } else {
      read_verilog -defer -sv {*}$vIdirsArgs $file
    }
  }
} else {
  foreach file $::env(VERILOG_FILES) {
    read_verilog -defer -sv {*}$vIdirsArgs $file
    puts "reading veilog $file"
  }
}

# Read standard cells and macros as blackbox inputs
# These libs have their dont_use properties set accordingly
read_liberty -lib {*}$::env(DONT_USE_LIBS)
puts "Reading standard cells and macros as blackbox inputs: $::env(DONT_USE_LIBS)"

# Apply toplevel parameters (if exist)
if {[info exist ::env(VERILOG_TOP_PARAMS)]} {
  dict for {key value} $::env(VERILOG_TOP_PARAMS) {
    chparam -set $key $value $::env(DESIGN_NAME)
  }
}

# Read platform specific mapfile for OPENROAD_CLKGATE cells
if {[info exist ::env(CLKGATE_MAP_FILE)]} {
  read_verilog -defer $::env(CLKGATE_MAP_FILE)
}

# Mark modules to keep from getting removed in flattening
if {[info exist ::env(PRESERVE_HIERARCHY_MODULES)] } {
  # Expand hierarchy since verilog was read in with -defer
  hierarchy -check -top $::env(DESIGN_NAME)
  foreach module $::env(PRESERVE_HIERARCHY_MODULES) {
    puts "Preserving the hierarchy of module: `$module`"
    select -module $module
    setattr -mod -set keep_hierarchy 1
    select -clear
  }
}

if {[info exist ::env(BLOCKS)]} {
  hierarchy -check -top $::env(DESIGN_NAME)
  puts "top module is $::env(DESIGN_NAME)"
  foreach block $::env(BLOCKS) {
    blackbox $block
    puts "blackboxing $block"
  }
}

blackbox sram_macro

# stat mem_sp_sky130

# setattr -mod -set keep 1 mem_sp_sky130

puts "synth preamble finished"