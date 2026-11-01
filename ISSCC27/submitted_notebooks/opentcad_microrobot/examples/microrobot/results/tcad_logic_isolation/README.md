# TCAD logic-only startup isolation

**Reviewed and accepted as held-reset logic-only startup evidence; no released-controller or actuator validation.**

Requested exactly one **250 µs / 25 ns** cold-start transient, with no fine or rescue run. Complete: **True**. The run starts at zero, reaches exactly **250 µs**, saves **10875 × 15 finite values**, and returns zero with no abort/timestep-too-small marker. Logic ends at **1.826129 V** and peaks at **1.831143 V**; the maximum per-cell voltage is **0.457786 V**, inside the characterized DD domain. Reset spans **−2.849476 to +3.041326 mV**; while logic ≥1.4 V, native Q stays within **128.698 µV** of zero and both reset/Q remain below the diagnostic 10%-of-logic bound. Global Q peaks at 0.215507 V during the low-rail startup interval, so the powered and global bounds must be distinguished. The held-reset numerical command remains exactly zero throughout. Two clock rising edges while logic ≥1.4 V occur at **81.369243 and 208.367507 µs**; no clock-frequency or divide-by-two qualification is claimed. The reduced held-reset logic bench passes beyond the previous abort times. Isolation also removed phase/event and supervisor networks and changed coupled loading and supply trajectories, so the source or cause of the earlier aborts is not uniquely isolated.

The four-series 1080 µm²/cell TCAD logic source, compact extracted clock, native resettable DFF/feedback, switched-capacitor digital proxy, 2 pF storage, optical ramp and Gear2 solver are retained. Reset is held asserted throughout by the existing rail-powered 10 kΩ bridge; its zero-valued numerical control supplies no analog gate charge. Removed components are explicit in configuration.json and deck.diff: all actuator PV/storage/driver/electrode/solution networks, phase counter/phase bridges, actuator supervisor controls and native supervisor components. No DD, native DC or layout run is added because the logic source expression is exactly unchanged from the verified source.

Metrics report complete finite coverage from zero to 250 µs, abort/exit checks, per-cell DD domain, rail/reset/native-clock/Q bounds and held-reset behavior. Logic 1.4–1.94 V are engineering bench limits, not foundry specifications. No released-controller, native POR, phase, bending or autonomous operation is accepted by this diagnostic. Raw data remain local; exact deck/log, source snapshot, diff and hashes are retained. No defaults or prior evidence are changed.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m examples.microrobot.tcad_logic_isolation
```

The runner refuses existing destinations. No submission, publication, push or fabrication occurred.

Three focused simulator-free tests pass in 0.82 s; Ruff passes. The initial absence assertion was corrected to distinguish the exact `Bpvlo ` source name from the prefix of `Bpvlogic`; no simulation deck changed. Full-suite testing was not run. No plot or mechanical postprocessing was generated for this isolation. Execution counts are one transient, zero fine/rescue/DC/DD/layout runs. The previous failed integration and supervisor-control evidence remain unchanged.

```text
MPLCONFIGDIR=/tmp/opentcad-mpl .venv/bin/python -m pytest tests/integration/test_tcad_logic_isolation.py -q
.venv/bin/python -m ruff check examples/microrobot/tcad_logic_isolation.py tests/integration/test_tcad_logic_isolation.py
```

The review corrected the original generated interpretation: removing several networks and their loading does not show that the actuator network was necessary for an abort. The executed runner snapshot and numerical results are preserved; no simulation was repeated.
