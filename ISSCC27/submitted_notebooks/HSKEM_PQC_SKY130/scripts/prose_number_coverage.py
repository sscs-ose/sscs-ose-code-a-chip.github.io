"""The prose-number coverage of this notebook (Appendix E.4), with toolkit/prose_coverage/prose_coverage.py.

    python3 scripts/prose_number_coverage.py [notebook.ipynb] [--list] [--json results/prose_number_coverage.json]

HSKEM's settings: the names of its chips and standards are labels, not claims; the results table of the first
page is compared as a whole by `assert rows == GLANCE`; the cell that prints this count does not count itself.
Definitional constants (the 1600-bit Keccak state, the 700 MB tool download) remain in the class "neither".
SPDX-License-Identifier: Apache-2.0
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "toolkit" / "prose_coverage"))
import prose_coverage  # noqa: E402

HSKEM = ["--skip", r"HSKEM-\d", "--skip", r"Keccak-f\[1600\]|Agilex\s*5|DE25|ESP32|M20K|OpenRAM|SKY130",
         "--skip", r"\b[A-H]\d?\b(?=[:.,)])", "--table-assert-marker", "assert rows == GLANCE",
         "--exclude-cell-marker", "prose_number_coverage"]

if __name__ == "__main__":
    args = sys.argv[1:] or ["HSKEM_PQC_SKY130.ipynb"]
    if args[0].startswith("--"):
        args = ["HSKEM_PQC_SKY130.ipynb"] + args
    prose_coverage.main(args + HSKEM)
