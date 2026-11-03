# Inspect saved simulation waveforms and project files

Open **06 Local Netlist Simulation**, **10 Global Netlist Simulation** or
**14 Post-layout Verification**, select the saved run, and choose
**Simulation waveform → Open saved waveform**. This reads saved evidence only.
It does not start a simulator, change RTL or expected values, save a design,
record a review, or change adoption.

The viewer shows signals on a common nanosecond time axis. Use the signal
checkboxes and **Find signal** under **Select signals**, **Zoom in / Zoom out / Fit waveform**, and
**Cursor (ns)** to inspect a value. Separate rows distinguish these sources:

| Row | Meaning |
|---|---|
| VCD observed | Transitions retained in the actual simulation VCD, including X/Z |
| Observed samples | Actual output values recorded at the original assertion times; no line claims intermediate transitions |
| Saved stimulus | Declared testbench drive, clock and reset schedule; explicitly not a recorded output observation |
| Saved expected samples | Independent original expected values at the assertion times |

New S06/S10 runs retain an actual VCD, original and recording testbenches,
input netlist, raw simulation logs and a recording manifest with byte hashes.
Recording reuses the S14 insertion while keeping the original frozen plan,
assertions, timing and expected values unchanged. The viewer displays real
transitions and compares them directly with the independent expected samples.
S06/S10 remain zero-delay netlist checks, not physical-delay simulation.

The older P1 S06/S10 runs retained14cycles/42 output samples rather than a
full VCD. Their sample diagrams require no rerun, and their accepted records
are not rewritten. The P1 replay generates new evidence from the same inputs.
P1 S14 retained a VCD; its
generated testbench aliases are mapped to the original declared port names.
S14 VCD is routed-netlist **functional** simulation, not dynamic SDF delay
simulation. Nine-corner extracted STA remains separate evidence.

The viewer compares retained observations with independently saved expectations.
An absent observation remains absent. A VCD ending early stops its observed
trace and does not supply values for later expected checks; these are counted
as missing observations. Mixed X/Z bus values remain visible and count as
differences from numeric expectations. Red mismatch markers and **Go to first
mismatch** locate a difference when present. Existing validation status is never
rewritten by this visual comparison. Decimal bus values remain exact beyond
JavaScript's integer precision; X/Z remain visible. The supported VCD reader is
bounded to32MiB,256signals,200000value changes and4096-bit digital signals;
unsupported encodings or exceeded limits produce an explicit error rather than
a silently truncated plot. Historical results without supported retained
waveform/sample evidence report that absence and start no tool.

## Files and change history

Choose **Files & history** in the project command bar. **Files** lists the active
system's saved stores (including repair/batch stores and diagnostic handoffs),
the containing project manifest, specification/expectation snapshots, stored RTL/netlist
records, verification records, retained EDA files and declared application
implementation changes. Filter by group or search, then select a **file row**
directly, press Enter/Space on a focused row, or use **Inspect**. Refresh/reopen
the index after generation to include the new saved outputs. Saved artifact
hashes and sizes are checked before display. Text has a read-only preview;
PNG layout images render inline. Other binary formats such as GDS show verified
metadata and an explicit preview limitation, with the existing saved download.
Text files above2MiB use explicit nominal64KiB pages. **First page**, **Previous
text page**, **Next text page** and **Last page** show the selected page and byte
range; no page is presented as the complete file. UTF-8 boundaries preserve
characters without loss or duplication. Each page is bound to the full-file
SHA-256; if the file changes, refresh it instead of mixing versions. Text preview
supports files up to64MiB with bounded streaming validation. Larger files show
an explicit limit; binary formats retain metadata and existing saved downloads.
Inline PNG retains its2MiB limit.

A location containing `#` identifies a record *inside* a JSON store; it is not a
separate generated file. Paths are relative to the HuLLCirq checkout. The catalog
supports systems stored inside that checkout and does not expose an arbitrary
OS directory browser. No file edit/delete/save action is added.

**Change history** shows retained execution, save-snapshot and review records.
**Design changes** contains diffs between retained adjacent snapshots. Unknown
historical edit times and actors stay unknown; file modification time is not
proof of authorship. Implementation changes declared in
`docs/implementation_activity.json` are shown separately with their actual
before/current text diff and current file checksum. This is an explicit
development record, not an automatic audit of unrelated external editors.

Opening these views, searching, paging, selecting signals and moving the cursor
changes browser view state only. Changing project, system, revision or selected
run invalidates the corresponding in-flight view; an old response must not fill
another project's viewer. Existing accepted evidence is retained.

See the verification ledger (historical development reference; not included in this curated archive)
for actual GUI coverage, loop counts, intervention times and preservation checks.
