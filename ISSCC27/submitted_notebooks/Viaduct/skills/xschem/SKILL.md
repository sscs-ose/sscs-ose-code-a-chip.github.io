---
name: viaduct-xschem
description: Build and edit schematics in the live xschem window through Viaduct - new/modify schematic, place SKY130 symbols, wire by pin name, label pins, set properties, read back connectivity, check, netlist, screenshot. Use for any schematic or testbench task in the open-source flow.
---

# xschem through Viaduct

Commands run inside the xschem process on the noVNC desktop (Tk event loop);
the schematic redraws as you edit. Add `-t xschem` to CLI commands.

## API

| Task | CLI (`python client.py -t xschem ...`) | Python |
|---|---|---|
| new schematic | `new-schematic /foss/designs/viaduct/xschem/tb.sch [--replace]` | `vd.xschem.new_schematic(path, replace)` |
| open / edit existing | `open PATH` / `modify PATH` (error if missing) | `vd.xschem.open(path)`, `.modify(path)` |
| place symbol | `place sky130_fd_pr/nfet_01v8.sym 0 0` | `vd.xschem.place(sym, x, y, rot)` |
| set properties | `set M1 --set W=4 L=0.15` | `vd.xschem.set_props("M1", {"W": "4"})` |
| wire | `wire x1 y1 x2 y2 [x3 y3 ...]` | `vd.xschem.wire(x1, y1, x2, y2)` |
| pins of an instance | `pins M1` (name, x, y, net) | `vd.xschem.pins("M1")` |
| wire pin to pin | `wire-pins R1 M M1 D` (straight or L) | `vd.xschem.wire_pins("R1", "M", "M1", "D")` |
| net label on a pin | `label-pin M1 G IN [--length 40]` (stub faces outward) | `vd.xschem.label_pin("M1", "G", "IN")` |
| connectivity | `connectivity` (instance pin -> net, net -> pins, labels) | `vd.xschem.connectivity()` |
| check | `check` (floating_pin, single_pin_net, label_only) | `vd.xschem.check()` |
| read back | `describe` / `selection` / `snapshot` | `vd.xschem.describe()` |
| netlist | `netlist` | `vd.xschem.netlist()` (path + text) |
| save / screenshot | `save` / `screenshot` | `vd.xschem.save()`, `.screenshot()` |
| Tcl inside xschem | `eval "xschem get schname"` | `vd.xschem.eval(code)` |

**Batch first.** Every single call costs one round trip (~0.8 s). Queue a whole
schematic and send it as ONE request (drawing suspended, one redraw): ~1 s instead of
~25 s for the 30-element CS-amplifier testbench, with an identical netlist. A batch stops at the first failing op and reports
`done`, `total` and `failure {index, op, error}`; ops before it stay applied.

```python
with vd.xschem.batch() as b:                      # sent on exit, raises on failure
    b.place("sky130_fd_pr/nfet_01v8.sym", 0, 0, name="M1", W="4", L="0.15")
    b.place("res.sym", 20, -100, name="R1", value="2k")
    b.wire(20, -70, 20, -30)
    b.add("netlist")                                # any op by name
print(b.result.result["results"][-1]["path"])
```

CLI: `python client.py -t xschem batch ops.json` with `[{"op": "place", "args": {...}}, ...]`.
MCP: `xschem_batch`. `place` takes `set: {name, W, value, lab, ...}` so no follow-up call
is needed; a missing symbol is an error (xschem itself would silently place an empty instance).

Builder helper (batched by default; keeps PDK template properties, then sets yours):

```python
from viaduct import Viaduct
from viaduct.schematic import Builder
sb = Builder(Viaduct.from_env())
sb.new("/foss/designs/viaduct/xschem/tb.sch", replace=True)
sb.place("sky130_fd_pr/nfet_01v8.sym", 0, 0, name="M1", W="10", L="0.15", nf="1")
sb.place("res.sym", 20, -160, name="R1", value="2k")
sb.connect("R1", "M", "M1", "D")                 # by pin name
sb.label_pin("R1", "P", "VDD"); sb.label_pin("M1", "G", "IN"); sb.label_pin("M1", "S", "GND")
sb.place("sky130_fd_pr/corner.sym", -300, 120, corner="tt")
sb.code(100, 120, ".control\nac dec 20 1e6 1e11\nwrite tb.raw\n.endc")
netlist = sb.finish()          # ONE request: everything above + save, zoom, netlist
```

Then verify from xschem's own connectivity, not from the picture:
`vd.xschem.check()` -> `{ok, warnings: [{kind, net, where, message}]}`
(e.g. `floating_pin M1.B` until the body is labelled).

## A readable schematic (what the designer expects)

The schematic is for the designer to read, not only for the netlister. A schematic made of
pins with a label on every stub netlists correctly but reads like a netlist.

- **Layout by function**: VDD at the top, GND at the bottom, inputs on the left, output on the
  right. PMOS above NMOS. Mirror and differential pairs side by side, the right device flipped
  (`flip=1`) so the gates of a mirror face each other and the pair's gates face outward.
- **Wires for the circuit's own nets**: connect drains, mirror gates, sources and tail nodes with
  `wire_pins` (straight or L). A diode connection is `wire_pins("M3", "D", "M3", "G")`.
- **Labels only for ports and supplies** (`label_pin`): INP, INN, OUT, VDD, GND, and a bias net
  that crosses between blocks. An internal net joined only by two labels is a readability defect
  (the experiment evaluator counts them as `label_joined_internal_nets`).
- **Testbench apart**: supply / input sources, the load, the corner and the code block in a
  corner of the sheet, not between the devices.
- Build it in one `batch` (no half-wired intermediate states), then `check`, `connectivity` and a
  `screenshot`; fix overlapping texts by spacing the columns (about 240 units between a pair).

```python
with vd.xschem.batch() as b:
    b.add("new_schematic", path=PATH, replace=True)
    b.place(P, 0, -200, flip=1, name="M3", W=WL, L=LL); b.place(P, 200, -200, name="M4", W=WL, L=LL)
    b.place(N, -40, 0, name="M1", W=WI, L=LI);          b.place(N, 240, 0, flip=1, name="M2", W=WI, L=LI)
    b.place(N, 80, 150, name="M5", W=WT, L=LT)          # sizes are yours to choose
    b.wire_pins("M3", "D", "M1", "D"); b.wire_pins("M4", "D", "M2", "D")
    b.wire_pins("M3", "G", "M4", "G"); b.wire_pins("M3", "D", "M3", "G")
    b.wire_pins("M1", "S", "M5", "D"); b.wire(220, 30, 100, 30)
    b.label_pin("M1", "G", "INP"); b.label_pin("M2", "G", "INN")
    b.label_pin("M3", "S", "VDD"); b.label_pin("M5", "S", "GND")   # ... bulks, OUT, bias
```

## Coordinates and pins (rotation 0, y grows downward)

- nfet_01v8 / pfet_01v8: D(20,-30) G(-20,0) S(20,30) B(20,0)
- res.sym, capa.sym, ind.sym, vsource.sym, isource.sym: pins at (0,-30) top, (0,30) bottom
- gnd.sym, lab_pin.sym: pin at (0,0). Net names come from `lab_pin` `lab=`; gnd is net 0.
- A wire end that lands on a pin or on another wire end connects. Keep to a 10 grid.
- Symbol pins for anything else: read the .sym (`B 5 ...` lines) with `eval`.

## Pitfalls

- An edit that returns `INTERRUPTED` did nothing: the designer interrupted you (instruction,
  pause, or a hand edit whose change is in the reply). Read it, `interrupt-ack`, apply it and
  continue on the current schematic. Do not rebuild it with `new_schematic replace=True`, do
  not reset sizes they set. See AGENTS.md, "Designer interrupts come first".

- Modal dialogs (tk_messageBox, Tk "Application Error") block requests. `dialogs` lists them
  read-only with id (window path), title, text, buttons; close one only with the designer's
  OK: `close-dialog .__tk__messagebox --title "..." --action button:OK`. A request it blocked
  times out with a `request_id`; `receipt ID` shows `running`, then `completed` with the
  original reply once the dialog is closed. Never resend it.

- Placing with an empty property string would drop the PDK template; `place` without
  `props` keeps it. Set properties afterwards (`set_props`), rename last.
- `new-schematic` refuses an existing file unless `--replace` (which discards unsaved edits).
- `netlist` sets SPICE mode and `simulation/` next to the schematic automatically; without
  that xschem shows a modal "Please Set netlisting mode" box.
- Models: place `sky130_fd_pr/corner.sym` (corner=tt) so the netlist includes the SKY130 lib.
- The analyses come from your code block (`.control ... .endc`); write a .raw with `write`.
