# SAR ADC in sky130 — two notebooks

Submissions to the IEEE SSCS Open-Source Ecosystem **"Code-a-Chip" Travel Grant Awards**,
ISSCC 2027. Joyce Berdkan, The George Washington University — `j.berdkan@gwu.edu`.
Apache-2.0.

## Which to read

**`SAR_digital_sky130.ipynb` — the digital half, and an OpenLayout replication.**
Start here. It is self-contained and runs from a single upload. A SAR sequencer taken from a
774-device transistor netlist to synthesisable RTL, verified, pushed through OpenROAD to a
sky130 layout that passes the PDK's full sign-off DRC deck, and then used as the subject of an
attempted replication of *OpenLayout* (Li *et al.*, ICCAD '26).

| section | what it establishes |
|---|---|
| 2–3 | two defects found by diffing RTL against the netlist, one of which **no testbench can catch** — demonstrated, not argued |
| 4–5 | an output that was not what its comment said; the one-line invariant that would have caught a seven-week bug |
| 6 | sky130 RTL-to-GDS: 78 cells, +8.61 ns slack, **0 violations across 256 sign-off rules** |
| 7 | scaling to a 16-channel controller, and why it was necessary |
| 8 | five findings from replicating OpenLayout, including two runs that reported a confident verdict having compared nothing |

**`SAR_ADC_sky130.ipynb` — the analog converter.**
The companion. An 8-bit charge-redistribution SAR: CDAC, StrongARM comparator, 774 devices live
in ngspice, DRC and LVS on generated layout. Four findings about measurement, each one a result
that was published and later withdrawn. Read it for Sections 3–6 if you only have ten minutes.

The two are independent; neither requires the other. They share a thesis, which is that **the
expensive failure is not a wrong answer but a right-looking answer from a check that did not
run**, and they arrive at it from opposite ends — one from analog measurement, one from digital
implementation.

## Running them

Both run on a free Colab instance from a cold start, no GPU and no API key. Each fetches its own
tools and prints its own measured end-to-end runtime; neither asks you to trust a quoted figure.

## Honest scope

- The long ngspice records in the analog notebook are **shipped as data**, not re-simulated.
  Hours of simulation; the findings they support are reproduced from first principles instead.
- The OpenLayout agent loop is **not** run in the notebook — it needs a funded LLM API key, and a
  cell a reviewer cannot execute is not a result. The baseline it would be compared against is.
- LVS on the digital block **does not yet close**. The 114 logic cells correspond exactly; 184
  transistors from physical-only fill and decap cells, supply naming and pin labelling remain.
  This is recorded rather than omitted.
