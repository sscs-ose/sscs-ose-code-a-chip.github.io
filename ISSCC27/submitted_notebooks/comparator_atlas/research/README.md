# Research extension scripts

Scripts for Notebook Section 9: later local SKY130/ngspice schematic studies
(r1-r24) asking why no compared design qualifies at 1 mV, and testing trim
designs that address it. They are not part of the sealed decision record.

Each script's docstring gives its command line. `archive_results.py` copies the
selected outputs from `research/out/` into `results/research/` and writes a
SHA256 manifest that `presentation/research_extension.py` verifies before the
Notebook draws anything. `out/` and `cache/` are ignored scratch folders.

Prerequisites, runtimes, study list and scope are in
[REPRODUCIBILITY.md](../REPRODUCIBILITY.md#research-extension).
