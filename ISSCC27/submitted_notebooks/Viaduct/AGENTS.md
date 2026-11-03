# Viaduct — instructions for coding agents

Viaduct drives the KLayout and xschem windows the designer is watching on the
noVNC desktop (http://localhost:18080/vnc.html?autoconnect=true&reconnect=true&reconnect_delay=3000&resize=remote), and runs ngspice and FastHenry in the
IIC-OSIC-TOOLS container. Your edits appear live in those windows. Treat them
like a colleague's open Virtuoso session: change only what you were asked to.

## Shortest path for a design task

1. `status`; read `skills/xschem/SKILL.md` ("A readable schematic") and `skills/ngspice/SKILL.md`.
2. Build the schematic in **one batch** (place with sizes, `wire_pins`, `label_pin` for ports only).
3. `check` must be `ok`; then `simulate --nodes out` (or `vd.sim.xschem`) and `sim-op` for the bias.
   A `.control` block without `write` is completed automatically; an `ac` magnitude must be set on
   an input source or the AC result is zero (the reply warns).
4. Change sizes with `set_props` (paired devices in the same batch), simulate again; repeat.
5. `screenshot`, `save`; report metrics with their run IDs.

## Before anything else

1. `python client.py status` (PowerShell, from this folder) or MCP `viaduct_status`.
   - container not `Up` → `wsl -d Ubuntu --exec docker start opencad-desktop`
   - a tap not `alive` → `python client.py start`
   - WSL is kept running by `%USERPROFILE%\.wslconfig` (`vmIdleTimeout=-1`) and the
     logon task "Viaduct WSL keep-alive"; the container restarts with WSL
     (`--restart unless-stopped`). If it is down anyway (after `wsl --shutdown`):
     `Start-ScheduledTask "Viaduct WSL keep-alive"`.
2. If any call returns `TIMEOUT`, read its `dialogs` field and tell the designer what
   the dialog says (title, text, buttons). The request's outcome is **unknown**: it may
   still run once the dialog closes, so do **not** resend it. Every reply carries a
   `request_id`; ask for its outcome with `receipt -t TOOL ID` (MCP `viaduct_receipt`):
   `running` -> still blocked, `completed` -> includes the original reply. The taps refuse
   a reused id.
3. Use PowerShell or cmd. Git Bash rewrites `/foss/...` arguments into Windows paths.
4. Work that the designer does not need to watch (sweeps, batch studies, CI) can run in
   `--mode headless`: same commands, invisible display, separate from their windows.

## Rules

- **Screenshot after every geometric or schematic edit** (`screenshot`, MCP
  `*_screenshot`) and look at it before reporting success.
- **Never fill result fields without a run ID.** PCell RF fields (L1, L2, Q1,
  Q2, K1, K2) are written only with `annotate`, using values and the `run_id`
  from an executed `em` run. Changing geometry resets them; that is intended.
- **Say exactly what DRC means.** `drc` runs the SKY130 community deck (256 rules);
  report "clean against the community deck, run <id>", never "signoff". No LVS yet.
- **Dialogs belong to the designer.** A dialog's origin (their click or your request)
  cannot be told apart. Inspect with `dialogs` (read-only). Close one only after the
  designer agrees, by id, exact title and a named action:
  `close-dialog ID --title TITLE --action button:OK`. Never close dialogs just to
  unblock yourself; `start` reports them and leaves them open. `dismiss-dialog --all`
  (closes everything, theirs included) only when the designer explicitly asks for it.
- **Time scroll.** Every successful edit is a history step (the reply carries `history_step`).
  Before a risky change record a `checkpoint LABEL`; when the designer asks to go back, `history`
  then `restore STEP` (the replaced state is recorded first, nothing is lost). Tell the designer
  the step numbers you created. `timeline` writes an HTML page with a screenshot per step.
- **Designer interrupts come first.** The designer can interrupt you at any time: an
  instruction (`interrupt "..."` or the cockpit page, with what they had selected), a pause, a
  restore of an earlier step, or simply an edit by
  hand in xschem / KLayout (detected from the design itself). While one is unacknowledged your
  edits return `INTERRUPTED` and change nothing; reads still work and carry `interrupts_pending`.
  Then: (1) read the reply (or `interrupts`, MCP `viaduct_interrupts`): the instruction, the
  selection, and for a hand edit the exact change (`changed` / `added` / `removed` / wires);
  (2) `interrupt-ack --note "what you will do"`; (3) apply the instruction or keep their edit,
  re-simulate if it matters; (4) update your plan and continue **from the modified design**.
  Never rebuild the schematic or reset values the designer set (`new-schematic --replace` on a
  file they edited is DENIED). A pause blocks you until the designer runs `resume`: wait, do not
  work around it. Keep your remaining steps in `plan set STEP ...` / `plan done N` (MCP
  `viaduct_plan`) so the designer sees where you are and you can resume after an interrupt.
- **Batch edits.** Use `batch` (Python `vd.<tool>.batch()`, CLI `batch ops.json`, MCP
  `*_batch`) for more than a couple of edits: one round trip instead of ~0.8 s each,
  one undo step in KLayout. Read `failure`/`done` when a batch stops early.
- **Wire schematics by pin name, then check.** `wire-pins A PIN B PIN` and
  `label-pin INST PIN NET` instead of computing coordinates; verify with `connectivity`
  (pin -> net read back from xschem) and `check` (floating pins, single-pin / label-only
  nets) before netlisting. Edit existing files with `modify PATH`, not `new-schematic`.
- **Trust only signed replies.** Taps sign every reply with the session token (protocol 2,
  `hello`). A `DENIED ... signature mismatch` means something else answered on the port:
  stop and tell the designer; do not work around it.
- **Prefer structured ops** (`place_tcoil`, `set`, `place`, `wire`, `set_props`)
  over `eval`. `eval` is developer mode and is refused in safe mode.
- **Do not overwrite designs you did not create.** `new-schematic` refuses an
  existing file unless `--replace`; `stop` refuses unsaved work unless `--force`.
  Ask before using either flag on someone else's file.
- **Report numbers with their run ID and run directory** (`runs/sim_<id>/`,
  `runs/em_<id>/`), and say which model produced them (ideal, FastHenry quasi-static).
- Paths given to tools are container paths (`/foss/designs/...`). Results include
  `local_path` / `local_run_dir` for reading files from Windows.

## Map

| Want to | Use |
|---|---|
| layout, PCells, selection, shapes | skills/klayout |
| schematics, netlists | skills/xschem |
| simulate, metrics, waveforms | skills/ngspice |
| L, R, Q, k and parasitic C of the T-coil | skills/em |
| size L/k, sweep, closed loop | skills/optimizer |
| DRC (markers in KLayout), LVS status | skills/verify |

Python API: `from viaduct import Viaduct; vd = Viaduct.from_env()`; every call
returns a `Result` (`.ok`, `.result`, `.error`, `.check()`).
MCP: `viaduct mcp` / `.mcp.json` (Claude Code picks it up in this folder).
Audit trail of every request: `python client.py audit`.
