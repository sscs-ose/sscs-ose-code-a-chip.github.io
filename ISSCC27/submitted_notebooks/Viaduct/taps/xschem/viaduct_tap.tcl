# Viaduct xschem tap: a small RPC server inside the running xschem GUI.
#
# Loaded by ~/.xschem/xschemrc (block added by `viaduct install`), or manually:
#     xschem --script /foss/designs/viaduct/taps/xschem/viaduct_tap.tcl
#
# The server lives on xschem's Tk event loop, so every request executes in the
# GUI and the schematic redraws immediately. It listens on 127.0.0.1 only.
# (xschem's own --tcp-port server binds all interfaces, has no authentication
# and closes after each command, so it is not used.)
#
# Protocol v2, one line per request:  <nonce> <hmac> <base64 Tcl script> <request_id> <proto>
#   hmac = HMAC-SHA256(token, nonce + request_id + proto + script)
# Reply, one line:  <KIND> <base64 payload> <hmac>,  KIND = OK | ERR | DENIED
#   hmac = HMAC-SHA256(token, nonce + KIND + base64 payload): the relay can tell a
#   genuine tap from anything else answering on the port.
# Receipts: every request id is remembered (state running/completed, and the reply),
# so a caller whose request timed out (e.g. held by a dialog) can ask what happened
# instead of resending; a reused id is refused.

package require sha256

namespace eval viaduct {
  variable version viaduct-xschem-tap-0.4
  variable proto 2
  variable port [expr {[info exists ::env(VIADUCT_XSCHEM_PORT)] ? $::env(VIADUCT_XSCHEM_PORT) : 18766}]
  variable dir [expr {[info exists ::env(VIADUCT_STATE_DIR)] ? $::env(VIADUCT_STATE_DIR) : [file join $::env(HOME) .viaduct]}]
  variable token
  variable seen [dict create]
  # survives `reload` (re-sourcing this file)
  if {![info exists receipts]} { variable receipts [dict create] }
  variable server
}

# ---- JSON helpers (structured ops return JSON text) -------------------------

proc viaduct::jstr {s} {
  set map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t]
  return "\"[string map $map $s]\""
}
proc viaduct::jobj {kv} {
  set parts {}
  foreach {k v} $kv { lappend parts "[jstr $k]: $v" }
  return "\{[join $parts {, }]\}"
}
proc viaduct::jarr {items} { return "\[[join $items {, }]\]" }
proc viaduct::jnum {x} { if {[string is double -strict $x]} { return $x } else { return [jstr $x] } }

# ---- structured ops: viaduct::op::<name> <args-dict> -----------------------

namespace eval viaduct::op {}

proc viaduct::op::ping {a} {
  namespace upvar ::viaduct version version
  return [viaduct::jobj [list tap [viaduct::jstr $version] \
    xschem [viaduct::jstr [xschem get version]] \
    pid [pid] schematic [viaduct::jstr [xschem get schname]]]]
}

proc viaduct::op::new_schematic {a} {
  set path [dict get $a path]
  set replace [expr {[dict exists $a replace] && [dict get $a replace]}]
  if {[file exists $path] && !$replace} { error "refusing to overwrite existing $path (pass replace)" }
  file mkdir [file dirname $path]
  set f [open $path w]
  puts $f "v {xschem version=[xschem get version] file_version=1.2}"
  close $f
  # replace: the caller asked to discard the current window's unsaved edits.
  if {$replace} { xschem clear force }
  xschem load $path
  return [viaduct::jobj [list schematic [viaduct::jstr [xschem get schname]]]]
}

proc viaduct::op::load {a} {
  xschem load [dict get $a path]
  xschem zoom_full
  return [viaduct::jobj [list schematic [viaduct::jstr [xschem get schname]]]]
}

# Place a symbol. props is the xschem property string, e.g. "name=M1 W=1 L=0.15 nf=1"
proc viaduct::op::place {a} {
  set rot  [expr {[dict exists $a rot]  ? [dict get $a rot]  : 0}]
  set flip [expr {[dict exists $a flip] ? [dict get $a flip] : 0}]
  set props [expr {[dict exists $a props] ? [dict get $a props] : {}}]
  # xschem silently places an empty instance for a missing symbol; refuse instead.
  set sympath [abs_sym_path [dict get $a symbol]]
  if {![file exists $sympath]} { error "symbol not found: [dict get $a symbol] (looked for $sympath)" }
  set cmd [list xschem instance [dict get $a symbol] [dict get $a x] [dict get $a y] $rot $flip]
  # Without a property string xschem applies the symbol's template (W, L, nf, ...);
  # an explicit empty string would replace the template with nothing.
  if {$props ne {}} { lappend cmd $props }
  uplevel #0 $cmd
  set i [expr {[xschem get instances] - 1}]
  # Optional properties (and name) applied right away, so a batch needs no round trip
  # to learn the auto-assigned name: place {symbol x y set {name M1 W 2}}.
  if {[dict exists $a set] && [dict size [dict get $a set]] > 0} {
    return [viaduct::op::set_props [dict create name [xschem getprop instance $i name] props [dict get $a set]]]
  }
  return [viaduct::describe_instance $i]
}

# Wire through a list of points: {x1 y1 x2 y2 x3 y3 ...}
proc viaduct::op::wire {a} {
  set pts [dict get $a points]
  set n 0
  foreach {x1 y1} [lrange $pts 0 end-2] {x2 y2} [lrange $pts 2 end] {
    if {$x2 eq {}} break
    xschem wire $x1 $y1 $x2 $y2
    incr n
  }
  return [viaduct::jobj [list segments $n]]
}

proc viaduct::op::set_props {a} {
  set inst [dict get $a name]
  set props [dict get $a props]
  # Rename last: later setprop calls still find the instance by its old name.
  dict for {k v} $props { if {$k ne "name"} { xschem setprop instance $inst $k $v } }
  if {[dict exists $props name]} {
    set new [dict get $props name]
    xschem setprop instance $inst name $new
    if {[catch {xschem getprop instance $new name}]} {
      error "xschem did not rename $inst to $new: the name is taken (instance names are case-insensitive and labels are auto-named l1, l2, ...); choose another name"
    }
    set inst $new
  }
  return [viaduct::describe_instance $inst]
}

# Run a list of ops in one request: ops = {{op place args {...}} {op wire args {...}} ...}.
# Drawing is suspended while the batch runs and the window redraws once at the end.
# Stops at the first failing op; the reply says how many ops completed.
proc viaduct::op::batch {a} {
  set results {}
  set done 0
  set failure {}
  catch {xschem set no_draw 1}
  foreach item [dict get $a ops] {
    set name [dict get $item op]
    set args [expr {[dict exists $item args] ? [dict get $item args] : {}}]
    if {$name in {batch eval reload stop dismiss_dialogs close_dialog} || [info commands ::viaduct::op::$name] eq {}} {
      set failure [viaduct::jobj [list index $done op [viaduct::jstr $name] error [viaduct::jstr "op not allowed in a batch or unknown"]]]
      break
    }
    if {[catch {viaduct::op::$name $args} r]} {
      set failure [viaduct::jobj [list index $done op [viaduct::jstr $name] error [viaduct::jstr $r]]]
      break
    }
    lappend results $r
    incr done
  }
  catch {xschem set no_draw 0}
  catch {xschem redraw}
  set total [llength [dict get $a ops]]
  if {$failure ne {}} {
    return [viaduct::jobj [list ok false done $done total $total failure $failure results [viaduct::jarr $results]]]
  }
  return [viaduct::jobj [list ok true done $done total $total results [viaduct::jarr $results]]]
}

proc viaduct::describe_instance {i} {
  set props [xschem getprop instance $i]
  return [viaduct::jobj [list name [viaduct::jstr [xschem getprop instance $i name]] \
    symbol [viaduct::jstr [xschem getprop instance $i cell::name]] \
    props [viaduct::jstr $props]]]
}

proc viaduct::op::describe {a} {
  set items {}
  for {set i 0} {$i < [xschem get instances]} {incr i} {
    lappend items [viaduct::describe_instance $i]
  }
  return [viaduct::jobj [list schematic [viaduct::jstr [xschem get schname]] \
    modified [xschem get modified] instances [viaduct::jarr $items]]]
}

proc viaduct::op::save {a} {
  xschem save
  return [viaduct::jobj [list schematic [viaduct::jstr [xschem get schname]]]]
}

proc viaduct::op::netlist {a} {
  # Without a netlisting mode xschem opens a modal "Please Set netlisting mode"
  # box, so set SPICE mode and a netlist dir next to the schematic first.
  xschem set netlist_type spice
  set ::netlist_dir [file join [file dirname [xschem get schname]] simulation]
  file mkdir $::netlist_dir
  set_netlist_dir 0
  xschem netlist
  set dir $::netlist_dir
  set name [file rootname [file tail [xschem get schname]]]
  set path [file join $dir $name.spice]
  set text {}
  if {[file exists $path]} { set f [open $path]; set text [read $f]; close $f }
  return [viaduct::jobj [list path [viaduct::jstr $path] netlist [viaduct::jstr $text]]]
}

# Put waveform graphs (complete "B 2 ... {flags=graph ... viaduct=1}" records,
# built by the relay) on the schematic and load a .raw file into them, the
# open-source equivalent of watching Maestro results arrive. Graphs from a
# previous call (tagged viaduct=1) are replaced; nothing else is touched.
proc viaduct::op::show_waveforms {a} {
  set sch [xschem get schname]
  xschem save
  set f [open $sch]; set txt [read $f]; close $f
  set before [string length $txt]
  regsub -all {B 2 [-+0-9.e ]+\{flags=graph[^\}]*viaduct=1[^\}]*\}\n?} $txt {} txt
  set removed [expr {$before != [string length $txt]}]
  if {![string match *\n $txt]} { append txt \n }
  append txt [dict get $a graphs]
  if {![string match *\n $txt]} { append txt \n }
  set f [open $sch w]; puts -nonewline $f $txt; close $f
  xschem load $sch
  catch {xschem raw_clear}
  xschem raw_read [dict get $a raw] [dict get $a type]
  xschem zoom_full
  xschem redraw
  return [viaduct::jobj [list schematic [viaduct::jstr $sch] raw [viaduct::jstr [dict get $a raw]] \
    replaced_previous $removed]]
}

proc viaduct::op::zoom_fit {a} {
  xschem zoom_full
  return true
}

proc viaduct::op::screenshot {a} {
  set path [dict get $a path]
  set w [expr {[dict exists $a width]  ? [dict get $a width]  : 1400}]
  set h [expr {[dict exists $a height] ? [dict get $a height] : 900}]
  file mkdir [file dirname $path]
  set sel [xschem selected_set]   ;# print png drops the selection; it belongs to the designer
  xschem zoom_full
  xschem print png $path $w $h
  foreach n $sel { catch {xschem select instance $n} }
  return [viaduct::jobj [list path [viaduct::jstr $path] width $w height $h]]
}

# ---- terminal-aware editing, readback and checks ----------------------------------

# Pins of an instance with their actual coordinates (placement and rotation applied) and nets.
proc viaduct::op::pins {a} {
  set inst [dict get $a name]
  catch {xschem rebuild_connectivity}
  set items {}
  foreach pin [xschem instance_pins $inst] {
    lassign [xschem instance_pin_coord $inst name $pin] - x y
    set net {}
    catch {set net [xschem instance_net $inst $pin]}
    lappend items [viaduct::jobj [list pin [viaduct::jstr $pin] x $x y $y net [viaduct::jstr $net]]]
  }
  return [viaduct::jarr $items]
}

proc viaduct::pin_xy {inst pin} {
  if {[lsearch -exact [xschem instance_pins $inst] $pin] < 0} {
    error "$inst has no pin \"$pin\" (pins: [xschem instance_pins $inst])"
  }
  lassign [xschem instance_pin_coord $inst name $pin] - x y
  return [list $x $y]
}

# Direction a pin points out of its symbol: from the instance origin to the pin
# (falls back to the centroid of all pins when the pin sits on the origin).
proc viaduct::pin_dir {inst pin} {
  lassign [viaduct::pin_xy $inst $pin] px py
  lassign [lrange [xschem instance_coord $inst] 2 3] ox oy
  set dx [expr {$px - $ox}]; set dy [expr {$py - $oy}]
  if {abs($dx) < 1 && abs($dy) < 1} {
    set sx 0; set sy 0; set n 0
    foreach p [xschem instance_pins $inst] { lassign [viaduct::pin_xy $inst $p] x y; set sx [expr {$sx+$x}]; set sy [expr {$sy+$y}]; incr n }
    set dx [expr {$px - $sx/double($n)}]; set dy [expr {$py - $sy/double($n)}]
  }
  if {abs($dx) >= abs($dy)} { return [expr {$dx < 0 ? "left" : "right"}] }
  return [expr {$dy < 0 ? "up" : "down"}]
}

# Wire two instance pins: straight when aligned, else horizontal then vertical.
proc viaduct::op::wire_pins {a} {
  lassign [viaduct::pin_xy [dict get $a from] [dict get $a from_pin]] x1 y1
  lassign [viaduct::pin_xy [dict get $a to] [dict get $a to_pin]] x2 y2
  if {$x1 == $x2 || $y1 == $y2} {
    xschem wire $x1 $y1 $x2 $y2
    set pts [list $x1 $y1 $x2 $y2]
  } else {
    xschem wire $x1 $y1 $x2 $y1
    xschem wire $x2 $y1 $x2 $y2
    set pts [list $x1 $y1 $x2 $y1 $x2 $y2]
  }
  return [viaduct::jobj [list points [viaduct::jarr $pts]]]
}

# A short stub out of a pin, in the direction the pin faces, ending in a net label.
proc viaduct::op::label_pin {a} {
  set inst [dict get $a name]; set pin [dict get $a pin]; set net [dict get $a net]
  set len [expr {[dict exists $a length] ? [dict get $a length] : 40}]
  lassign [viaduct::pin_xy $inst $pin] x y
  set dir [viaduct::pin_dir $inst $pin]
  switch $dir {
    left  { set ex [expr {$x - $len}]; set ey $y; set rot 0 }
    right { set ex [expr {$x + $len}]; set ey $y; set rot 2 }
    up    { set ex $x; set ey [expr {$y - $len}]; set rot 1 }
    down  { set ex $x; set ey [expr {$y + $len}]; set rot 3 }
  }
  xschem wire $x $y $ex $ey
  viaduct::op::place [dict create symbol lab_pin.sym x $ex y $ey rot $rot flip 0 set [dict create lab $net]]
  return [viaduct::jobj [list pin [viaduct::jstr $pin] net [viaduct::jstr $net] direction [viaduct::jstr $dir] \
    end [viaduct::jarr [list $ex $ey]]]]
}

# Open an EXISTING schematic for editing (the counterpart of new_schematic / create).
proc viaduct::op::modify {a} {
  set path [dict get $a path]
  if {![file exists $path]} { error "no schematic at $path; use new_schematic to create one" }
  xschem load $path
  return [viaduct::jobj [list schematic [viaduct::jstr [xschem get schname]] modified [xschem get modified]]]
}

proc viaduct::label_like {sym} {
  return [expr {[file tail $sym] in {lab_pin.sym lab_wire.sym ipin.sym opin.sym iopin.sym gnd.sym vdd.sym}}]
}

# Connectivity read back from xschem: every instance pin with its net, and every net
# with its connections (device pins and labels separately).
proc viaduct::connectivity_data {} {
  catch {xschem rebuild_connectivity}
  # nets: net -> {pins {inst.pin ..} labels {inst ..}}
  set nets [dict create]
  set insts {}
  for {set i 0} {$i < [xschem get instances]} {incr i} {
    set name [xschem getprop instance $i name]
    set sym [xschem getprop instance $i cell::name]
    set pins {}
    foreach pin [xschem instance_pins $name] {
      set net {}
      catch {set net [xschem instance_net $name $pin]}
      lappend pins $pin $net
      if {$net eq {}} continue
      if {![dict exists $nets $net]} { dict set nets $net [dict create pins {} labels {}] }
      set d [dict get $nets $net]
      if {[viaduct::label_like $sym]} {
        dict lappend d labels $name
      } else {
        dict lappend d pins "$name.$pin"
      }
      dict set nets $net $d
    }
    lappend insts [list $name $sym $pins]
  }
  return [list $insts $nets]
}

proc viaduct::op::connectivity {a} {
  lassign [viaduct::connectivity_data] insts nets
  set ji {}
  foreach it $insts {
    lassign $it name sym pins
    set jp {}
    foreach {p n} $pins { lappend jp $p [viaduct::jstr $n] }
    lappend ji [viaduct::jobj [list name [viaduct::jstr $name] symbol [viaduct::jstr $sym] pins [viaduct::jobj $jp]]]
  }
  set jn {}
  dict for {net d} $nets {
    set p [expr {[dict exists $d pins] ? [dict get $d pins] : {}}]
    set l [expr {[dict exists $d labels] ? [dict get $d labels] : {}}]
    set pj {}; foreach x $p { lappend pj [viaduct::jstr $x] }
    lappend jn $net [viaduct::jobj [list pins [viaduct::jarr $pj] labels [llength $l]]]
  }
  return [viaduct::jobj [list instances [viaduct::jarr $ji] nets [viaduct::jobj $jn]]]
}

# Electrical sanity check: device pins left on a net of their own (floating / not wired)
# and labels that name a net no device pin reaches.
proc viaduct::op::check {a} {
  lassign [viaduct::connectivity_data] insts nets
  set warnings {}
  dict for {net d} $nets {
    set p [expr {[dict exists $d pins] ? [dict get $d pins] : {}}]
    set l [expr {[dict exists $d labels] ? [dict get $d labels] : {}}]
    if {[llength $p] == 1 && [llength $l] == 0} {
      lappend warnings [viaduct::jobj [list kind [viaduct::jstr floating_pin] net [viaduct::jstr $net] \
        where [viaduct::jstr [lindex $p 0]] message [viaduct::jstr "[lindex $p 0] is not connected to anything"]]]
    } elseif {[llength $p] == 0 && [llength $l] > 0 && $net ni {0 GND gnd}} {
      lappend warnings [viaduct::jobj [list kind [viaduct::jstr label_only] net [viaduct::jstr $net] \
        where [viaduct::jstr [join $l ,]] message [viaduct::jstr "net $net has labels but no device pin"]]]
    } elseif {[llength $p] == 1 && [llength $l] > 0} {
      lappend warnings [viaduct::jobj [list kind [viaduct::jstr single_pin_net] net [viaduct::jstr $net] \
        where [viaduct::jstr [lindex $p 0]] message [viaduct::jstr "net $net reaches only [lindex $p 0]"]]]
    }
  }
  return [viaduct::jobj [list ok [expr {[llength $warnings] == 0 ? "true" : "false"}] \
    nets [dict size $nets] instances [llength $insts] warnings [viaduct::jarr $warnings]]]
}

# ---- dialogs, readback, lifecycle ---------------------------------------------

proc viaduct::modal_windows {} {
  set out {}
  foreach w [winfo children .] {
    if {[winfo toplevel $w] ne $w || ![winfo ismapped $w]} continue
    if {[string match .__tk__* $w] || [string match .bgerror* $w] || [wm transient $w] ne {} || [grab current] eq $w} {
      lappend out $w
    }
  }
  return $out
}

# Buttons of a dialog (any depth): list of {widget text}.
proc viaduct::dialog_buttons {w} {
  set out {}
  set stack [winfo children $w]
  while {[llength $stack]} {
    set c [lindex $stack 0]
    set stack [lrange $stack 1 end]
    if {[winfo class $c] in {Button TButton}} {
      set t {}
      catch { set t [$c cget -text] }
      lappend out [list $c $t]
    }
    lappend stack {*}[winfo children $c]
  }
  return $out
}

proc viaduct::dialog_info {w} {
  set txt {}
  foreach c [winfo children $w] {
    if {[winfo class $c] in {Button TButton}} continue
    catch { append txt [$c cget -text] " " }
    foreach cc [winfo children $c] {
      if {[winfo class $cc] in {Button TButton}} continue
      catch { append txt [$cc cget -text] " " }
    }
  }
  set buttons {}
  foreach b [viaduct::dialog_buttons $w] { lappend buttons [viaduct::jstr [lindex $b 1]] }
  return [viaduct::jobj [list id [viaduct::jstr $w] title [viaduct::jstr [wm title $w]] \
    text [viaduct::jstr [string trim $txt]] buttons [viaduct::jarr $buttons]]]
}

# Read-only: visible dialogs. Their origin (designer or script) cannot be told apart.
proc viaduct::op::dialogs {a} {
  set items {}
  foreach w [viaduct::modal_windows] { lappend items [viaduct::dialog_info $w] }
  return [viaduct::jarr $items]
}

# Close ONE dialog the designer agreed to close. id and expected_title come from dialogs()
# and are re-checked; action is "close" (window close, usually = Cancel) or
# "button:<text>" to press one named button.
proc viaduct::op::close_dialog {a} {
  set w [dict get $a id]
  set want [dict get $a expected_title]
  set action [expr {[dict exists $a action] ? [dict get $a action] : "close"}]
  if {$w ni [viaduct::modal_windows]} { error "no open dialog with id $w (already closed?)" }
  set info [viaduct::dialog_info $w]
  if {[wm title $w] ne $want} { error "dialog $w is now titled \"[wm title $w]\", not \"$want\"; inspect again" }
  if {$action eq "close"} {
    set handler [wm protocol $w WM_DELETE_WINDOW]
    if {$handler ne {}} { after 0 [list uplevel #0 $handler] } else { after 0 [list destroy $w] }
  } elseif {[string match "button:*" $action]} {
    set label [string range $action 7 end]
    set hit {}
    foreach b [viaduct::dialog_buttons $w] { if {[lindex $b 1] eq $label} { set hit [lindex $b 0]; break } }
    if {$hit eq {}} {
      set names {}
      foreach b [viaduct::dialog_buttons $w] { lappend names [lindex $b 1] }
      error "dialog $w has no button \"$label\" (buttons: $names)"
    }
    after 0 [list $hit invoke]
  } else {
    error "action must be \"close\" or \"button:<text>\""
  }
  return [viaduct::jobj [list requested [viaduct::jstr $action] dialog $info]]
}

# Legacy bulk close of EVERY visible dialog, including the designer's own. Refused unless
# confirm_all is set; prefer dialogs + close_dialog.
proc viaduct::op::dismiss_dialogs {a} {
  if {!([dict exists $a confirm_all] && [dict get $a confirm_all])} {
    error "bulk dismissal closes the designer's dialogs too; pass confirm_all only when told to, or use close_dialog"
  }
  set closed [viaduct::op::dialogs {}]
  foreach w [viaduct::modal_windows] {
    set done 0
    foreach b {ok cancel no yes} {
      if {[winfo exists $w.$b]} { after 0 [list $w.$b invoke]; set done 1; break }
    }
    if {!$done} { after 0 [list destroy $w] }
  }
  return [viaduct::jobj [list closed $closed]]
}

# ---- history (time scroll) --------------------------------------------------------

proc viaduct::sch_escape {s} {
  return [string map [list \\ \\\\ \{ \\\{ \} \\\}] $s]
}

# Write the schematic as it is in memory (unsaved edits included) to `path`, without
# touching the window's file name, its modified flag, the undo history, the designer's
# clipboard or their selection. The body comes from xschem's own copy of all objects;
# the global attributes are added as the file header.
proc viaduct::op::history_snapshot {a} {
  set path [dict get $a path]
  set clip [file join $::USER_CONF_DIR .clipboard.sch]
  set saved {}
  if {[file exists $clip]} { set f [open $clip rb]; set saved [read $f]; close $f; file delete $clip }
  set sel [xschem selected_set]
  xschem select_all
  xschem copy
  xschem unselect_all
  set body {}
  if {[file exists $clip]} { set f [open $clip rb]; set body [read $f]; close $f; file delete $clip }
  if {$saved ne {}} { set f [open $clip wb]; puts -nonewline $f $saved; close $f }
  foreach n $sel { catch {xschem select instance $n} }
  set version {}
  set objects {}
  foreach line [split $body \n] {
    if {[string match {v \{*} $line]} { set version $line; continue }
    if {[string match {G \{*\}} $line] && $objects eq {}} continue  ;# clipboard anchor, not a property
    lappend objects $line
  }
  if {$version eq {}} { set version "v {xschem version=[xschem get version] file_version=1.3}" }
  set header [list $version]
  foreach {tag prop} {G schvhdlprop K schsymbolprop V schverilogprop S schprop F schspectreprop E schtedaxprop} {
    set val {}
    catch {set val [xschem get $prop]}
    lappend header "$tag \{[viaduct::sch_escape $val]\}"
  }
  file mkdir [file dirname $path]
  set f [open $path wb]
  puts -nonewline $f "[join $header \n]\n[string trimright [join $objects \n]]\n"
  close $f
  return [viaduct::jobj [list path [viaduct::jstr $path] schematic [viaduct::jstr [xschem get schname]] \
    modified [xschem get modified] instances [xschem get instances]]]
}

# A hash of what the schematic contains (instances with their place and attributes,
# wires), not of how it is shown: zoom and selection do not change it. The relay compares
# it with the value after its own last edit to tell a hand edit in the GUI.
proc viaduct::op::fingerprint {a} {
  set parts {}
  set n [xschem get instances]
  for {set i 0} {$i < $n} {incr i} {
    set name [xschem getprop instance $i name]
    lappend parts [xschem instance_coord $name] [xschem getprop instance $i]
  }
  set nw [xschem get wires]
  for {set i 0} {$i < $nw} {incr i} { lappend parts [xschem wire_coord $i] }
  return [viaduct::jobj [list schematic [viaduct::jstr [xschem get schname]] instances $n wires $nw \
    sha [viaduct::jstr [string range [::sha2::sha256 -hex [join $parts \n]] 0 15]]]]
}

# Bring a snapshot back into this window: the snapshot is copied over the open
# schematic's file (the caller keeps a snapshot of the state it replaces) and reloaded.
proc viaduct::op::history_restore {a} {
  set src [dict get $a src]
  set target [expr {[dict exists $a target] && [dict get $a target] ne {} ? [dict get $a target] : [xschem get schname]}]
  file copy -force $src $target
  xschem load -noundoreset -nofullzoom $target
  return [viaduct::jobj [list schematic [viaduct::jstr [xschem get schname]] instances [xschem get instances] \
    modified [xschem get modified]]]
}

proc viaduct::op::selection {a} {
  set items {}
  foreach name [xschem selected_set] {
    lappend items [viaduct::describe_instance $name]
  }
  return [viaduct::jarr $items]
}

proc viaduct::op::snapshot {a} {
  return [viaduct::jobj [list design [viaduct::op::describe {}] \
    selection [viaduct::op::selection {}] dialogs [viaduct::op::dialogs {}] \
    netlist_dir [viaduct::jstr [expr {[info exists ::netlist_dir] ? $::netlist_dir : {}}]]]]
}

proc viaduct::op::stop {a} {
  set force [expr {[dict exists $a force] && [dict get $a force]}]
  if {[xschem get modified] && !$force} { error "unsaved schematic [xschem get schname]; save it or pass force" }
  after 200 { xschem exit closewindow force }
  return [viaduct::jobj [list stopping true]]
}

# Re-source this file: refreshes every op; the running server is kept.
proc viaduct::op::reload {a} {
  uplevel #0 [list source $::viaduct::source_file]
  return [viaduct::jobj [list tap [viaduct::jstr $::viaduct::version]]]
}

# ---- server -----------------------------------------------------------------

proc viaduct::read_token {} {
  variable dir
  file mkdir $dir
  file attributes $dir -permissions 0700
  set path [file join $dir xschem.token]
  if {![file exists $path]} {
    set r [open /dev/urandom rb]; set raw [read $r 32]; close $r
    set f [open $path {WRONLY CREAT EXCL} 0600]
    puts -nonewline $f [binary encode hex $raw]
    close $f
  }
  set f [open $path]; set t [string trim [read $f]]; close $f
  return $t
}

proc viaduct::accept {sock addr port} {
  fconfigure $sock -buffering line -blocking 0 -translation lf -encoding binary
  fileevent $sock readable [list viaduct::on_readable $sock]
}

proc viaduct::on_readable {sock} {
  if {[catch {gets $sock line} n] || $n < 0} {
    if {[catch {eof $sock} at_eof] || $at_eof} { catch {close $sock} }
    return
  }
  if {[string trim $line] eq {}} return
  # Always answer, so a tap bug never leaves the client waiting or pops a Tk error dialog.
  if {[catch {viaduct::handle $line} reply]} {
    set reply "ERR [binary encode base64 [encoding convertto utf-8 "tap error: $reply"]]"
  }
  # A dialog may have held this request past the client's timeout; the client then closed
  # the connection (handled in a nested event loop), so the channel can be gone by now.
  # Drop the reply quietly instead of raising a Tk error dialog on the designer's desktop.
  catch {puts $sock $reply; flush $sock}
}

proc viaduct::sign {nonce kind payload} {
  variable token
  return "$kind $payload [::sha2::hmac -hex -key $token "$nonce$kind$payload"]"
}

proc viaduct::reply {nonce kind text} {
  return [viaduct::sign $nonce $kind [binary encode base64 [encoding convertto utf-8 $text]]]
}

# Ops that are not tracked as receipts (read-only / the receipt query itself).
proc viaduct::untracked {script} {
  foreach op {receipt hello ping dialogs} {
    if {[string match "viaduct::op::$op *" $script] || $script eq "viaduct::op::$op"} { return 1 }
  }
  return 0
}

proc viaduct::handle {line} {
  variable token
  variable seen
  variable receipts
  variable proto
  lassign [split $line " "] nonce mac b64 rid rproto
  if {$rproto eq {}} { return "DENIED old-protocol (relay predates protocol $proto; update the relay)" }
  if {[catch {binary decode base64 $b64} raw]} { return [viaduct::sign $nonce DENIED [binary encode base64 bad-encoding]] }
  set expected [::sha2::hmac -hex -key $token "$nonce$rid$rproto$raw"]
  if {$mac ne $expected} { return "DENIED bad-signature" }
  set now [clock seconds]
  dict for {k t} $seen { if {$now - $t > 900} { dict unset seen $k } }
  if {[dict exists $seen $nonce]} { return [viaduct::reply $nonce DENIED "replayed nonce"] }
  dict set seen $nonce $now
  if {$rproto != $proto} { return [viaduct::reply $nonce DENIED "protocol $rproto, tap speaks $proto"] }
  set script [encoding convertfrom utf-8 $raw]
  set track [expr {$rid ne {} && $rid ne "-" && ![viaduct::untracked $script]}]
  if {$track} {
    if {[dict exists $receipts $rid]} {
      return [viaduct::reply $nonce DENIED "request id $rid was already submitted; query its receipt, do not resend"]
    }
    viaduct::prune_receipts
    dict set receipts $rid [dict create state running started $now script [string range $script 0 200]]
  }
  set code [catch {uplevel #0 $script} res opts]
  # 0 = ok, 2 = script used `return`: both are results, not errors.
  if {$code != 0 && $code != 2} {
    set kind ERR
    set text [expr {[dict exists $opts -errorinfo] ? [dict get $opts -errorinfo] : $res}]
  } else {
    set kind OK
    set text $res
  }
  if {$track} {
    dict set receipts $rid state completed
    dict set receipts $rid finished [clock seconds]
    dict set receipts $rid kind $kind
    dict set receipts $rid payload [binary encode base64 [encoding convertto utf-8 $text]]
  }
  return [viaduct::reply $nonce $kind $text]
}

proc viaduct::prune_receipts {} {
  variable receipts
  set now [clock seconds]
  dict for {k r} $receipts {
    if {[dict get $r state] eq "completed" && $now - [dict get $r finished] > 3600} { dict unset receipts $k }
  }
  # bounded: drop the oldest completed ones beyond 2000 entries
  while {[dict size $receipts] > 2000} {
    set dropped 0
    dict for {k r} $receipts {
      if {[dict get $r state] eq "completed"} { dict unset receipts $k; set dropped 1; break }
    }
    if {!$dropped} break
  }
}

# Handshake: protocol, version, capabilities; changes nothing.
proc viaduct::op::hello {a} {
  upvar #0 ::viaduct::version version ::viaduct::proto proto
  return [viaduct::jobj [list proto $proto tap [viaduct::jstr $version] pid [pid] \
    xschem [viaduct::jstr [xschem get version]] receipts true server_time [clock seconds]]]
}

# What happened to an earlier request: unknown | running | completed (+ its reply).
proc viaduct::op::receipt {a} {
  upvar #0 ::viaduct::receipts receipts
  set rid [dict get $a request_id]
  if {![dict exists $receipts $rid]} {
    return [viaduct::jobj [list request_id [viaduct::jstr $rid] state [viaduct::jstr unknown]]]
  }
  set r [dict get $receipts $rid]
  set items [list request_id [viaduct::jstr $rid] state [viaduct::jstr [dict get $r state]] \
    started [dict get $r started] script [viaduct::jstr [dict get $r script]]]
  if {[dict get $r state] eq "completed"} {
    lappend items finished [dict get $r finished] kind [viaduct::jstr [dict get $r kind]] \
      payload_b64 [viaduct::jstr [dict get $r payload]]
  }
  return [viaduct::jobj $items]
}

proc viaduct::start {} {
  variable server
  variable port
  variable dir
  variable token [read_token]
  if {[info exists server]} return
  if {[catch {socket -server viaduct::accept -myaddr 127.0.0.1 $port} chan]} {
    # Another xschem already owns the tap port; this one stays a plain xschem.
    puts "\[viaduct\] tap not started, 127.0.0.1:$port busy: $chan"
    return
  }
  set server $chan
  set f [open [file join $dir xschem.json] w]
  puts $f [jobj [list port $port pid [pid] tap [jstr $::viaduct::version] started [clock seconds]]]
  close $f
  puts "\[viaduct\] xschem tap listening on 127.0.0.1:$port"
}

set ::viaduct::source_file [info script]
viaduct::start
