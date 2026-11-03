---
name: viaduct-klayout
description: Edit the live KLayout window through Viaduct - open/new layouts, place and edit the VIADUCT_SKY130 T-coil PCell, add shapes, read back selection and parameters, screenshot, hot-reload device code. Use for any layout task in the open-source flow.
---

# KLayout through Viaduct

Everything runs inside the KLayout process on the noVNC desktop, on its GUI
thread: edits redraw at once and each structured edit is one undo step.

## API (PowerShell from the repo root, or Python `vd.klayout.*`, or MCP `klayout_*`)

| Task | CLI | Python |
|---|---|---|
| state of the window | `python client.py snapshot` | `vd.klayout.snapshot()` |
| new layout view | `python client.py new-layout TCOIL_DEMO` | `vd.klayout.new_layout("TCOIL_DEMO")` |
| open a file | `python client.py open /foss/designs/x.gds` | `vd.klayout.open(path)` |
| place T-coil | `python client.py tcoil --set metalWidth=4 area=6400` | `vd.klayout.place_tcoil("DUT", params={...})` |
| change parameters | `python client.py set DUT --set turnSpacing=3` | `vd.klayout.set_pcell_params("DUT", turnSpacing=3.0)` |
| read back | `python client.py describe --name DUT` | `vd.klayout.describe("DUT")` |
| designer's selection | `python client.py selection` | `vd.klayout.selection()` |
| shapes / labels | `python client.py add-box 72 20 x1 y1 x2 y2` | `vd.klayout.add_shapes(72, 20, boxes=[[...]])` |
| screenshot | `python client.py screenshot` | `vd.klayout.screenshot().result["local_path"]` |
| hot-reload device code | `python client.py use-library` | `vd.klayout.use_library("tcoil")` |
| EM results into PCell | `python client.py annotate --set L1=.. --run-id ID` | `vd.klayout.annotate("DUT", results, run_id)` |
| save | `python client.py save /foss/designs/viaduct/runs/x.gds` | `vd.klayout.save(path)` |
| Python inside KLayout | `python client.py eval "result = view.title"` | `vd.klayout.eval(code)` |

**Batch first.** Several edits in one request are one round trip and ONE undo step:

```python
with vd.klayout.batch() as b:
    b.new_layout("TCOIL_DEMO")
    b.place_tcoil("DUT", params={"metalWidth": 4.0, "area": 8000.0})
    b.add_shapes(72, 20, boxes=[[60, -10, 70, 10]])
    b.set_pcell_params("DUT", turnSpacing=3.0)
```

A batch stops at the first failing op (`done`, `failure`); hierarchy/zoom refresh once
at the end. CLI `python client.py batch ops.json`; MCP `klayout_batch`.

Instances placed by Viaduct are named (`--name`, default `DUT`) through the
`viaduct_name` property; `describe`/`set` find them by that name.

## T-coil PCell (devices/tcoil, library VIADUCT_SKY130)

Parameters: `metalWidth` (um, 0.01 grid), `area` (um^2 envelope budget, not
metal area), `turnSpacing` (um; 0 = reference gap, actual 1.94 um at W=4,
area=6400), `upperMetal`/`lowerMetal` (met1..met5, upper above lower),
`upperCrossover`/`lowerCrossover` (e.g. `met1+met2+met3`, must not use a winding
metal), `upperViaChain`/`lowerViaChain`/`parallelViaChain` (`Auto` or the full chain).
Invalid combinations raise an error and leave the instance unchanged.
Ports: P1, P2 (leads, bottom) and P3 (tap, inner turn left side). The tap is
off-centre electrically: P1-P3 is about 3/4 of the inner turn, P2-P3 about 1/4.

Read-only: `actualTurnSpacing`, `resultStatus`, `L1`, `L2`, `Q1`, `Q2`, `K1`,
`K2`. RF fields stay `--`/`NOT_RUN` until `annotate` with an EM run ID, and
reset when any geometry parameter changes.

## Pitfalls

- After editing `devices/tcoil/*.py`, run `use-library`; existing instances regenerate.
- After editing `taps/klayout/viaduct_tap.py`, run `reload` (no KLayout restart).
- A `TIMEOUT` with `dialogs` means a modal dialog is open (KLayout's startup "Tip"
  is one). Report it to the designer; close it only with their OK, by id + exact title
  (`close-dialog ID --title T --action button:OK`). The timed-out request may still run
  after the dialog closes: never resend it; `receipt REQUEST_ID` (id from the timeout reply)
  says `running` or `completed` with the original reply.
- The designer may edit the same instance by hand (Q / Properties): call `describe`
  before assuming parameters.
- Layer numbers (SKY130): met1..met5 = 68..72 / 20, via1..via4 = 68..71 / 44,
  pins datatype 16, labels datatype 5 (pdk/sky130A.json).
