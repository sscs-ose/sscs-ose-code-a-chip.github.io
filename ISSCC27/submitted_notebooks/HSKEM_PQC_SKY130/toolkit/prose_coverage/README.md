# prose_coverage: which numbers in a notebook's prose are tied to its data?

A measurement notebook is only as trustworthy as the link between the numbers in its text and the results
they quote. `prose_coverage.py` reads an executed Jupyter notebook and sorts every number in its markdown
into three classes:

| Class | Meaning |
|:---|:---|
| asserted | the number appears in an `assert` of a code cell, or in a markdown table that a code cell compares as a whole |
| shown | the number appears in a saved output of an executed code cell, so it was computed |
| neither | typed by hand: a reader cannot trace it to the data |

A number also counts when it is a rounding of a computed or asserted value to its own number of significant
digits (two or more), so "about 27 µJ" matches 26.62 and "99.5 %" matches an asserted share of 0.995.
Section and appendix numbers, heading numbers, citations, years, inline code and math, URLs and list markers
are labels, not claims, and are skipped.

## Usage

```bash
python3 prose_coverage.py notebook.ipynb --list --json coverage.json
```

| Option | Effect |
|:---|:---|
| `--body-end REGEX` | stop at the first markdown cell that starts with this pattern (default: an *Appendix*, *Appendices* or *References* heading) |
| `--skip REGEX` | an extra label pattern, repeatable (product names with digits, chip names) |
| `--table-assert-marker TEXT` | if a code cell contains `TEXT`, the tables of the first markdown cell count as asserted |
| `--exclude-cell-marker TEXT` | ignore code cells that contain `TEXT` (e.g. the cell that prints this count) |
| `--list` | print the numbers of the class *neither*, by section |
| `--json FILE` | write the counts and the list |

The notebook must have been executed and saved with its outputs; otherwise only asserted numbers can count
and the tool says so.

## Evidence

- HSKEM (this submission): 193 numbers in the body, 97.9 % asserted or shown; the rest are definitions (the
  1600-bit Keccak state, a 700 MB download) and the pre-correction value quoted in the table of results that
  looked right (Appendix E.4 prints the current count).
- Three notebooks accepted at ISSCC 2026, unchanged: 26 numbers and 73 % (Auto-R2R-DAC), 4 numbers and
  100 % (Onchip_CurrentReference_LayoutAutomated), and 607 numbers in a notebook saved without outputs,
  which the tool reports as such (Izhikevich_neuron).
- `test_prose_coverage.py`: six unit tests on synthetic notebooks (`python3 -m pytest -q`).

SPDX-License-Identifier: Apache-2.0
